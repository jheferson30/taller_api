"""
Script de seed para datos de demostración.

Crea un taller de prueba completo con:
  - 1 taller activo con plan próximo a vencer (para ver el banner de renovación)
  - 1 usuario ADMIN del taller
  - 1 usuario MECANICO del taller
  - 1 mecánico vinculado al usuario MECANICO
  - 1 vehículo y 2 tickets (uno asignado al mecánico)
  - Notificaciones de prueba:
      * TICKET_ASIGNADO  → para el mecánico
      * RENOVACION_PLAN  → para el admin

Uso:
    python scripts/seed_demo.py

Credenciales creadas:
    ADMIN    → usuario: admin_demo    / contraseña: Demo1234!
    MECANICO → usuario: mecanico_demo / contraseña: Demo1234!

IMPORTANTE: Solo para desarrollo/demo. No ejecutar en producción.
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Agregar el directorio raíz al path para importar módulos de la app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.configuracion.base_datos import SessionLocal

# Importar TODOS los modelos para que SQLAlchemy resuelva las relaciones entre ellos
import app.modelos.app_config          # noqa: F401
import app.modelos.audit_log           # noqa: F401
import app.modelos.cita                # noqa: F401
import app.modelos.configuracion_taller  # noqa: F401
import app.modelos.mecanico            # noqa: F401
import app.modelos.movimiento_caja     # noqa: F401
import app.modelos.notificacion        # noqa: F401
import app.modelos.password_reset_token  # noqa: F401
import app.modelos.role                # noqa: F401
import app.modelos.taller              # noqa: F401
import app.modelos.ticket              # noqa: F401
import app.modelos.token_blacklist     # noqa: F401
import app.modelos.user                # noqa: F401
import app.modelos.user_role           # noqa: F401
import app.modelos.vehiculo            # noqa: F401

from app.modelos.taller import Taller, EstadoTaller
from app.modelos.user import User
from app.modelos.role import Role
from app.modelos.user_role import UserRole
from app.modelos.mecanico import Mecanico
from app.modelos.vehiculo import Vehiculo
from app.modelos.ticket import Ticket
from app.modelos.notificacion import Notificacion, TipoNotificacion
from app.seguridad.password_hasher import PasswordHasher

TALLER_NOMBRE = "Taller Demo Notificaciones"
ADMIN_USERNAME = "admin_demo"
MECANICO_USERNAME = "mecanico_demo"
# Contraseña de demo — configurable via SEED_DEMO_PASSWORD (solo para desarrollo)
PASSWORD = os.getenv("SEED_DEMO_PASSWORD", "Demo1234!")

hasher = PasswordHasher()


def limpiar_datos_previos(db: Session) -> None:
    """Elimina datos de demo previos usando SQL directo para evitar problemas de FK."""
    from sqlalchemy import text
    print("🧹 Limpiando datos de demo previos...")

    # Buscar el taller demo
    result = db.execute(text("SELECT id FROM talleres WHERE nombre = :nombre"), {"nombre": TALLER_NOMBRE})
    row = result.fetchone()
    if not row:
        print("   No hay datos previos. Continuando...")
        return

    taller_id = row[0]

    # Buscar usuarios demo
    user_ids = []
    for username in [ADMIN_USERNAME, MECANICO_USERNAME]:
        r = db.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username})
        u = r.fetchone()
        if u:
            user_ids.append(u[0])

    # Eliminar en orden correcto por FK usando SQL directo
    db.execute(text("DELETE FROM notificaciones WHERE taller_id = :tid"), {"tid": taller_id})
    db.execute(text("DELETE FROM tickets WHERE taller_id = :tid"), {"tid": taller_id})
    db.execute(text("DELETE FROM vehiculos WHERE taller_id = :tid"), {"tid": taller_id})
    db.execute(text("DELETE FROM mecanicos WHERE taller_id = :tid"), {"tid": taller_id})

    # Borrar TODOS los usuarios del taller (no solo los del demo)
    all_users = db.execute(text("SELECT id FROM users WHERE taller_id = :tid"), {"tid": taller_id})
    for u_row in all_users:
        db.execute(text("DELETE FROM user_roles WHERE user_id = :uid"), {"uid": u_row[0]})
    db.execute(text("DELETE FROM users WHERE taller_id = :tid"), {"tid": taller_id})

    # Eliminar configuracion_taller y el taller
    db.execute(text("DELETE FROM configuracion_taller WHERE taller_id = :tid"), {"tid": taller_id})
    db.execute(text("DELETE FROM talleres WHERE id = :tid"), {"tid": taller_id})

    db.commit()
    print("   ✅ Datos previos eliminados.")


def obtener_o_crear_rol(db: Session, nombre: str) -> Role:
    """Obtiene un rol existente o lo crea si no existe."""
    rol = db.query(Role).filter(Role.name == nombre).first()
    if not rol:
        rol = Role(name=nombre, description=f"Rol {nombre}")
        db.add(rol)
        db.flush()
        print(f"   Rol '{nombre}' creado.")
    return rol


def crear_taller(db: Session) -> Taller:
    """Crea el taller de demo con plan próximo a vencer (2 días)."""
    ahora = datetime.now(timezone.utc)
    taller = Taller(
        nombre=TALLER_NOMBRE,
        nit="900123456-7",
        direccion="Calle 123 # 45-67, Bogotá",
        telefono="3001234567",
        activo=True,
        estado=EstadoTaller.ACTIVO,
        fecha_inicio_trial=ahora - timedelta(days=28),
        # Plan vence en 2 días → activa el banner de RENOVACION_PLAN
        fecha_vencimiento_plan=ahora + timedelta(days=2),
    )
    db.add(taller)
    db.flush()
    print(f"   Taller '{taller.nombre}' creado (id={taller.id})")
    print(f"   Plan vence en: {taller.fecha_vencimiento_plan.strftime('%Y-%m-%d %H:%M UTC')}")
    return taller


def crear_usuario(db: Session, taller_id: int, username: str, email: str, nombre: str, rol: Role) -> User:
    """Crea un usuario y le asigna el rol indicado."""
    user = User(
        taller_id=taller_id,
        username=username,
        email=email,
        password_hash=hasher.hash_password(PASSWORD),
        is_active=True,
        nombre_completo=nombre,
    )
    db.add(user)
    db.flush()

    user_role = UserRole(user_id=user.id, role_id=rol.id)
    db.add(user_role)
    db.flush()

    print(f"   Usuario '{username}' creado (id={user.id}, rol={rol.name})")
    return user


def crear_mecanico(db: Session, taller_id: int, nombre: str) -> Mecanico:
    """Crea un mecánico en el taller."""
    mecanico = Mecanico(taller_id=taller_id, nombre=nombre, activo=True)
    db.add(mecanico)
    db.flush()
    print(f"   Mecánico '{nombre}' creado (id={mecanico.id})")
    return mecanico


def crear_vehiculo(db: Session, taller_id: int) -> Vehiculo:
    """Crea un vehículo de prueba."""
    vehiculo = Vehiculo(
        taller_id=taller_id,
        placa="ABC123",
        marca="Toyota",
        modelo="Corolla",
        anio=2020,
        color="Blanco",
        nombre_propietario="Carlos Pérez",
        telefono_propietario="3109876543",
    )
    db.add(vehiculo)
    db.flush()
    print(f"   Vehículo '{vehiculo.placa}' creado (id={vehiculo.id})")
    return vehiculo


def crear_ticket(db: Session, taller_id: int, vehiculo_id: int, mecanico_id: int, codigo: str, motivo: str) -> Ticket:
    """Crea un ticket de prueba."""
    ticket = Ticket(
        taller_id=taller_id,
        vehiculo_id=vehiculo_id,
        ticket_codigo=codigo,
        placa="ABC123",
        motivo_visita=motivo,
        estado="ABIERTO",
        recepcionado_por=ADMIN_USERNAME,
        mecanico_asignado_id=mecanico_id,
        anticipo_recibido=0,
    )
    db.add(ticket)
    db.flush()
    print(f"   Ticket '{codigo}' creado (id={ticket.id})")
    return ticket


def crear_notificaciones(db: Session, taller_id: int, admin_user_id: int, mecanico_user_id: int, ticket_id: int) -> None:
    """Crea las notificaciones de demo."""

    # Notificación para el MECANICO: ticket asignado
    notif_ticket = Notificacion(
        taller_id=taller_id,
        destinatario_user_id=mecanico_user_id,
        tipo=TipoNotificacion.TICKET_ASIGNADO,
        titulo="Nuevo ticket asignado",
        mensaje="Se te asignó el ticket TK-001: Cambio de aceite y filtros. Revisa los detalles.",
        leida=False,
        referencia_id=ticket_id,
    )
    db.add(notif_ticket)

    # Notificación para el ADMIN: renovación de plan (2 días restantes)
    notif_renovacion = Notificacion(
        taller_id=taller_id,
        destinatario_user_id=admin_user_id,
        tipo=TipoNotificacion.RENOVACION_PLAN,
        titulo="Plan próximo a vencer",
        mensaje="Tu plan vence en 2 días. Renueva ahora para no perder el acceso al sistema.",
        leida=False,
        referencia_id=taller_id,
    )
    db.add(notif_renovacion)

    # Segunda notificación para el MECANICO: otro ticket
    notif_ticket2 = Notificacion(
        taller_id=taller_id,
        destinatario_user_id=mecanico_user_id,
        tipo=TipoNotificacion.TICKET_ASIGNADO,
        titulo="Nuevo ticket asignado",
        mensaje="Se te asignó el ticket TK-002: Revisión de frenos y suspensión. Prioridad alta.",
        leida=False,
        referencia_id=ticket_id,
    )
    db.add(notif_ticket2)

    db.flush()
    print(f"   3 notificaciones creadas (2 para mecánico, 1 para admin)")


def main() -> None:
    print("\n" + "=" * 60)
    print("  SEED DEMO — Sistema de Notificaciones")
    print("=" * 60)

    db: Session = SessionLocal()
    try:
        limpiar_datos_previos(db)

        print("\n📦 Creando datos de demo...")

        # Roles
        rol_admin = obtener_o_crear_rol(db, "ADMIN")
        rol_mecanico = obtener_o_crear_rol(db, "MECANICO")

        # Taller
        taller = crear_taller(db)

        # Usuarios
        admin_user = crear_usuario(
            db, taller.id, ADMIN_USERNAME,
            "admin_demo@taller.com", "Admin Demo", rol_admin
        )
        mecanico_user = crear_usuario(
            db, taller.id, MECANICO_USERNAME,
            "mecanico_demo@taller.com", "Juan Mecánico", rol_mecanico
        )

        # Mecánico (entidad operativa vinculada al usuario)
        mecanico = crear_mecanico(db, taller.id, "Juan Mecánico")

        # Vehículo y tickets
        vehiculo = crear_vehiculo(db, taller.id)
        ticket = crear_ticket(
            db, taller.id, vehiculo.id, mecanico.id,
            "TK-001", "Cambio de aceite y filtros"
        )
        crear_ticket(
            db, taller.id, vehiculo.id, mecanico.id,
            "TK-002", "Revisión de frenos y suspensión"
        )

        # Notificaciones
        crear_notificaciones(db, taller.id, admin_user.id, mecanico_user.id, ticket.id)

        db.commit()

        print("\n" + "=" * 60)
        print("  ✅ SEED COMPLETADO")
        print("=" * 60)
        print("\n🔑 Credenciales de acceso:")
        print(f"   ADMIN    → usuario: {ADMIN_USERNAME:<20} contraseña: {PASSWORD}")
        print(f"   MECANICO → usuario: {MECANICO_USERNAME:<20} contraseña: {PASSWORD}")
        print("\n👁️  Qué verás al iniciar sesión:")
        print("   ADMIN    → Banner amarillo de renovación de plan (1 notif)")
        print("              Badge 🔔 con contador en 1")
        print("   MECANICO → Badge 🔔 con contador en 2 (2 tickets asignados)")
        print("\n🌐 Frontend: http://localhost:5173")
        print("   Backend:  http://localhost:8000/docs")
        print("=" * 60 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante el seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
