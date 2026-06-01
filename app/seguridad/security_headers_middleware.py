"""
Security Headers Middleware

Middleware ASGI puro que agrega headers de seguridad HTTP a todas las respuestas del sistema.
Implementado sin BaseHTTPMiddleware para evitar problemas de buffering con respuestas de
streaming (como PDFs).

Headers aplicados:
- X-Content-Type-Options: previene MIME sniffing
- X-Frame-Options: previene clickjacking
- X-XSS-Protection: activa protección XSS del navegador
- Referrer-Policy: controla información de referrer
- Content-Security-Policy: política restrictiva de contenido
- Strict-Transport-Security: solo en producción, fuerza HTTPS
"""

import os
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.datastructures import MutableHeaders


# Headers de seguridad que aplican en todos los entornos
SECURITY_HEADERS_ALWAYS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "  # unsafe-inline necesario para Vite en dev
        "img-src 'self' data: blob:; "  # blob: para PDFs generados
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    ),
}

# Headers adicionales solo en producción
SECURITY_HEADERS_PRODUCTION: dict[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware:
    """
    Agrega headers de seguridad HTTP a todas las respuestas.

    Implementado como middleware ASGI puro (no BaseHTTPMiddleware) para
    evitar overhead de buffering y garantizar que los headers se agregan
    incluso en respuestas de streaming.

    El middleware detecta automáticamente el entorno de producción mediante
    la variable de entorno ENVIRONMENT y agrega headers adicionales cuando
    corresponde (como HSTS).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.is_production = os.getenv("ENVIRONMENT") == "production"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Solo procesar requests HTTP
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message):
            """Intercepta el mensaje de respuesta y agrega headers de seguridad."""
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)

                # Agregar headers que aplican siempre
                for name, value in SECURITY_HEADERS_ALWAYS.items():
                    headers.append(name, value)

                # Agregar headers adicionales en producción
                if self.is_production:
                    for name, value in SECURITY_HEADERS_PRODUCTION.items():
                        headers.append(name, value)

            await send(message)

        await self.app(scope, receive, send_with_security_headers)
