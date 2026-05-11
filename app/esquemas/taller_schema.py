"""Esquemas Pydantic para endpoints de Talleres."""
from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, EmailStr, Field


class EstadoTallerEnum(StrEnum):
    TRIAL = "TRIAL"
    ACTIVO = "ACTIVO"
    SUSPENDIDO = "SUSPENDIDO"
    CANCELADO = "CANCELADO"


class TallerCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    nit: str | None = Field(None, max_length=50)
    direccion: str | None = Field(None, max_length=300)
    telefono: str | None = Field(None, max_length=50)
    dias_trial: int = Field(default=30, ge=1, le=365)


class TallerUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=200)
    nit: str | None = Field(None, max_length=50)
    direccion: str | None = Field(None, max_length=300)
    telefono: str | None = Field(None, max_length=50)
    activo: bool | None = None
    estado: EstadoTallerEnum | None = None
    dias_trial: int | None = Field(None, ge=1, le=365)


class TallerResponse(BaseModel):
    id: int
    nombre: str
    nit: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    activo: bool
    estado: EstadoTallerEnum
    fecha_creacion: datetime
    fecha_actualizacion: datetime | None = None
    fecha_inicio_trial: datetime | None = None
    dias_trial: int | None = None
    dias_restantes_trial: int | None = None  # calculado en el servicio
    fecha_suspension: datetime | None = None
    fecha_cancelacion: datetime | None = None
    bloqueado_emergencia: bool = False
    fecha_bloqueo_emergencia: datetime | None = None
    motivo_bloqueo_emergencia: str | None = None

    class Config:
        from_attributes = True


class TallerMetricasResponse(BaseModel):
    taller_id: int
    usuarios_activos: int
    tickets_historicos: int
    tickets_mes_actual: int
    fecha_ultimo_acceso: datetime | None = None


class MetricasGlobalesResponse(BaseModel):
    total_talleres: int
    talleres_por_estado: dict[str, int]
    total_usuarios_activos: int
    total_usuarios: int


class TallerRecursosResponse(BaseModel):
    taller_id: int
    almacenamiento_bytes: int
    almacenamiento_mb: float
    tickets_mes_actual: int
    limite_tickets_mes: int | None = None


class BloqueoEmergenciaRequest(BaseModel):
    motivo: str = Field(..., min_length=10, max_length=500)


class CrearAdminTallerRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    nombre_completo: str | None = None


class NotificacionMasivaRequest(BaseModel):
    """Request para enviar notificación masiva a todos los talleres."""
    titulo: str = Field(..., min_length=5, max_length=200, description="Título de la notificación")
    mensaje: str = Field(..., min_length=10, max_length=500, description="Mensaje de la notificación")
    solo_admins: bool = Field(default=True, description="Si es True, solo envía a usuarios ADMIN. Si es False, envía a todos los usuarios activos")
    talleres_ids: list[int] | None = Field(default=None, description="IDs de talleres específicos. Si es None, envía a todos los talleres activos")


class NotificacionMasivaResponse(BaseModel):
    """Response del envío de notificación masiva."""
    notificaciones_enviadas: int
    talleres_afectados: int
    usuarios_notificados: int
    detalles: dict[str, int] = Field(default_factory=dict, description="Desglose por taller")
