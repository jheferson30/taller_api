"""Esquemas Pydantic para el Security Dashboard del SUPER_ADMIN."""
from datetime import datetime

from pydantic import BaseModel, Field


class HourlyCount(BaseModel):
    """Conteo de eventos agrupado por hora."""

    hour: datetime = Field(..., description="Inicio del bucket horario (UTC)")
    count: int = Field(..., ge=0, description="Número de eventos en esa hora")


class DailyCount(BaseModel):
    """Conteo de eventos agrupado por día."""

    day: datetime = Field(..., description="Inicio del bucket diario (UTC)")
    count: int = Field(..., ge=0, description="Número de eventos en ese día")


class IPViolationEntry(BaseModel):
    """Entrada de IP con total de violaciones de rate limit."""

    ip_address: str = Field(..., description="Dirección IP del cliente")
    total_violations: int = Field(..., ge=0, description="Total de violaciones en el período")


class UserViolationEntry(BaseModel):
    """Entrada de usuario con total de violaciones de rate limit."""

    user_id: int = Field(..., description="ID del usuario")
    total_violations: int = Field(..., ge=0, description="Total de violaciones en el período")


class SecurityMetricsResponse(BaseModel):
    """Respuesta completa del dashboard de métricas de seguridad."""

    # Violaciones de rate limit agrupadas por hora (últimas 24h)
    rate_limit_violations_24h: list[HourlyCount] = Field(
        ...,
        description="Violaciones de rate limit por hora en las últimas 24 horas",
    )
    # Intentos cross-tenant agrupados por día (últimos 30 días)
    cross_tenant_attempts_30d: list[DailyCount] = Field(
        ...,
        description="Intentos de acceso cross-tenant por día en los últimos 30 días",
    )
    # Intentos de autenticación fallidos agrupados por hora (últimas 24h)
    failed_auth_attempts_24h: list[HourlyCount] = Field(
        ...,
        description="Intentos de autenticación fallidos por hora en las últimas 24 horas",
    )
    # Top 10 IPs por violaciones de rate limit (últimas 24h)
    top_ips_by_violations: list[IPViolationEntry] = Field(
        ...,
        description="Top 10 IPs con más violaciones de rate limit en las últimas 24 horas",
    )
    # Top 10 usuarios por violaciones de rate limit (últimas 24h)
    top_users_by_violations: list[UserViolationEntry] = Field(
        ...,
        description="Top 10 usuarios con más violaciones de rate limit en las últimas 24 horas",
    )
    # Metadatos de la respuesta
    generated_at: datetime = Field(..., description="Timestamp de generación de las métricas (UTC)")
    cache_hit: bool = Field(..., description="True si la respuesta proviene del caché Redis")
