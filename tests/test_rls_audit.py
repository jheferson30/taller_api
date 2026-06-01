"""
Tests for RLS Audit Script

**Validates: Requirements 6.2, 6.3, 6.4**

This test suite verifies that the RLS audit script correctly detects:
- CRITICAL: Queries on multi-tenant tables without taller_id filter
- HIGH: Route handlers without @require_auth decorator
- HIGH: Repository instantiation without taller_id parameter
"""

import os
import tempfile
from pathlib import Path

import pytest

from scripts.rls_audit import RLSAuditor, RLSViolation


class TestRLSAuditor:
    """Test suite for RLS auditor functionality."""

    @pytest.fixture
    def auditor(self):
        """Create a fresh RLSAuditor instance for each test."""
        return RLSAuditor()

    @pytest.fixture
    def temp_routes_dir(self):
        """Create a temporary directory for test route files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_detects_missing_taller_id_filter(self, auditor, temp_routes_dir):
        """
        Test that auditor detects queries on multi-tenant tables without taller_id filter.
        
        **Validates: Requirement 6.2**
        """
        # Create a test file with a violation
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modelos.ticket import Ticket

router = APIRouter()

@router.get("/tickets")
async def get_tickets(db: Session = Depends(get_db)):
    # CRITICAL: Missing taller_id filter
    tickets = db.query(Ticket).all()
    return tickets
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should detect the missing taller_id filter
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        assert len(critical_violations) >= 1
        assert any("Ticket" in v.description for v in critical_violations)
        assert any("taller_id filter" in v.description for v in critical_violations)

    def test_detects_missing_require_auth(self, auditor, temp_routes_dir):
        """
        Test that auditor detects route handlers without @require_auth decorator.
        
        **Validates: Requirement 6.3**
        """
        # Create a test file with a violation
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/data")
async def get_data(db: Session = Depends(get_db)):
    # HIGH: Missing @require_auth
    return {"data": "sensitive"}
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should detect the missing @require_auth
        high_violations = [v for v in violations if v.severity == "HIGH"]
        assert len(high_violations) >= 1
        assert any("@require_auth" in v.description for v in high_violations)

    def test_detects_repository_without_taller_id(self, auditor, temp_routes_dir):
        """
        Test that auditor detects repository instantiation without taller_id parameter.
        
        **Validates: Requirement 6.4**
        """
        # Create a test file with a violation
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.repositorios.ticket_repository import TicketRepository

router = APIRouter()

@router.get("/tickets")
async def get_tickets(db: Session = Depends(get_db)):
    # HIGH: Missing taller_id parameter
    repo = TicketRepository(db)
    return repo.get_all()
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should detect the missing taller_id parameter
        high_violations = [v for v in violations if v.severity == "HIGH"]
        assert len(high_violations) >= 1
        assert any("taller_id parameter" in v.description for v in high_violations)

    def test_no_violations_for_secure_endpoint(self, auditor, temp_routes_dir):
        """
        Test that auditor does not report violations for properly secured endpoints.
        """
        # Create a test file without violations
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.modelos.ticket import Ticket
from app.seguridad.dependencias import require_auth

router = APIRouter()

@router.get("/tickets")
@require_auth
async def get_tickets(request: Request, db: Session = Depends(get_db)):
    taller_id = request.state.taller_id
    tickets = db.query(Ticket).filter(Ticket.taller_id == taller_id).all()
    return tickets
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should not detect any violations
        assert len(violations) == 0

    def test_ignores_public_endpoints(self, auditor, temp_routes_dir):
        """
        Test that auditor ignores known public endpoints (webhooks, login, health).
        """
        # Create a test file with public endpoints
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter

router = APIRouter()

@router.post("/whatsapp/webhook")
async def webhook_handler():
    return {"status": "ok"}

@router.post("/login")
async def login():
    return {"token": "abc"}

@router.get("/health")
async def health():
    return {"status": "healthy"}
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should not detect violations for public endpoints
        missing_auth_violations = [
            v for v in violations if v.violation_type == "MISSING_AUTH"
        ]
        assert len(missing_auth_violations) == 0

    def test_detects_helper_function_without_taller_id(self, auditor, temp_routes_dir):
        """
        Test that auditor detects helper functions called without taller_id parameter.
        """
        # Create a test file with helper function violation
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modelos.movimiento_caja import MovimientoCaja

router = APIRouter()

def _base_query_dia(db: Session, fecha):
    return db.query(MovimientoCaja).filter(MovimientoCaja.fecha == fecha)

@router.get("/economia")
async def get_economia(db: Session = Depends(get_db)):
    # CRITICAL: Helper function called without taller_id
    result = _base_query_dia(db, "2024-01-01")
    return result
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should detect both the missing filter in helper and the missing param in call
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        assert len(critical_violations) >= 1

    def test_report_generation(self, auditor, temp_routes_dir):
        """
        Test that auditor generates a human-readable report.
        
        **Validates: Requirement 6.4**
        """
        # Create a test file with violations
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modelos.ticket import Ticket

router = APIRouter()

@router.get("/tickets")
async def get_tickets(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).all()
    return tickets
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))
        report = auditor.generate_report(violations)

        # Report should contain key information
        assert "RLS AUDIT REPORT" in report
        assert "Total violations:" in report
        assert "CRITICAL" in report or "HIGH" in report
        assert "RECOMMENDATIONS" in report

    def test_empty_report_for_clean_code(self, auditor, temp_routes_dir):
        """
        Test that auditor generates a clean report when no violations are found.
        """
        # Create a test file without violations
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.modelos.ticket import Ticket
from app.seguridad.dependencias import require_auth

router = APIRouter()

@router.get("/tickets")
@require_auth
async def get_tickets(request: Request, db: Session = Depends(get_db)):
    taller_id = request.state.taller_id
    tickets = db.query(Ticket).filter(Ticket.taller_id == taller_id).all()
    return tickets
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))
        report = auditor.generate_report(violations)

        # Report should indicate no violations
        assert "NO RLS VIOLATIONS FOUND" in report

    def test_scan_actual_routes_directory(self, auditor):
        """
        Test scanning the actual app/rutas/ directory.
        
        This test verifies that the auditor can scan the real codebase
        and detect violations as documented in the requirements.
        
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
        """
        routes_dir = "app/rutas"
        
        # Skip if routes directory doesn't exist (e.g., in isolated test environment)
        if not os.path.exists(routes_dir):
            pytest.skip(f"Routes directory {routes_dir} not found")

        violations = auditor.scan_routes(routes_dir)

        # The actual codebase should have violations (as documented in requirements)
        # We expect at least some violations to be detected
        assert isinstance(violations, list)
        
        # Verify violation structure
        for violation in violations:
            assert isinstance(violation, RLSViolation)
            assert violation.file_path.startswith("app/rutas/")
            assert violation.line_number > 0
            assert violation.severity in ["CRITICAL", "HIGH", "MEDIUM"]
            assert violation.violation_type in [
                "MISSING_TALLER_FILTER",
                "MISSING_AUTH",
                "MISSING_TALLER_PARAM",
            ]
            assert len(violation.description) > 0
            assert len(violation.code_snippet) > 0

    def test_detects_movimiento_caja_without_filter(self, auditor, temp_routes_dir):
        """
        Test detection of MovimientoCaja queries without taller_id filter.
        
        This specifically tests the economia_ruta.py violations (C-06).
        """
        test_file = temp_routes_dir / "economia_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modelos.movimiento_caja import MovimientoCaja

router = APIRouter()

@router.get("/economia")
async def get_economia(db: Session = Depends(get_db)):
    # CRITICAL: Missing taller_id filter
    movimientos = db.query(MovimientoCaja).all()
    return movimientos
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should detect MovimientoCaja without taller_id filter
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        assert len(critical_violations) >= 1
        assert any("MovimientoCaja" in v.description for v in critical_violations)

    def test_detects_log_notificacion_without_filter(self, auditor, temp_routes_dir):
        """
        Test detection of LogNotificacion queries without taller_id filter.
        
        This specifically tests the whatsapp_ruta.py violations (C-04).
        """
        test_file = temp_routes_dir / "whatsapp_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modelos.log_notificacion import LogNotificacion

router = APIRouter()

@router.get("/logs")
async def get_logs(db: Session = Depends(get_db)):
    # CRITICAL: Missing taller_id filter
    logs = db.query(LogNotificacion).all()
    return logs
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should detect LogNotificacion without taller_id filter
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        assert len(critical_violations) >= 1
        assert any("LogNotificacion" in v.description for v in critical_violations)

    def test_exit_code_with_violations(self, auditor, temp_routes_dir):
        """
        Test that the script would exit with non-zero code when violations are found.
        
        **Validates: Requirement 6.5**
        """
        # Create a test file with violations
        test_file = temp_routes_dir / "test_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modelos.ticket import Ticket

router = APIRouter()

@router.get("/tickets")
async def get_tickets(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).all()
    return tickets
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should have violations
        assert len(violations) > 0
        
        # Check if there are critical or high violations (which should cause non-zero exit)
        critical_or_high = [v for v in violations if v.severity in ("CRITICAL", "HIGH")]
        assert len(critical_or_high) > 0

    def test_performance_requirement(self, auditor):
        """
        Test that the audit script completes in under 10 seconds.
        
        **Validates: Requirement 6.7**
        """
        import time

        routes_dir = "app/rutas"
        
        # Skip if routes directory doesn't exist
        if not os.path.exists(routes_dir):
            pytest.skip(f"Routes directory {routes_dir} not found")

        start_time = time.time()
        violations = auditor.scan_routes(routes_dir)
        elapsed_time = time.time() - start_time

        # Should complete in under 10 seconds
        assert elapsed_time < 10.0, f"Audit took {elapsed_time:.2f}s, expected < 10s"

    def test_detects_vehiculo_without_filter(self, auditor, temp_routes_dir):
        """
        Test detection of Vehiculo queries without taller_id filter.
        """
        test_file = temp_routes_dir / "vehiculo_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modelos.vehiculo import Vehiculo

router = APIRouter()

@router.get("/vehiculos")
async def get_vehiculos(db: Session = Depends(get_db)):
    # CRITICAL: Missing taller_id filter
    vehiculos = db.query(Vehiculo).all()
    return vehiculos
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should detect Vehiculo without taller_id filter
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        assert len(critical_violations) >= 1
        assert any("Vehiculo" in v.description for v in critical_violations)

    def test_detects_cliente_without_filter(self, auditor, temp_routes_dir):
        """
        Test detection of Cliente queries without taller_id filter.
        """
        test_file = temp_routes_dir / "cliente_ruta.py"
        test_file.write_text(
            """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modelos.cliente import Cliente

router = APIRouter()

@router.get("/clientes")
async def get_clientes(db: Session = Depends(get_db)):
    # CRITICAL: Missing taller_id filter
    clientes = db.query(Cliente).all()
    return clientes
"""
        )

        violations = auditor.scan_routes(str(temp_routes_dir))

        # Should detect Cliente without taller_id filter
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        assert len(critical_violations) >= 1
        assert any("Cliente" in v.description for v in critical_violations)


def test_rls_audit_as_pytest():
    """
    Test that the RLS audit can be run as a pytest test.
    
    This test verifies Requirement 6.6: "THE RLS_Audit_Script SHALL be executable
    as a pytest test via `pytest tests/test_rls_audit.py` without additional configuration"
    
    **Validates: Requirement 6.6**
    """
    auditor = RLSAuditor()
    routes_dir = "app/rutas"
    
    # Skip if routes directory doesn't exist
    if not os.path.exists(routes_dir):
        pytest.skip(f"Routes directory {routes_dir} not found")
    
    violations = auditor.scan_routes(routes_dir)
    
    # This test passes if the audit completes successfully
    # The actual violations will be fixed in subsequent tasks
    assert isinstance(violations, list)
    
    # Generate report for visibility
    report = auditor.generate_report(violations)
    print("\n" + report)
