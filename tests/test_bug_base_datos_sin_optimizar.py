"""
Test de Exploración: Base de Datos Sin Optimizar (Bug Condition)

**Validates: Requirements 1.7, 1.8, 1.9, 1.10**

CRÍTICO: Este test DEBE FALLAR en código sin corregir - el fallo confirma que el bug existe.
NO intentar corregir el test o el código cuando falle.

Este test codifica el comportamiento esperado - validará la corrección cuando pase después
de la implementación.

OBJETIVO: Demostrar que consultas son lentas y no usan índices compuestos.
"""

import os
import time
from datetime import datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import DATABASE_URL
from app.modelos.ticket import Ticket
from app.repositorios.ticket_repository import TicketRepository


class TestBaseDatosSinOptimizar:
    """
    Property 1: Bug Condition - Consultas Lentas Sin Índices

    Este test verifica que las consultas actuales no usan índices compuestos y son lentas.
    En código SIN CORREGIR, este test DEBE FALLAR.
    """

    @pytest.fixture(scope="class")
    def db_engine(self):
        """Motor de base de datos para testing"""
        # Usar DATABASE_URL de test si está disponible
        test_db_url = os.getenv("TEST_DATABASE_URL", DATABASE_URL)
        engine = create_engine(test_db_url)
        return engine

    @pytest.fixture(scope="class")
    def db_session(self, db_engine):
        """Sesión de base de datos para testing"""
        SessionLocal = sessionmaker(bind=db_engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_consulta_tickets_por_estado_fecha_usa_seq_scan(self, db_engine):
        """
        Verifica que consultas filtradas por estado+fecha usan Sequential Scan.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay índice compuesto idx_tickets_estado_fecha)
        """
        # Query típica: buscar tickets abiertos de los últimos 30 días
        fecha_desde = (datetime.now() - timedelta(days=30)).isoformat()

        query = text(
            """
            EXPLAIN ANALYZE
            SELECT * FROM tickets
            WHERE estado = 'ABIERTO'
            AND fecha_ingreso >= :fecha_desde
            ORDER BY fecha_ingreso DESC
        """
        )

        with db_engine.connect() as conn:
            result = conn.execute(query, {"fecha_desde": fecha_desde})
            explain_output = "\n".join([row[0] for row in result])

        print("\n" + "=" * 80)
        print("EXPLAIN ANALYZE - Consulta por Estado + Fecha")
        print("=" * 80)
        print(explain_output)
        print("=" * 80 + "\n")

        # En código sin corregir, NO debería usar el índice compuesto
        # Este test FALLA porque el índice no existe
        tiene_index_compuesto = "idx_tickets_estado_fecha" in explain_output

        assert tiene_index_compuesto, (
            f"Bug Condition: Query debería usar índice compuesto idx_tickets_estado_fecha "
            f"para optimizar búsqueda por estado+fecha, pero no lo usa. "
            f"En código sin corregir, este índice no existe. "
            f"Si este test falla, confirma que el bug existe (sin índice compuesto).\n\n"
            f"EXPLAIN output:\n{explain_output}"
        )

        print("✓ Query usa índice compuesto idx_tickets_estado_fecha (comportamiento correcto)")

    def test_latencia_consulta_tickets_filtrados_mayor_500ms(self, db_session):
        """
        Verifica que consultas filtradas tienen latencia >500ms.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que consultas son lentas sin índices)

        NOTA: Este test puede pasar si la base de datos tiene pocos registros.
        Para reproducir el bug, la BD debe tener al menos 1000 tickets.
        """
        # Primero verificar si hay suficientes datos
        total_tickets = db_session.query(Ticket).count()

        if total_tickets < 100:
            pytest.skip(
                f"Base de datos tiene solo {total_tickets} tickets. "
                f"Se necesitan al menos 100 tickets para medir latencia significativa. "
                f"Este test es más relevante con >1000 tickets."
            )

        # Medir latencia de consulta filtrada
        fecha_desde = datetime.now() - timedelta(days=30)

        start_time = time.time()
        tickets = (
            db_session.query(Ticket)
            .filter(Ticket.estado == "ABIERTO")
            .filter(Ticket.fecha_ingreso >= fecha_desde)
            .order_by(Ticket.fecha_ingreso.desc())
            .all()
        )
        end_time = time.time()

        latencia_ms = (end_time - start_time) * 1000

        print(f"\n{'='*80}")
        print("MEDICIÓN DE LATENCIA - Consulta Filtrada")
        print(f"{'='*80}")
        print(f"Total tickets en BD: {total_tickets}")
        print(f"Tickets retornados: {len(tickets)}")
        print(f"Latencia: {latencia_ms:.2f}ms")
        print(f"{'='*80}\n")

        # En código CORREGIDO, esperamos latencia <50ms con índices
        # En código sin corregir, la latencia será mayor
        if total_tickets >= 1000:
            assert latencia_ms < 50, (
                f"Bug Condition: Con {total_tickets} tickets y índices optimizados, "
                f"la latencia debería ser <50ms, pero fue {latencia_ms:.2f}ms. "
                f"En código sin corregir (sin índices), la latencia es >500ms. "
                f"Si este test falla, confirma que el bug existe."
            )
            print(f"✓ Latencia optimizada: {latencia_ms:.2f}ms < 50ms (comportamiento correcto)")
        else:
            print(
                f"⚠ Advertencia: Solo {total_tickets} tickets en BD. "
                f"Latencia medida: {latencia_ms:.2f}ms. "
                f"Este test es más confiable con >1000 tickets para detectar diferencias significativas."
            )

    def test_n_plus_one_queries_al_cargar_relaciones(self, db_session, db_engine):
        """
        Verifica que cargar tickets con relaciones ejecuta N+1 queries.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no se usa eager loading)
        """
        # Habilitar logging de SQL para contar queries
        from sqlalchemy import event

        query_count = {"count": 0}

        def count_queries(conn, cursor, statement, parameters, context, executemany):
            query_count["count"] += 1

        event.listen(db_engine, "before_cursor_execute", count_queries)

        try:
            # Cargar tickets (sin eager loading)
            tickets = db_session.query(Ticket).limit(10).all()

            initial_query_count = query_count["count"]

            # Acceder a relaciones (esto debería disparar queries adicionales)
            # Nota: En el código actual, las relaciones no están definidas en el modelo
            # pero el patrón N+1 ocurre cuando se cargan procesos, repuestos, fotos

            # Simular acceso a relaciones como lo haría el código real
            from app.modelos.ticket_foto import TicketFoto
            from app.modelos.ticket_proceso import TicketProceso
            from app.modelos.ticket_repuesto import TicketRepuesto

            for ticket in tickets:
                # Cada una de estas consultas es una query adicional (N+1 problem)
                procesos = (
                    db_session.query(TicketProceso)
                    .filter(TicketProceso.ticket_id == ticket.id)
                    .all()
                )
                repuestos = (
                    db_session.query(TicketRepuesto)
                    .filter(TicketRepuesto.ticket_id == ticket.id)
                    .all()
                )
                fotos = db_session.query(TicketFoto).filter(TicketFoto.ticket_id == ticket.id).all()

            final_query_count = query_count["count"]
            additional_queries = final_query_count - initial_query_count
            expected_n_plus_one = len(tickets) * 3  # 3 relaciones por ticket

            print(f"\n{'='*80}")
            print("CONTEO DE QUERIES - N+1 Problem")
            print(f"{'='*80}")
            print(f"Tickets cargados: {len(tickets)}")
            print(f"Queries iniciales: {initial_query_count}")
            print(f"Queries adicionales: {additional_queries}")
            print(f"Total queries: {final_query_count}")
            print(f"{'='*80}\n")

            # En código CORREGIDO con eager loading, esperamos 1 query inicial
            # que carga todo con JOINs, sin queries adicionales
            # En código sin corregir, esperamos N+1 queries
            assert additional_queries == 0, (
                f"Bug Condition: Con eager loading, cargar {len(tickets)} tickets con relaciones "
                f"debería ejecutar 0 queries adicionales (todo en 1 query con JOINs), "
                f"pero ejecutó {additional_queries} queries adicionales. "
                f"En código sin corregir, esto es N+1 problem ({expected_n_plus_one} queries). "
                f"Si este test falla, confirma que el bug existe."
            )

            print("✓ Eager loading implementado: 0 queries adicionales (comportamiento correcto)")

        finally:
            event.remove(db_engine, "before_cursor_execute", count_queries)

    def test_endpoint_tickets_sin_paginacion_retorna_todos(self, db_session):
        """
        Verifica que get_all() sin parámetros retorna todos los registros.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que no hay paginación obligatoria)
        """
        total_tickets = db_session.query(Ticket).count()

        if total_tickets == 0:
            pytest.skip("No hay tickets en la base de datos para probar")

        # Usar el repositorio como lo haría el código real
        repo = TicketRepository(db_session)

        # Llamar get_all sin límite explícito
        tickets = repo.get_all()

        print(f"\n{'='*80}")
        print("VERIFICACIÓN DE PAGINACIÓN")
        print(f"{'='*80}")
        print(f"Total tickets en BD: {total_tickets}")
        print(f"Tickets retornados por get_all(): {len(tickets)}")
        print(f"{'='*80}\n")

        # En código CORREGIDO con paginación, esperamos máximo 50 registros
        # En código sin corregir, retorna todos los registros
        if total_tickets > 50:
            assert len(tickets) <= 50, (
                f"Bug Condition: Con paginación implementada, get_all() debería retornar "
                f"máximo 50 tickets, pero retornó {len(tickets)} de {total_tickets} totales. "
                f"En código sin corregir, retorna todos los registros sin límite. "
                f"Si este test falla, confirma que el bug existe."
            )
            print(
                f"✓ Paginación implementada: {len(tickets)} tickets <= 50 (comportamiento correcto)"
            )
        else:
            print(
                f"⚠ Advertencia: Solo {total_tickets} tickets en BD. "
                f"Este test es más relevante con >50 tickets para verificar paginación."
            )

    def test_no_existe_indice_compuesto_estado_fecha(self, db_engine):
        """
        Verifica que NO existe el índice compuesto idx_tickets_estado_fecha.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que el índice no fue creado)
        """
        query = text(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'tickets'
            AND indexname = 'idx_tickets_estado_fecha'
        """
        )

        with db_engine.connect() as conn:
            result = conn.execute(query)
            indices = list(result)

        print(f"\n{'='*80}")
        print("VERIFICACIÓN DE ÍNDICES - idx_tickets_estado_fecha")
        print(f"{'='*80}")

        if indices:
            for idx in indices:
                print(f"Índice encontrado: {idx[0]}")
                print(f"Definición: {idx[1]}")
        else:
            print("Índice NO encontrado (esperado en código sin corregir)")

        print(f"{'='*80}\n")

        # En código CORREGIDO, el índice DEBE existir
        # En código sin corregir, NO existe
        assert len(indices) > 0, (
            "Bug Condition: El índice idx_tickets_estado_fecha DEBE existir "
            "para optimizar consultas por estado+fecha, pero no fue encontrado. "
            "En código sin corregir, este índice no existe. "
            "Si este test falla, confirma que el bug existe."
        )

        print("✓ Índice idx_tickets_estado_fecha existe (comportamiento correcto)")
        print(f"  Definición: {indices[0][1]}")

    @given(
        estado=st.sampled_from(["ABIERTO", "EN_PROCESO", "FINALIZADO", "ENTREGADO"]),
        dias_atras=st.integers(min_value=1, max_value=90),
    )
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_consultas_sin_indices_son_lentas(self, estado, dias_atras, db_session):
        """
        Property-Based Test: Para cualquier combinación de estado y fecha,
        el sistema sin corregir ejecuta consultas sin índices compuestos.

        RESULTADO ESPERADO EN CÓDIGO SIN CORREGIR: FALLA
        (confirma que todas las consultas filtradas son ineficientes)
        """
        total_tickets = db_session.query(Ticket).count()

        if total_tickets < 10:
            pytest.skip(f"Solo {total_tickets} tickets en BD - test requiere más datos")

        fecha_desde = datetime.now() - timedelta(days=dias_atras)

        start_time = time.time()
        tickets = (
            db_session.query(Ticket)
            .filter(Ticket.estado == estado)
            .filter(Ticket.fecha_ingreso >= fecha_desde)
            .order_by(Ticket.fecha_ingreso.desc())
            .all()
        )
        end_time = time.time()

        latencia_ms = (end_time - start_time) * 1000

        print(f"\n✓ Property Test: estado={estado}, días_atrás={dias_atras}")
        print(f"  Tickets encontrados: {len(tickets)}")
        print(f"  Latencia: {latencia_ms:.2f}ms")

        # En código CORREGIDO con índices, las consultas deberían ser rápidas
        # La propiedad clave es que TODAS las consultas usan índices compuestos
        # sin importar los parámetros

        # Verificar que la consulta fue eficiente (latencia razonable)
        # Con índices, incluso con muchos datos, debería ser <100ms
        if total_tickets >= 100:
            assert latencia_ms < 100, (
                f"Property Bug Condition: Con índices optimizados, consulta con "
                f"estado={estado} y días_atrás={dias_atras} debería ser <100ms, "
                f"pero fue {latencia_ms:.2f}ms. "
                f"En código sin corregir (sin índices), las consultas son lentas. "
                f"Si este test falla, confirma que el bug existe."
            )

        print("  ✓ Consulta optimizada con índices")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TEST DE EXPLORACIÓN: BASE DE DATOS SIN OPTIMIZAR (Bug Condition)")
    print("=" * 80)
    print("\nCRÍTICO: Este test DEBE FALLAR en código sin corregir.")
    print("El fallo confirma que el bug existe (consultas lentas sin índices).")
    print("\nEste test validará la corrección cuando pase después de la implementación.")
    print("=" * 80 + "\n")

    pytest.main([__file__, "-v", "-s"])
