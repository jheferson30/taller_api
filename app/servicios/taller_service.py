"""
Servicio de gestión de Talleres (tenants).
Solo accesible por SUPER_ADMIN.
"""
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modelos.audit_log import AuditAction
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.modelos.password_reset_token import PasswordResetToken
from app.modelos.taller import EstadoTaller, Taller
from app.modelos.token_blacklist import TokenBlacklist
from app.modelos.user import User
from app.repositorios.taller_repository import TallerRepository
from app.servicios.audit_service import AuditService
from app.utils.tenant_guard import obtener_recurso_del_taller


class TallerService:
    # ID del taller principal (Taller_Default) — no se puede desactivar
    TALLER_DEFAULT_ID = 1

    def __init__(self, taller_repo: TallerRepository, audit_service: AuditService, db: Session):
        self.taller_repo = taller_repo
        self.audit_service = audit_service
        self.db = db

    def _audit(self, user_id: int, taller_id: int | None, action: AuditAction,
               resource_type: str, resource_id: int | None,
               ip_address: str, user_agent: str, details: dict | None = None) -> None:
        """Registra en audit log usando flush (no commit) para no romper transacciones."""
        from app.modelos.audit_log import AuditLog
        audit = AuditLog(
            user_id=user_id,
            taller_id=taller_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
        self.db.add(audit)
        self.db.flush()

    def crear_taller(self, nombre: str, nit: str | None, direccion: str | None,
                     telefono: str | None, dias_trial: int,
                     created_by: int, ip_address: str,
                     user_agent: str) -> Taller:
        """
        Crea un nuevo taller y su configuración por defecto.
        El taller inicia en estado TRIAL con fecha_inicio_trial = NOW().
        Raises ValueError si el nombre ya existe o está vacío.
        """
        # Validar nombre
        if not nombre or not nombre.strip():
            raise ValueError("El nombre del taller es obligatorio")

        # Verificar nombre duplicado
        existing = self.taller_repo.get_by_nombre(nombre.strip())
        if existing:
            raise ValueError("Ya existe un taller con ese nombre")

        ahora = datetime.now(timezone.utc)

        # Crear taller
        taller = Taller(
            nombre=nombre.strip(),
            nit=nit,
            direccion=direccion,
            telefono=telefono,
            activo=True,
            estado=EstadoTaller.TRIAL,
            fecha_inicio_trial=ahora,
            dias_trial=dias_trial,
        )
        taller = self.taller_repo.create(taller)

        # Crear configuración por defecto
        config = ConfiguracionTaller(
            taller_id=taller.id,
            nombre_taller=nombre.strip(),
        )
        self.db.add(config)
        self.db.flush()

        self._audit(created_by, taller.id, AuditAction.TALLER_CREATE, "taller", taller.id,
                    ip_address, user_agent, {"nombre": taller.nombre, "dias_trial": dias_trial})

        return taller

    def obtener_taller(self, taller_id: int) -> Taller | None:
        """Obtiene un taller por ID."""
        return self.taller_repo.get_by_id(taller_id)

    def listar_talleres(self) -> list[Taller]:
        """Lista todos los talleres."""
        return self.taller_repo.get_all()

    def actualizar_taller(self, taller_id: int, nombre: str | None, nit: str | None,
                          direccion: str | None, telefono: str | None,
                          updated_by: int, ip_address: str, user_agent: str) -> Taller:
        """
        Actualiza datos de un taller.
        Raises ValueError si el taller no existe.
        Raises ValueError si el nuevo nombre ya está en uso por otro taller.
        """
        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")

        if nombre is not None:
            nombre = nombre.strip()
            existing = self.taller_repo.get_by_nombre(nombre)
            if existing and existing.id != taller_id:
                raise ValueError("Ya existe un taller con ese nombre")
            taller.nombre = nombre

        if nit is not None:
            taller.nit = nit
        if direccion is not None:
            taller.direccion = direccion
        if telefono is not None:
            taller.telefono = telefono

        taller = self.taller_repo.update(taller)

        self._audit(updated_by, taller.id, AuditAction.TALLER_UPDATE, "taller", taller.id,
                    ip_address, user_agent, {"nombre": taller.nombre})

        return taller

    def desactivar_taller(self, taller_id: int, updated_by: int,
                          ip_address: str, user_agent: str) -> Taller:
        """
        Desactiva un taller. No se puede desactivar el Taller_Default (ID=1).
        Raises ValueError si es el taller principal o no existe.
        """
        if taller_id == self.TALLER_DEFAULT_ID:
            raise ValueError("No se puede desactivar el taller principal")

        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")

        taller.activo = False
        taller = self.taller_repo.update(taller)

        self._audit(updated_by, taller.id, AuditAction.TALLER_DEACTIVATE, "taller", taller.id,
                    ip_address, user_agent, {"nombre": taller.nombre})

        return taller

    # -------------------------------------------------------------------------
    # Ciclo de vida del taller
    # -------------------------------------------------------------------------

    # Mapa de estado → acción de audit log
    _ESTADO_AUDIT_ACTION: dict[EstadoTaller, AuditAction] = {
        EstadoTaller.ACTIVO: AuditAction.TALLER_ACTIVATE,
        EstadoTaller.SUSPENDIDO: AuditAction.TALLER_SUSPEND,
        EstadoTaller.CANCELADO: AuditAction.TALLER_CANCEL,
        EstadoTaller.TRIAL: AuditAction.TALLER_UPDATE,
    }

    def cambiar_estado(self, taller_id: int, nuevo_estado: EstadoTaller,
                       updated_by: int, ip_address: str, user_agent: str) -> Taller:
        """
        Cambia el estado del taller validando que no sea igual al actual.
        Registra fecha_suspension / fecha_cancelacion según corresponda.
        """
        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")

        if taller.estado == nuevo_estado:
            raise ValueError("El taller ya se encuentra en el estado especificado")

        ahora = datetime.now(timezone.utc)
        estado_anterior = taller.estado

        taller.estado = nuevo_estado

        if nuevo_estado == EstadoTaller.SUSPENDIDO:
            taller.fecha_suspension = ahora
        elif nuevo_estado == EstadoTaller.CANCELADO:
            taller.fecha_cancelacion = ahora

        self.taller_repo.update(taller)

        accion = self._ESTADO_AUDIT_ACTION.get(nuevo_estado, AuditAction.TALLER_UPDATE)
        self._audit(updated_by, taller.id, accion, "taller", taller.id,
                    ip_address, user_agent,
                    {"estado_anterior": str(estado_anterior), "estado_nuevo": str(nuevo_estado)})

        return taller

    # -------------------------------------------------------------------------
    # Bloqueo de emergencia
    # -------------------------------------------------------------------------

    def _invalidar_tokens_taller(self, taller_id: int, motivo: str) -> None:
        """Invalida todos los tokens JWT activos de todos los usuarios del taller."""
        usuarios = self.db.query(User).filter(
            User.taller_id == taller_id,
            User.is_active == True,
        ).all()

        ahora = datetime.now(timezone.utc)
        for usuario in usuarios:
            # Insertar un token centinela con jti único para forzar rechazo
            # El middleware verifica blacklist por jti; aquí invalidamos
            # todos los tokens existentes del usuario marcándolos en blacklist.
            tokens_activos = self.db.query(TokenBlacklist).filter(
                TokenBlacklist.user_id == usuario.id,
                TokenBlacklist.expires_at > ahora,
            ).all()
            # Marcar tokens existentes ya está en blacklist — agregar entrada
            # de bloqueo masivo con jti especial por usuario
            entrada = TokenBlacklist(
                jti=f"block_{usuario.id}_{int(ahora.timestamp())}",
                token_type="access",
                user_id=usuario.id,
                expires_at=ahora + timedelta(days=30),
                reason=motivo,
            )
            self.db.add(entrada)

        self.db.flush()

    def activar_bloqueo_emergencia(self, taller_id: int, motivo: str,
                                    updated_by: int, ip_address: str,
                                    user_agent: str) -> Taller:
        """
        Bloqueo inmediato de emergencia. Invalida todos los tokens del taller.
        No altera el estado de suscripción del taller.
        """
        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")

        if taller.bloqueado_emergencia:
            raise ValueError("El taller ya se encuentra bloqueado de emergencia")

        ahora = datetime.now(timezone.utc)
        taller.bloqueado_emergencia = True
        taller.fecha_bloqueo_emergencia = ahora
        taller.motivo_bloqueo_emergencia = motivo
        self.taller_repo.update(taller)

        self._invalidar_tokens_taller(taller_id, f"emergency_block: {motivo}")

        self._audit(updated_by, taller.id, AuditAction.TALLER_EMERGENCY_BLOCK, "taller", taller.id,
                    ip_address, user_agent, {"motivo": motivo})

        return taller

    def levantar_bloqueo_emergencia(self, taller_id: int,
                                     updated_by: int, ip_address: str,
                                     user_agent: str) -> Taller:
        """Levanta el bloqueo de emergencia y limpia los campos asociados."""
        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")

        if not taller.bloqueado_emergencia:
            raise ValueError("El taller no se encuentra bloqueado de emergencia")

        taller.bloqueado_emergencia = False
        taller.fecha_bloqueo_emergencia = None
        taller.motivo_bloqueo_emergencia = None
        self.taller_repo.update(taller)

        self._audit(updated_by, taller.id, AuditAction.TALLER_EMERGENCY_UNBLOCK, "taller", taller.id,
                    ip_address, user_agent, {})

        return taller

    # -------------------------------------------------------------------------
    # Métricas
    # -------------------------------------------------------------------------

    def obtener_metricas(self, taller_id: int) -> dict:
        """
        Retorna métricas operativas del taller (solo conteos).
        Calcula dias_restantes_trial si el taller está en TRIAL.
        """
        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")

        metricas = self.taller_repo.get_metricas(taller_id)
        metricas["taller_id"] = taller_id
        metricas["fecha_ultimo_acceso"] = self.taller_repo.get_ultimo_acceso(taller_id)

        return metricas

    def obtener_metricas_globales(self) -> dict:
        """Retorna métricas agregadas de toda la plataforma."""
        return self.taller_repo.get_metricas_globales()

    # -------------------------------------------------------------------------
    # Recursos
    # -------------------------------------------------------------------------

    def obtener_recursos(self, taller_id: int) -> dict:
        """
        Calcula almacenamiento usado recorriendo uploads/talleres/{taller_id}/.
        Retorna 0 bytes si la ruta no existe.
        """
        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")

        ruta = os.path.join("uploads", "talleres", str(taller_id))
        total_bytes = 0

        if os.path.exists(ruta):
            for dirpath, _, filenames in os.walk(ruta):
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    try:
                        total_bytes += os.path.getsize(fpath)
                    except OSError:
                        pass

        metricas = self.taller_repo.get_metricas(taller_id)

        return {
            "taller_id": taller_id,
            "almacenamiento_bytes": total_bytes,
            "almacenamiento_mb": round(total_bytes / (1024 * 1024), 2),
            "tickets_mes_actual": metricas["tickets_mes_actual"],
            "limite_tickets_mes": None,  # se llenará cuando exista el módulo de planes
        }

    # -------------------------------------------------------------------------
    # Gestión de usuarios por taller
    # -------------------------------------------------------------------------

    def crear_admin_taller(self, taller_id: int, username: str, email: str,
                            password: str, nombre_completo: str | None,
                            created_by: int, ip_address: str,
                            user_agent: str) -> User:
        """
        Crea el primer usuario ADMIN de un taller.
        El taller_id siempre viene del path, nunca del body.
        No se puede crear usuarios en talleres CANCELADOS.
        """
        from app.modelos.role import Role
        from app.seguridad.password_hasher import PasswordHasher

        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")

        if taller.estado == EstadoTaller.CANCELADO:
            raise ValueError("No se pueden crear usuarios en un taller cancelado")

        # Verificar duplicados
        existente_username = self.db.query(User).filter(User.username == username).first()
        if existente_username:
            raise ValueError(f"El username '{username}' ya existe")

        existente_email = self.db.query(User).filter(User.email == email).first()
        if existente_email:
            raise ValueError(f"El email '{email}' ya está registrado")

        # Obtener rol ADMIN
        rol_admin = self.db.query(Role).filter(Role.name == "ADMIN").first()
        if not rol_admin:
            raise ValueError("El rol ADMIN no existe en el sistema")

        hasher = PasswordHasher()
        password_hash = hasher.hash_password(password)

        usuario = User(
            taller_id=taller_id,
            username=username,
            email=email,
            password_hash=password_hash,
            nombre_completo=nombre_completo,
            is_active=True,
        )
        usuario.roles = [rol_admin]
        self.db.add(usuario)
        self.db.flush()

        self._audit(created_by, taller_id, AuditAction.USER_CREATE, "user", usuario.id,
                    ip_address, user_agent,
                    {"username": username, "taller_id": taller_id, "rol": "ADMIN"})

        return usuario

    def forzar_reset_password(self, taller_id: int, usuario_id: int,
                               updated_by: int, ip_address: str,
                               user_agent: str) -> str:
        """
        Invalida tokens del usuario y genera token de reset de un solo uso (24h).
        Verifica que el usuario pertenezca al taller del path.
        """
        usuario = obtener_recurso_del_taller(
            self.db,
            User,
            usuario_id,
            taller_id,
            "Usuario",
        )

        # Invalidar tokens activos del usuario
        ahora = datetime.now(timezone.utc)
        entrada = TokenBlacklist(
            jti=f"reset_{usuario_id}_{int(ahora.timestamp())}",
            token_type="access",
            user_id=usuario_id,
            expires_at=ahora + timedelta(days=1),
            reason="password_reset_forced",
        )
        self.db.add(entrada)

        # Invalidar tokens de reset anteriores
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == usuario_id,
            PasswordResetToken.used == False,
        ).update({"used": True}, synchronize_session=False)

        # Generar nuevo token de reset (24h)
        token_value = secrets.token_hex(32)
        reset_token = PasswordResetToken(
            user_id=usuario_id,
            token=token_value,
            expires_at=ahora + timedelta(hours=24),
        )
        self.db.add(reset_token)
        self.db.flush()

        self._audit(updated_by, taller_id, AuditAction.PASSWORD_RESET_FORCED, "user", usuario_id,
                    ip_address, user_agent, {"taller_id": taller_id})

        return token_value

    def forzar_reset_password_masivo(self, taller_id: int,
                                      updated_by: int, ip_address: str,
                                      user_agent: str) -> int:
        """
        Invalida tokens de todos los usuarios del taller.
        Retorna la cantidad de usuarios afectados.
        """
        usuarios = self.db.query(User).filter(
            User.taller_id == taller_id,
            User.is_active == True,
        ).all()

        ahora = datetime.now(timezone.utc)
        for usuario in usuarios:
            entrada = TokenBlacklist(
                jti=f"mass_reset_{usuario.id}_{int(ahora.timestamp())}",
                token_type="access",
                user_id=usuario.id,
                expires_at=ahora + timedelta(days=1),
                reason="password_reset_mass",
            )
            self.db.add(entrada)

        self.db.flush()

        self._audit(updated_by, taller_id, AuditAction.PASSWORD_RESET_MASS, "taller", taller_id,
                    ip_address, user_agent,
                    {"usuarios_afectados": len(usuarios), "taller_id": taller_id})

        return len(usuarios)

    # -------------------------------------------------------------------------
    # Seguridad y auditoría
    # -------------------------------------------------------------------------

    def obtener_intentos_fallidos(self, taller_id: int, desde: datetime | None,
                                   page: int, page_size: int) -> list:
        """
        Retorna intentos de login fallidos del taller desde Audit_Log,
        ordenados por timestamp descendente con paginación.
        """
        from app.modelos.audit_log import AuditLog

        query = self.db.query(AuditLog).filter(
            AuditLog.taller_id == taller_id,
            AuditLog.action == AuditAction.LOGIN_FAILED,
        )

        if desde:
            query = query.filter(AuditLog.timestamp >= desde)

        total = query.count()
        registros = (
            query.order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return registros

    def obtener_auditoria_global(self, taller_id: int | None, user_id: int | None,
                                  accion: str | None, desde: datetime | None,
                                  hasta: datetime | None, page: int,
                                  page_size: int) -> list:
        """
        Auditoría cruzada global con filtros opcionales.
        Máximo 100 registros por página, ordenados por timestamp descendente.
        """
        from app.modelos.audit_log import AuditLog

        if page_size > 100:
            page_size = 100

        if desde and hasta and desde > hasta:
            raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")

        query = self.db.query(AuditLog)

        if taller_id is not None:
            query = query.filter(AuditLog.taller_id == taller_id)
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if accion:
            query = query.filter(AuditLog.action == accion)
        if desde:
            query = query.filter(AuditLog.timestamp >= desde)
        if hasta:
            query = query.filter(AuditLog.timestamp <= hasta)

        return (
            query.order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    def enviar_notificacion_masiva(
        self,
        titulo: str,
        mensaje: str,
        solo_admins: bool,
        talleres_ids: list[int] | None,
        created_by: int,
        ip_address: str,
        user_agent: str,
    ) -> dict:
        """
        Envía una notificación masiva a usuarios de talleres.

        Args:
            titulo: Título de la notificación (5-200 caracteres)
            mensaje: Mensaje de la notificación (10-500 caracteres)
            solo_admins: Si True, solo envía a usuarios ADMIN. Si False, a todos los usuarios activos
            talleres_ids: Lista de IDs de talleres específicos. Si None, envía a todos los talleres activos
            created_by: ID del SUPER_ADMIN que envía la notificación
            ip_address: IP del cliente
            user_agent: User agent del cliente

        Returns:
            Dict con estadísticas del envío:
            {
                "notificaciones_enviadas": int,
                "talleres_afectados": int,
                "usuarios_notificados": int,
                "detalles": {"taller_1": 3, "taller_2": 5, ...}
            }

        Raises:
            ValueError: Si no hay talleres activos o usuarios para notificar
        """
        from app.modelos.notificacion import Notificacion, TipoNotificacion
        from app.modelos.role import Role
        from app.modelos.user_role import UserRole

        # 1. Obtener talleres objetivo
        query_talleres = self.db.query(Taller).filter(Taller.estado == EstadoTaller.ACTIVO)
        if talleres_ids:
            query_talleres = query_talleres.filter(Taller.id.in_(talleres_ids))
        talleres = query_talleres.all()

        if not talleres:
            raise ValueError("No hay talleres activos para enviar notificaciones")

        # 2. Obtener usuarios objetivo
        query_usuarios = self.db.query(User).filter(
            User.is_active == True,
            User.taller_id.in_([t.id for t in talleres])
        )

        # Si solo_admins, filtrar por rol ADMIN
        if solo_admins:
            role_admin = self.db.query(Role).filter(Role.name == "ADMIN").first()
            if role_admin:
                user_ids_admin = self.db.query(UserRole.user_id).filter(
                    UserRole.role_id == role_admin.id
                ).all()
                user_ids_admin = [uid[0] for uid in user_ids_admin]
                query_usuarios = query_usuarios.filter(User.id.in_(user_ids_admin))

        usuarios = query_usuarios.all()

        if not usuarios:
            raise ValueError("No hay usuarios activos para notificar")

        # 3. Crear notificaciones
        notificaciones_creadas = 0
        talleres_afectados = set()
        detalles = {}

        for usuario in usuarios:
            notificacion = Notificacion(
                taller_id=usuario.taller_id,
                destinatario_user_id=usuario.id,
                tipo=TipoNotificacion.MENSAJE_PLATAFORMA,
                titulo=titulo,
                mensaje=mensaje,
                leida=False,
                referencia_id=None,
            )
            self.db.add(notificacion)
            notificaciones_creadas += 1
            talleres_afectados.add(usuario.taller_id)

            # Contar por taller
            taller_key = f"taller_{usuario.taller_id}"
            detalles[taller_key] = detalles.get(taller_key, 0) + 1

        self.db.flush()

        # 4. Registrar en audit log
        self._audit(
            user_id=created_by,
            taller_id=None,  # SUPER_ADMIN no tiene taller
            action=AuditAction.NOTIFICACION_MASIVA_ENVIADA,
            resource_type="notificacion_masiva",
            resource_id=None,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "titulo": titulo,
                "mensaje": mensaje[:100],  # Solo primeros 100 caracteres
                "solo_admins": solo_admins,
                "talleres_ids": talleres_ids,
                "notificaciones_enviadas": notificaciones_creadas,
                "talleres_afectados": len(talleres_afectados),
            },
        )

        return {
            "notificaciones_enviadas": notificaciones_creadas,
            "talleres_afectados": len(talleres_afectados),
            "usuarios_notificados": len(usuarios),
            "detalles": detalles,
        }

    def importar_bd_desde_sql(
        self,
        taller_id: int,
        sql_file_path: str,
        created_by: int,
        ip_address: str,
        user_agent: str
    ) -> dict:
        """
        Importa datos desde un archivo SQL (backup de mono-tenant) al taller.
        
        Este método:
        1. Lee el archivo SQL
        2. Crea una BD temporal usando SQL directo
        3. Ejecuta el script de migración Python
        4. Mapea los datos al taller_id especificado
        5. Registra en audit log
        
        Args:
            taller_id: ID del taller destino
            sql_file_path: Ruta al archivo SQL
            created_by: ID del SUPER_ADMIN que ejecuta la importación
            ip_address: IP del cliente
            user_agent: User agent del cliente
            
        Returns:
            dict con estadísticas de la importación
            
        Raises:
            ValueError: Si el taller no existe o el archivo no es válido
        """
        import os
        from sqlalchemy import create_engine, text
        
        # Verificar que el taller existe
        taller = self.taller_repo.get_by_id(taller_id)
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")
        
        # Verificar que el archivo existe
        if not os.path.exists(sql_file_path):
            raise ValueError(f"Archivo SQL no encontrado: {sql_file_path}")
        
        # Crear una BD temporal para restaurar el backup
        temp_db_name = f"temp_import_{taller_id}_{secrets.token_hex(4)}"
        
        # Obtener URL de conexión desde variables de entorno
        import os as env_os
        db_url = env_os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/taller_db")
        # Cambiar a la BD postgres (default) para crear la temporal
        base_url = db_url.rsplit('/', 1)[0]
        postgres_url = f"{base_url}/postgres"
        
        try:
            # 1. Crear BD temporal usando SQL directo
            engine_postgres = create_engine(postgres_url.replace('+psycopg2', ''))
            with engine_postgres.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text(f"CREATE DATABASE {temp_db_name}"))
            engine_postgres.dispose()
            
            # 2. Restaurar backup en BD temporal
            # Leer y limpiar el SQL (remover comandos especiales de pg_dump)
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Remover comandos especiales de pg_dump que no son SQL estándar
            lines_to_remove = [
                '\\connect',
                '\\unrestrict',
                'SET default_table_access_method',
                'SET default_tablespace',
                'SET row_security',
                'SET check_function_bodies',
                'SET xmloption',
                'SET client_min_messages',
                'SET search_path',
            ]
            
            sql_lines = sql_content.split('\n')
            cleaned_lines = []
            for line in sql_lines:
                # Saltar líneas con comandos especiales
                skip = False
                for pattern in lines_to_remove:
                    if pattern in line:
                        skip = True
                        break
                if not skip:
                    cleaned_lines.append(line)
            
            # Ejecutar el SQL limpio statement por statement
            temp_engine = create_engine(f"{base_url}/{temp_db_name}".replace('+psycopg2', ''))
            try:
                # Usar AUTOCOMMIT para que cada statement se ejecute independientemente
                with temp_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                    # Deshabilitar triggers temporalmente
                    conn.execute(text("SET session_replication_role = 'replica';"))
                    
                    # Dividir el SQL en statements individuales
                    # Manejar bloques COPY que tienen múltiples líneas
                    statements = []
                    current_statement = []
                    in_copy_block = False
                    
                    for line in cleaned_lines:
                        # Saltar líneas vacías y comentarios puros
                        if not line.strip() or line.strip().startswith('--'):
                            continue
                        
                        # Detectar inicio de bloque COPY
                        if 'COPY ' in line and ' FROM stdin;' in line:
                            in_copy_block = True
                            current_statement.append(line)
                            continue
                        
                        # Detectar fin de bloque COPY
                        if in_copy_block and line.strip() == '\\.':
                            current_statement.append(line)
                            in_copy_block = False
                            statement = '\n'.join(current_statement)
                            if statement.strip():
                                statements.append(statement)
                            current_statement = []
                            continue
                        
                        # Si estamos en un bloque COPY, agregar la línea sin procesar
                        if in_copy_block:
                            current_statement.append(line)
                            continue
                        
                        # Procesamiento normal para statements que no son COPY
                        # Remover comentarios inline (-- al final de línea)
                        if '--' in line:
                            line = line.split('--')[0]
                        
                        # Solo agregar si la línea tiene contenido después de limpiar
                        if line.strip():
                            current_statement.append(line)
                        
                        # Si la línea termina con ;, es el fin del statement
                        if line.strip().endswith(';'):
                            statement = '\n'.join(current_statement)
                            if statement.strip():
                                statements.append(statement)
                            current_statement = []
                    
                    # Agregar el último statement si existe
                    if current_statement:
                        statement = '\n'.join(current_statement)
                        if statement.strip():
                            statements.append(statement)
                    
                    # Ejecutar cada statement individualmente
                    total_statements = len(statements)
                    print(f"[IMPORTAR] Total de statements a ejecutar: {total_statements}")
                    
                    for i, statement in enumerate(statements):
                        try:
                            # Log cada 100 statements para no saturar
                            if i % 100 == 0:
                                print(f"[IMPORTAR] Ejecutando statement {i+1}/{total_statements}")
                            
                            conn.execute(text(statement))
                        except Exception as e:
                            # Ignorar errores de objetos que ya existen
                            error_msg = str(e).lower()
                            if 'already exists' not in error_msg and 'duplicate' not in error_msg:
                                # Log el error con el statement que falló (primeros 200 caracteres)
                                statement_preview = statement[:200].replace('\n', ' ')
                                print(f"[IMPORTAR] Error en statement {i+1}: {str(e)[:150]}")
                                print(f"[IMPORTAR] Statement: {statement_preview}...")
                                # No lanzar excepción, continuar con el siguiente statement
                    
                    # Rehabilitar triggers
                    conn.execute(text("SET session_replication_role = 'origin';"))
            finally:
                temp_engine.dispose()
            
            # 3. Ejecutar script de migración
            from app.utils.importar_mono_tenant import importar_desde_bd_temporal
            
            resultado = importar_desde_bd_temporal(
                db=self.db,
                taller_id=taller_id,
                temp_db_name=temp_db_name
            )
            
            # 4. Registrar en audit log
            self._audit(
                user_id=created_by,
                taller_id=taller_id,
                action=AuditAction.TALLER_UPDATE,
                resource_type="taller_importacion",
                resource_id=taller_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "archivo": os.path.basename(sql_file_path),
                    "usuarios_importados": resultado.get("usuarios", 0),
                    "clientes_importados": resultado.get("clientes", 0),
                    "vehiculos_importados": resultado.get("vehiculos", 0),
                    "tickets_importados": resultado.get("tickets", 0),
                }
            )
            
            return resultado
            
        finally:
            # Limpiar BD temporal usando SQL directo
            try:
                engine_postgres = create_engine(postgres_url.replace('+psycopg2', ''))
                with engine_postgres.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                    # Terminar conexiones activas
                    conn.execute(text(f"""
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = '{temp_db_name}'
                        AND pid <> pg_backend_pid()
                    """))
                    # Eliminar BD
                    conn.execute(text(f"DROP DATABASE IF EXISTS {temp_db_name}"))
                engine_postgres.dispose()
            except Exception as e:
                # No fallar si no se puede eliminar
                print(f"Warning: No se pudo eliminar BD temporal {temp_db_name}: {e}")
