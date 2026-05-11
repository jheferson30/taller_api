"""
Módulo de jobs programados del sistema.

Contiene tareas automatizadas que se ejecutan en segundo plano:
- Limpieza de notificaciones leídas (diario a las 00:00)
- Verificación y rotación automática de clave JWT (diario a las 02:00)
- Flush de alertas de seguridad LOW acumuladas (cada 15 minutos)
"""

from app.jobs.scheduler import detener_scheduler, iniciar_scheduler

__all__ = ["iniciar_scheduler", "detener_scheduler"]
