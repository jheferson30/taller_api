"""
Parser y pretty-printer para configuración declarativa de rate limits.

Permite gestionar los límites por endpoint desde archivos YAML o JSON
sin necesidad de modificar código. Soporta validación estricta de valores
y patrones regex, con errores descriptivos que incluyen número de línea.

Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Literal

import yaml


# ---------------------------------------------------------------------------
# Modelos de datos
# ---------------------------------------------------------------------------


@dataclass
class GlobalLimit:
    """Límite global aplicado a todos los endpoints."""

    limit: int
    """Número máximo de requests permitidos en la ventana."""

    window: str
    """Ventana de tiempo: 'minute' | 'hour' | 'day'."""

    description: str = ""
    """Descripción legible del límite (opcional)."""


@dataclass
class EndpointRateLimit:
    """Límite específico para un endpoint o grupo de endpoints."""

    pattern: str
    """Expresión regular que identifica el endpoint, ej: r'^/upload/.*'."""

    limit: int
    """Número máximo de requests permitidos en la ventana."""

    window: str
    """Ventana de tiempo: 'minute' | 'hour' | 'day'."""

    description: str = ""
    """Descripción legible del límite (opcional)."""


@dataclass
class RateLimitConfig:
    """Configuración completa de rate limits, parseada desde YAML o JSON."""

    version: str
    """Versión del esquema de configuración, ej: '1.0'."""

    global_limits: list[GlobalLimit] = field(default_factory=list)
    """Límites globales aplicados a todos los endpoints."""

    endpoint_limits: list[EndpointRateLimit] = field(default_factory=list)
    """Límites específicos por endpoint o patrón de ruta."""


# ---------------------------------------------------------------------------
# Excepción de configuración
# ---------------------------------------------------------------------------


class RateLimitConfigError(Exception):
    """
    Error de validación o parsing de configuración de rate limits.

    Incluye el número de línea del primer campo inválido cuando está disponible,
    para facilitar la corrección del archivo de configuración.
    """

    def __init__(self, message: str, line_number: int | None = None) -> None:
        self.line_number = line_number
        location = f" (línea {line_number})" if line_number is not None else ""
        super().__init__(f"{message}{location}")


# ---------------------------------------------------------------------------
# Ventanas válidas
# ---------------------------------------------------------------------------

_VALID_WINDOWS = {"minute", "hour", "day"}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class RateLimitsParser:
    """
    Parsea archivos de configuración YAML o JSON en objetos RateLimitConfig.

    Valida que todos los valores de límite sean enteros positivos y que todos
    los patrones de endpoint sean expresiones regulares válidas. Los errores
    incluyen el número de línea del primer campo inválido.
    """

    def parse(
        self,
        content: str,
        fmt: Literal["yaml", "json"],
    ) -> RateLimitConfig:
        """
        Parsea contenido YAML o JSON en un RateLimitConfig validado.

        Args:
            content: Contenido del archivo de configuración como string.
            fmt: Formato del contenido, 'yaml' o 'json'.

        Returns:
            Objeto RateLimitConfig con los límites configurados.

        Raises:
            RateLimitConfigError: Si el contenido es inválido, con mensaje
                descriptivo y número de línea del primer campo inválido.
        """
        raw = self._parse_raw(content, fmt)
        self._validate(raw)
        return self._build(raw)

    # ------------------------------------------------------------------
    # Parsing del formato
    # ------------------------------------------------------------------

    def _parse_raw(
        self,
        content: str,
        fmt: Literal["yaml", "json"],
    ) -> dict:
        """
        Deserializa el contenido al formato nativo (dict).

        Captura errores de sintaxis y los relanza como RateLimitConfigError
        con el número de línea cuando el parser lo proporciona.

        Args:
            content: Contenido del archivo.
            fmt: Formato del archivo ('yaml' o 'json').

        Returns:
            Diccionario con los datos crudos del archivo.

        Raises:
            RateLimitConfigError: Si hay un error de sintaxis en el archivo.
        """
        if fmt == "yaml":
            return self._parse_yaml(content)
        elif fmt == "json":
            return self._parse_json(content)
        else:
            raise RateLimitConfigError(
                f"Formato no soportado: '{fmt}'. Use 'yaml' o 'json'."
            )

    def _parse_yaml(self, content: str) -> dict:
        """Parsea YAML y convierte errores de sintaxis a RateLimitConfigError."""
        try:
            raw = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            line_number = None
            if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
                # problem_mark.line es 0-indexed; convertir a 1-indexed
                line_number = exc.problem_mark.line + 1
            raise RateLimitConfigError(
                f"Error de sintaxis YAML: {exc.problem}",
                line_number=line_number,
            ) from exc

        if not isinstance(raw, dict):
            raise RateLimitConfigError(
                "El archivo YAML debe contener un objeto (mapping) en el nivel raíz."
            )
        return raw

    def _parse_json(self, content: str) -> dict:
        """Parsea JSON y convierte errores de sintaxis a RateLimitConfigError."""
        try:
            raw = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RateLimitConfigError(
                f"Error de sintaxis JSON: {exc.msg}",
                line_number=exc.lineno,
            ) from exc

        if not isinstance(raw, dict):
            raise RateLimitConfigError(
                "El archivo JSON debe contener un objeto en el nivel raíz."
            )
        return raw

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def _validate(self, raw: dict) -> None:
        """
        Valida el contenido crudo antes de construir el objeto de dominio.

        Verifica:
        - Presencia del campo 'version'
        - Todos los valores de 'limit' son enteros > 0
        - Todos los valores de 'window' son válidos ('minute', 'hour', 'day')
        - Todos los 'pattern' son expresiones regulares válidas

        Args:
            raw: Diccionario con los datos crudos del archivo.

        Raises:
            RateLimitConfigError: Con mensaje descriptivo del primer campo inválido.
        """
        if "version" not in raw:
            raise RateLimitConfigError(
                "Campo requerido ausente: 'version'. "
                "Ejemplo: version: '1.0'"
            )

        # Validar global_limits
        for i, entry in enumerate(raw.get("global_limits", []), start=1):
            self._validate_limit_value(
                entry.get("limit"),
                context=f"global_limits[{i}].limit",
            )
            self._validate_window(
                entry.get("window"),
                context=f"global_limits[{i}].window",
            )

        # Validar endpoint_limits
        for i, entry in enumerate(raw.get("endpoint_limits", []), start=1):
            self._validate_limit_value(
                entry.get("limit"),
                context=f"endpoint_limits[{i}].limit",
            )
            self._validate_window(
                entry.get("window"),
                context=f"endpoint_limits[{i}].window",
            )
            self._validate_regex_pattern(
                entry.get("pattern"),
                context=f"endpoint_limits[{i}].pattern",
            )

    def _validate_limit_value(self, value: object, context: str) -> None:
        """
        Verifica que un valor de límite sea un entero estrictamente positivo.

        Args:
            value: El valor a validar.
            context: Ruta del campo para el mensaje de error (ej: 'global_limits[1].limit').

        Raises:
            RateLimitConfigError: Si el valor no es un entero > 0.
        """
        # Rechazar booleanos explícitamente: bool es subclase de int en Python
        if isinstance(value, bool):
            raise RateLimitConfigError(
                f"Valor de límite inválido en '{context}': {value!r} "
                f"(debe ser un entero > 0, no un booleano)."
            )
        if not isinstance(value, int):
            raise RateLimitConfigError(
                f"Valor de límite inválido en '{context}': {value!r} "
                f"(debe ser un entero > 0, se recibió {type(value).__name__})."
            )
        if value <= 0:
            raise RateLimitConfigError(
                f"Valor de límite inválido en '{context}': {value!r} "
                f"(debe ser un entero > 0)."
            )

    def _validate_window(self, value: object, context: str) -> None:
        """
        Verifica que una ventana de tiempo sea un valor válido.

        Args:
            value: El valor a validar.
            context: Ruta del campo para el mensaje de error.

        Raises:
            RateLimitConfigError: Si el valor no es 'minute', 'hour' o 'day'.
        """
        if value not in _VALID_WINDOWS:
            raise RateLimitConfigError(
                f"Ventana de tiempo inválida en '{context}': {value!r} "
                f"(valores válidos: {sorted(_VALID_WINDOWS)})."
            )

    def _validate_regex_pattern(self, pattern: object, context: str) -> None:
        """
        Verifica que un patrón de endpoint sea una expresión regular válida.

        Args:
            pattern: El patrón a validar.
            context: Ruta del campo para el mensaje de error.

        Raises:
            RateLimitConfigError: Si el patrón no es un string o no es regex válido.
        """
        if not isinstance(pattern, str):
            raise RateLimitConfigError(
                f"Patrón de endpoint inválido en '{context}': {pattern!r} "
                f"(debe ser un string con una expresión regular válida)."
            )
        if not pattern:
            raise RateLimitConfigError(
                f"Patrón de endpoint vacío en '{context}': "
                f"el patrón no puede ser un string vacío."
            )
        try:
            re.compile(pattern)
        except re.error as exc:
            raise RateLimitConfigError(
                f"Patrón regex inválido en '{context}': {pattern!r} — {exc}."
            ) from exc

    # ------------------------------------------------------------------
    # Construcción del objeto de dominio
    # ------------------------------------------------------------------

    def _build(self, raw: dict) -> RateLimitConfig:
        """
        Construye un RateLimitConfig a partir del diccionario validado.

        Args:
            raw: Diccionario ya validado con los datos del archivo.

        Returns:
            Objeto RateLimitConfig completamente construido.
        """
        global_limits = [
            GlobalLimit(
                limit=entry["limit"],
                window=entry["window"],
                description=entry.get("description", ""),
            )
            for entry in raw.get("global_limits", [])
        ]

        endpoint_limits = [
            EndpointRateLimit(
                pattern=entry["pattern"],
                limit=entry["limit"],
                window=entry["window"],
                description=entry.get("description", ""),
            )
            for entry in raw.get("endpoint_limits", [])
        ]

        return RateLimitConfig(
            version=str(raw["version"]),
            global_limits=global_limits,
            endpoint_limits=endpoint_limits,
        )


# ---------------------------------------------------------------------------
# Pretty-printer
# ---------------------------------------------------------------------------


class RateLimitsPrettyPrinter:
    """
    Serializa objetos RateLimitConfig a YAML o JSON con formato legible.

    Garantiza que el output sea parseable por RateLimitsParser, cumpliendo
    la propiedad de round-trip: parse(print(config)) == config.
    """

    def to_yaml(self, config: RateLimitConfig) -> str:
        """
        Serializa un RateLimitConfig a YAML válido con indentación.

        Args:
            config: Objeto RateLimitConfig a serializar.

        Returns:
            String con el contenido YAML, listo para escribir a un archivo.
        """
        data = self._to_dict(config)
        return yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            indent=2,
        )

    def to_json(self, config: RateLimitConfig) -> str:
        """
        Serializa un RateLimitConfig a JSON válido con indentación de 2 espacios.

        Args:
            config: Objeto RateLimitConfig a serializar.

        Returns:
            String con el contenido JSON, listo para escribir a un archivo.
        """
        data = self._to_dict(config)
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _to_dict(self, config: RateLimitConfig) -> dict:
        """
        Convierte un RateLimitConfig a un diccionario serializable.

        Omite los campos 'description' vacíos para mantener el output limpio,
        pero los preserva cuando tienen contenido para no perder información.

        Args:
            config: Objeto RateLimitConfig a convertir.

        Returns:
            Diccionario con la representación del config, listo para serializar.
        """
        global_limits = []
        for gl in config.global_limits:
            entry: dict = {"limit": gl.limit, "window": gl.window}
            if gl.description:
                entry["description"] = gl.description
            global_limits.append(entry)

        endpoint_limits = []
        for el in config.endpoint_limits:
            entry = {"pattern": el.pattern, "limit": el.limit, "window": el.window}
            if el.description:
                entry["description"] = el.description
            endpoint_limits.append(entry)

        return {
            "version": config.version,
            "global_limits": global_limits,
            "endpoint_limits": endpoint_limits,
        }
