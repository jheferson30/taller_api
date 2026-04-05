import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_whitelist_ips() -> set:
    """Obtiene lista de IPs whitelisted desde variable de entorno."""
    whitelist_str = os.getenv("RATE_LIMIT_WHITELIST_IPS", "")
    if not whitelist_str:
        return set()
    return {ip.strip() for ip in whitelist_str.split(",") if ip.strip()}


def _key_func(request: Request) -> str:
    """
    Key function para rate limiting.
    
    - Excluye preflight OPTIONS
    - Excluye IPs en whitelist
    - Usa IP del cliente para rate limiting
    """
    # No aplicar rate limiting a preflight OPTIONS
    if request.method == "OPTIONS":
        return "options-exempt"
    
    # Obtener IP del cliente
    client_ip = get_remote_address(request)
    
    # Verificar si está en whitelist
    whitelist = _get_whitelist_ips()
    if client_ip in whitelist:
        return "whitelist-exempt"
    
    return client_ip


limiter = Limiter(key_func=_key_func, storage_uri="memory://")
