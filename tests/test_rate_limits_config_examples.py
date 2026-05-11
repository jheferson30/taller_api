"""
Tests de ejemplos concretos para el parser y pretty-printer de configuración
de rate limits.

Cubre casos específicos de parsing válido e inválido para verificar que el
parser acepta configuraciones correctas y rechaza las incorrectas con mensajes
descriptivos.

Requisitos: 5.1, 5.2, 5.5, 5.6, 5.7, 5.8
"""

from __future__ import annotations

import json

import pytest
import yaml

from app.configuracion.rate_limits_config import (
    EndpointRateLimit,
    GlobalLimit,
    RateLimitConfig,
    RateLimitConfigError,
    RateLimitsParser,
    RateLimitsPrettyPrinter,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXAMPLE_YAML = """\
version: "1.0"
global_limits:
  - limit: 100
    window: minute
    description: "Límite global por IP"
  - limit: 1000
    window: hour
    description: "Límite global por IP por hora"
  - limit: 5000
    window: day
    description: "Límite global por IP por día"
endpoint_limits:
  - pattern: "^/upload/.*"
    limit: 10
    window: minute
    description: "Endpoints de subida de archivos"
  - pattern: "^/whatsapp/.*"
    limit: 5
    window: minute
    description: "Endpoints de WhatsApp"
  - pattern: "^/tickets.*"
    limit: 30
    window: minute
    description: "Endpoints de tickets"
  - pattern: "^/vehiculos.*"
    limit: 30
    window: minute
    description: "Endpoints de vehículos"
"""


@pytest.fixture
def parser() -> RateLimitsParser:
    return RateLimitsParser()


@pytest.fixture
def printer() -> RateLimitsPrettyPrinter:
    return RateLimitsPrettyPrinter()


# ---------------------------------------------------------------------------
# Tests de parsing válido — Requisito 5.1
# ---------------------------------------------------------------------------


class TestValidParsing:
    """Verifica que el parser acepta configuraciones válidas y produce el objeto correcto."""

    def test_parse_example_yaml_produces_correct_config(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Parsear el YAML de ejemplo del diseño produce el RateLimitConfig esperado.

        Verifica:
        - version == "1.0"
        - 3 global_limits con los valores correctos
        - 4 endpoint_limits con los patrones y límites correctos

        Requisito 5.1
        """
        config = parser.parse(EXAMPLE_YAML, fmt="yaml")

        # Versión
        assert config.version == "1.0"

        # Global limits
        assert len(config.global_limits) == 3

        gl_minute = config.global_limits[0]
        assert gl_minute.limit == 100
        assert gl_minute.window == "minute"
        assert gl_minute.description == "Límite global por IP"

        gl_hour = config.global_limits[1]
        assert gl_hour.limit == 1000
        assert gl_hour.window == "hour"
        assert gl_hour.description == "Límite global por IP por hora"

        gl_day = config.global_limits[2]
        assert gl_day.limit == 5000
        assert gl_day.window == "day"
        assert gl_day.description == "Límite global por IP por día"

        # Endpoint limits
        assert len(config.endpoint_limits) == 4

        upload = config.endpoint_limits[0]
        assert upload.pattern == "^/upload/.*"
        assert upload.limit == 10
        assert upload.window == "minute"
        assert upload.description == "Endpoints de subida de archivos"

        whatsapp = config.endpoint_limits[1]
        assert whatsapp.pattern == "^/whatsapp/.*"
        assert whatsapp.limit == 5
        assert whatsapp.window == "minute"

        tickets = config.endpoint_limits[2]
        assert tickets.pattern == "^/tickets.*"
        assert tickets.limit == 30
        assert tickets.window == "minute"

        vehiculos = config.endpoint_limits[3]
        assert vehiculos.pattern == "^/vehiculos.*"
        assert vehiculos.limit == 30
        assert vehiculos.window == "minute"

    def test_parse_json_equivalent_to_yaml(self, parser: RateLimitsParser) -> None:
        """
        Parsear el mismo config en JSON produce el mismo resultado que en YAML.

        Requisito 5.1
        """
        # Convertir el YAML de ejemplo a JSON
        raw = yaml.safe_load(EXAMPLE_YAML)
        json_content = json.dumps(raw)

        config_from_yaml = parser.parse(EXAMPLE_YAML, fmt="yaml")
        config_from_json = parser.parse(json_content, fmt="json")

        assert config_from_yaml.version == config_from_json.version
        assert len(config_from_yaml.global_limits) == len(config_from_json.global_limits)
        assert len(config_from_yaml.endpoint_limits) == len(config_from_json.endpoint_limits)

        for orig, parsed in zip(
            config_from_yaml.endpoint_limits, config_from_json.endpoint_limits
        ):
            assert orig.pattern == parsed.pattern
            assert orig.limit == parsed.limit
            assert orig.window == parsed.window

    def test_parse_config_without_endpoint_limits(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Una configuración sin endpoint_limits es válida (lista vacía).

        Requisito 5.1
        """
        yaml_content = """\
version: "1.0"
global_limits:
  - limit: 100
    window: minute
"""
        config = parser.parse(yaml_content, fmt="yaml")
        assert config.version == "1.0"
        assert len(config.global_limits) == 1
        assert config.endpoint_limits == []

    def test_parse_config_without_global_limits(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Una configuración sin global_limits es válida (lista vacía).

        Requisito 5.1
        """
        yaml_content = """\
version: "2.0"
endpoint_limits:
  - pattern: "^/api/.*"
    limit: 50
    window: hour
"""
        config = parser.parse(yaml_content, fmt="yaml")
        assert config.version == "2.0"
        assert config.global_limits == []
        assert len(config.endpoint_limits) == 1

    def test_parse_config_without_description_fields(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Los campos 'description' son opcionales; su ausencia no causa error.

        Requisito 5.1
        """
        yaml_content = """\
version: "1.0"
global_limits:
  - limit: 100
    window: minute
endpoint_limits:
  - pattern: "^/upload/.*"
    limit: 10
    window: minute
"""
        config = parser.parse(yaml_content, fmt="yaml")
        assert config.global_limits[0].description == ""
        assert config.endpoint_limits[0].description == ""


# ---------------------------------------------------------------------------
# Tests de errores de parsing — Requisito 5.2
# ---------------------------------------------------------------------------


class TestParsingErrors:
    """Verifica que el parser rechaza configuraciones inválidas con mensajes descriptivos."""

    def test_error_message_includes_line_number_for_yaml_syntax_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un error de sintaxis YAML incluye el número de línea en el error.

        Requisito 5.2
        """
        # YAML con tabulación inválida (causa error de sintaxis)
        invalid_yaml = "version: '1.0'\nglobal_limits:\n\t- limit: 100\n"
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(invalid_yaml, fmt="yaml")
        # El error debe tener número de línea
        assert exc_info.value.line_number is not None

    def test_error_missing_version_field(self, parser: RateLimitsParser) -> None:
        """
        Una configuración sin el campo 'version' lanza RateLimitConfigError.

        Requisito 5.2
        """
        yaml_content = """\
global_limits:
  - limit: 100
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")
        assert "version" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Tests de rechazo de valores de límite inválidos — Requisitos 5.5, 5.7
# ---------------------------------------------------------------------------


class TestInvalidLimitValues:
    """Verifica que el parser rechaza valores de límite inválidos con mensajes descriptivos."""

    def test_limit_zero_in_global_limits_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un valor de límite igual a 0 en global_limits lanza RateLimitConfigError.

        Requisitos 5.5, 5.7
        """
        yaml_content = """\
version: "1.0"
global_limits:
  - limit: 0
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "global_limits[1].limit" in error_message, (
            f"El error debe mencionar el campo inválido, se obtuvo: {error_message!r}"
        )
        assert "0" in error_message, (
            f"El error debe mencionar el valor inválido (0), se obtuvo: {error_message!r}"
        )

    def test_limit_negative_in_global_limits_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un valor de límite negativo (-5) en global_limits lanza RateLimitConfigError.

        Requisitos 5.5, 5.7
        """
        yaml_content = """\
version: "1.0"
global_limits:
  - limit: -5
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "global_limits[1].limit" in error_message, (
            f"El error debe mencionar el campo inválido, se obtuvo: {error_message!r}"
        )
        assert "-5" in error_message, (
            f"El error debe mencionar el valor inválido (-5), se obtuvo: {error_message!r}"
        )

    def test_limit_string_in_global_limits_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un valor de límite como string ("abc") en global_limits lanza RateLimitConfigError.

        Requisitos 5.5, 5.7
        """
        yaml_content = """\
version: "1.0"
global_limits:
  - limit: "abc"
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "global_limits[1].limit" in error_message, (
            f"El error debe mencionar el campo inválido, se obtuvo: {error_message!r}"
        )
        # El mensaje debe indicar que se recibió un tipo incorrecto (str)
        assert "str" in error_message.lower() or "abc" in error_message, (
            f"El error debe mencionar el tipo o valor inválido, se obtuvo: {error_message!r}"
        )

    def test_limit_zero_in_endpoint_limits_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un valor de límite igual a 0 en endpoint_limits lanza RateLimitConfigError.

        Requisitos 5.5, 5.7
        """
        yaml_content = """\
version: "1.0"
endpoint_limits:
  - pattern: "^/api/.*"
    limit: 0
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "endpoint_limits[1].limit" in error_message, (
            f"El error debe mencionar el campo inválido, se obtuvo: {error_message!r}"
        )

    def test_limit_negative_in_endpoint_limits_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un valor de límite negativo en endpoint_limits lanza RateLimitConfigError.

        Requisitos 5.5, 5.7
        """
        yaml_content = """\
version: "1.0"
endpoint_limits:
  - pattern: "^/api/.*"
    limit: -5
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "endpoint_limits[1].limit" in error_message

    def test_limit_string_in_endpoint_limits_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un valor de límite como string en endpoint_limits lanza RateLimitConfigError.

        Requisitos 5.5, 5.7
        """
        yaml_content = """\
version: "1.0"
endpoint_limits:
  - pattern: "^/api/.*"
    limit: "abc"
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "endpoint_limits[1].limit" in error_message

    def test_first_invalid_limit_is_reported(self, parser: RateLimitsParser) -> None:
        """
        Cuando hay múltiples límites inválidos, el error reporta el primero.

        Requisito 5.2
        """
        yaml_content = """\
version: "1.0"
global_limits:
  - limit: -1
    window: minute
  - limit: -2
    window: hour
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        # El primer error debe ser el de global_limits[1], no global_limits[2]
        assert "global_limits[1].limit" in error_message


# ---------------------------------------------------------------------------
# Tests de rechazo de patrones regex inválidos — Requisitos 5.6, 5.8
# ---------------------------------------------------------------------------


class TestInvalidRegexPatterns:
    """Verifica que el parser rechaza patrones regex inválidos con mensajes descriptivos."""

    def test_unclosed_bracket_pattern_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un patrón con corchete sin cerrar ("[") lanza RateLimitConfigError.

        Requisitos 5.6, 5.8
        """
        yaml_content = """\
version: "1.0"
endpoint_limits:
  - pattern: "["
    limit: 10
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "endpoint_limits[1].pattern" in error_message, (
            f"El error debe mencionar el campo inválido, se obtuvo: {error_message!r}"
        )
        assert "[" in error_message, (
            f"El error debe mencionar el patrón inválido, se obtuvo: {error_message!r}"
        )

    def test_unclosed_group_pattern_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un patrón con paréntesis sin cerrar ("(abc") lanza RateLimitConfigError.

        Requisitos 5.6, 5.8
        """
        yaml_content = """\
version: "1.0"
endpoint_limits:
  - pattern: "(abc"
    limit: 10
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "endpoint_limits[1].pattern" in error_message

    def test_invalid_quantifier_pattern_raises_error(
        self, parser: RateLimitsParser
    ) -> None:
        """
        Un patrón con cuantificador inválido ("*abc") lanza RateLimitConfigError.

        Requisitos 5.6, 5.8
        """
        yaml_content = """\
version: "1.0"
endpoint_limits:
  - pattern: "*abc"
    limit: 10
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "endpoint_limits[1].pattern" in error_message

    def test_error_message_includes_invalid_pattern(
        self, parser: RateLimitsParser
    ) -> None:
        """
        El mensaje de error incluye el patrón inválido para facilitar la corrección.

        Requisito 5.8
        """
        invalid_pattern = "(?P<invalid"  # grupo nombrado sin cerrar
        yaml_content = f"""\
version: "1.0"
endpoint_limits:
  - pattern: "{invalid_pattern}"
    limit: 10
    window: minute
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        assert "endpoint_limits[1].pattern" in error_message
        # El patrón inválido debe aparecer en el mensaje
        assert invalid_pattern in error_message or repr(invalid_pattern) in error_message, (
            f"El error debe mencionar el patrón inválido {invalid_pattern!r}, "
            f"se obtuvo: {error_message!r}"
        )

    def test_first_invalid_pattern_is_reported(self, parser: RateLimitsParser) -> None:
        """
        Cuando hay múltiples patrones inválidos, el error reporta el primero.

        Requisito 5.2
        """
        yaml_content = """\
version: "1.0"
endpoint_limits:
  - pattern: "["
    limit: 10
    window: minute
  - pattern: "("
    limit: 20
    window: hour
"""
        with pytest.raises(RateLimitConfigError) as exc_info:
            parser.parse(yaml_content, fmt="yaml")

        error_message = str(exc_info.value)
        # El primer error debe ser el de endpoint_limits[1], no endpoint_limits[2]
        assert "endpoint_limits[1].pattern" in error_message


# ---------------------------------------------------------------------------
# Tests del pretty-printer — Requisito 5.3
# ---------------------------------------------------------------------------


class TestPrettyPrinter:
    """Verifica que el pretty-printer serializa correctamente los objetos RateLimitConfig."""

    def test_to_yaml_produces_valid_yaml(self, printer: RateLimitsPrettyPrinter) -> None:
        """
        to_yaml produce un string YAML válido que puede ser parseado de vuelta.

        Requisito 5.3
        """
        config = RateLimitConfig(
            version="1.0",
            global_limits=[GlobalLimit(limit=100, window="minute", description="Test")],
            endpoint_limits=[
                EndpointRateLimit(
                    pattern="^/api/.*",
                    limit=50,
                    window="hour",
                    description="API endpoints",
                )
            ],
        )
        yaml_str = printer.to_yaml(config)

        # Debe ser YAML válido
        parsed = yaml.safe_load(yaml_str)
        assert isinstance(parsed, dict)
        assert parsed["version"] == "1.0"
        assert parsed["global_limits"][0]["limit"] == 100
        assert parsed["endpoint_limits"][0]["pattern"] == "^/api/.*"

    def test_to_json_produces_valid_json(self, printer: RateLimitsPrettyPrinter) -> None:
        """
        to_json produce un string JSON válido que puede ser parseado de vuelta.

        Requisito 5.3
        """
        config = RateLimitConfig(
            version="1.0",
            global_limits=[GlobalLimit(limit=1000, window="hour")],
            endpoint_limits=[],
        )
        json_str = printer.to_json(config)

        # Debe ser JSON válido
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["version"] == "1.0"
        assert parsed["global_limits"][0]["limit"] == 1000

    def test_to_yaml_omits_empty_descriptions(
        self, printer: RateLimitsPrettyPrinter
    ) -> None:
        """
        to_yaml omite el campo 'description' cuando está vacío para mantener el output limpio.

        Requisito 5.3
        """
        config = RateLimitConfig(
            version="1.0",
            global_limits=[GlobalLimit(limit=100, window="minute", description="")],
            endpoint_limits=[],
        )
        yaml_str = printer.to_yaml(config)
        parsed = yaml.safe_load(yaml_str)

        # El campo description no debe aparecer cuando está vacío
        assert "description" not in parsed["global_limits"][0]

    def test_to_yaml_preserves_non_empty_descriptions(
        self, printer: RateLimitsPrettyPrinter
    ) -> None:
        """
        to_yaml preserva el campo 'description' cuando tiene contenido.

        Requisito 5.3
        """
        config = RateLimitConfig(
            version="1.0",
            global_limits=[
                GlobalLimit(limit=100, window="minute", description="Límite global")
            ],
            endpoint_limits=[],
        )
        yaml_str = printer.to_yaml(config)
        parsed = yaml.safe_load(yaml_str)

        assert parsed["global_limits"][0]["description"] == "Límite global"


# ---------------------------------------------------------------------------
# Tests de round-trip — Requisito 5.4
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Verifica la propiedad de round-trip: parse(print(config)) == config."""

    def test_round_trip_yaml_with_example_config(
        self, parser: RateLimitsParser, printer: RateLimitsPrettyPrinter
    ) -> None:
        """
        El YAML de ejemplo del diseño sobrevive un round-trip sin pérdida de datos.

        Requisito 5.4
        """
        original = parser.parse(EXAMPLE_YAML, fmt="yaml")
        yaml_str = printer.to_yaml(original)
        reparsed = parser.parse(yaml_str, fmt="yaml")

        assert original.version == reparsed.version
        assert len(original.global_limits) == len(reparsed.global_limits)
        assert len(original.endpoint_limits) == len(reparsed.endpoint_limits)

        for orig_el, rep_el in zip(original.endpoint_limits, reparsed.endpoint_limits):
            assert orig_el.pattern == rep_el.pattern
            assert orig_el.limit == rep_el.limit
            assert orig_el.window == rep_el.window

    def test_round_trip_json_with_example_config(
        self, parser: RateLimitsParser, printer: RateLimitsPrettyPrinter
    ) -> None:
        """
        El config de ejemplo sobrevive un round-trip YAML → JSON → parse sin pérdida.

        Requisito 5.4
        """
        original = parser.parse(EXAMPLE_YAML, fmt="yaml")
        json_str = printer.to_json(original)
        reparsed = parser.parse(json_str, fmt="json")

        assert original.version == reparsed.version
        assert len(original.global_limits) == len(reparsed.global_limits)
        assert len(original.endpoint_limits) == len(reparsed.endpoint_limits)

        for orig_el, rep_el in zip(original.endpoint_limits, reparsed.endpoint_limits):
            assert orig_el.pattern == rep_el.pattern
            assert orig_el.limit == rep_el.limit
            assert orig_el.window == rep_el.window

    def test_round_trip_preserves_all_limit_values(
        self, parser: RateLimitsParser, printer: RateLimitsPrettyPrinter
    ) -> None:
        """
        Los valores de límite se preservan exactamente en el round-trip.

        Requisito 5.4
        """
        config = RateLimitConfig(
            version="1.0",
            global_limits=[
                GlobalLimit(limit=100, window="minute"),
                GlobalLimit(limit=1000, window="hour"),
                GlobalLimit(limit=5000, window="day"),
            ],
            endpoint_limits=[
                EndpointRateLimit(pattern="^/upload/.*", limit=10, window="minute"),
                EndpointRateLimit(pattern="^/whatsapp/.*", limit=5, window="minute"),
            ],
        )

        # Round-trip YAML
        yaml_str = printer.to_yaml(config)
        reparsed = parser.parse(yaml_str, fmt="yaml")

        for orig_gl, rep_gl in zip(config.global_limits, reparsed.global_limits):
            assert orig_gl.limit == rep_gl.limit
            assert orig_gl.window == rep_gl.window

        for orig_el, rep_el in zip(config.endpoint_limits, reparsed.endpoint_limits):
            assert orig_el.pattern == rep_el.pattern
            assert orig_el.limit == rep_el.limit
            assert orig_el.window == rep_el.window
