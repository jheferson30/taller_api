"""
Tests unitarios para AuditService.

Valida que el servicio de auditoría registre correctamente
todos los eventos con la información completa requerida.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from app.servicios.audit_service import AuditService
from app.repositorios.audit_log_repository import AuditLogRepository


@pytest.fixture
def mock_audit_repo():
    """Crea un mock del repositorio de auditoría."""
    return Mock(spec=AuditLogRepository)


@pytest.fixture
def audit_service(mock_audit_repo):
    """Crea una instancia del servicio de auditoría con repositorio mock."""
    return AuditService(audit_repo=mock_audit_repo)


class TestAuditService:
    """Tests para el servicio de auditoría."""
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_with_all_fields(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento con todos los campos requeridos."""
        # Arrange
        user_id = 1
        action = "LOGIN"
        resource_type = "user"
        resource_id = 1
        ip_address = "192.168.1.100"
        user_agent = "Mozilla/5.0"
        details = {"browser": "Chrome", "os": "Windows"}
        
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        # Assert
        mock_audit_log_class.assert_called_once_with(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        mock_audit_repo.create.assert_called_once_with(mock_audit_log_instance)
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_login(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento LOGIN correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="LOGIN",
            resource_type="user",
            resource_id=1,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "LOGIN"
        mock_audit_repo.create.assert_called_once_with(mock_audit_log_instance)
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_logout(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento LOGOUT correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="LOGOUT",
            resource_type="user",
            resource_id=1,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "LOGOUT"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_login_failed(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento LOGIN_FAILED correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=None,  # Usuario anónimo en login fallido
            action="LOGIN_FAILED",
            resource_type="user",
            resource_id=None,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"username": "testuser"}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "LOGIN_FAILED"
        assert mock_audit_log_class.call_args[1]['user_id'] is None
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_user_create(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento USER_CREATE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="USER_CREATE",
            resource_type="user",
            resource_id=2,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"created_username": "newuser"}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "USER_CREATE"
        assert mock_audit_log_class.call_args[1]['resource_id'] == 2
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_user_update(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento USER_UPDATE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="USER_UPDATE",
            resource_type="user",
            resource_id=2,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"updated_fields": ["email"]}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "USER_UPDATE"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_user_deactivate(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento USER_DEACTIVATE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="USER_DEACTIVATE",
            resource_type="user",
            resource_id=2,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "USER_DEACTIVATE"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_role_change(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento ROLE_CHANGE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="ROLE_CHANGE",
            resource_type="user",
            resource_id=2,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"old_roles": ["MECANICO"], "new_roles": ["ADMIN"]}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "ROLE_CHANGE"
        assert "old_roles" in mock_audit_log_class.call_args[1]['details']
        assert "new_roles" in mock_audit_log_class.call_args[1]['details']
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_password_change(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento PASSWORD_CHANGE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="PASSWORD_CHANGE",
            resource_type="user",
            resource_id=1,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "PASSWORD_CHANGE"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_password_reset(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento PASSWORD_RESET correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="PASSWORD_RESET",
            resource_type="user",
            resource_id=1,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"reset_token_used": True}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "PASSWORD_RESET"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_ticket_create(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento TICKET_CREATE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="TICKET_CREATE",
            resource_type="ticket",
            resource_id=100,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"ticket_number": "T-2026-001"}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "TICKET_CREATE"
        assert mock_audit_log_class.call_args[1]['resource_type'] == "ticket"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_ticket_update(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento TICKET_UPDATE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="TICKET_UPDATE",
            resource_type="ticket",
            resource_id=100,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"updated_fields": ["estado", "total_servicio"]}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "TICKET_UPDATE"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_ticket_finalize(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento TICKET_FINALIZE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="TICKET_FINALIZE",
            resource_type="ticket",
            resource_id=100,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"saldo_pendiente": 0}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "TICKET_FINALIZE"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_config_change(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event registra evento CONFIG_CHANGE correctamente."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="CONFIG_CHANGE",
            resource_type="config",
            resource_id=1,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"config_key": "rate_limit", "old_value": 100, "new_value": 200}
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['action'] == "CONFIG_CHANGE"
        assert mock_audit_log_class.call_args[1]['resource_type'] == "config"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_without_details(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event funciona sin campo details opcional."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="LOGIN",
            resource_type="user",
            resource_id=1,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['details'] is None
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_anonymous_user(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event permite user_id None para eventos anónimos."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=None,
            action="LOGIN_FAILED",
            resource_type="user",
            resource_id=None,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['user_id'] is None
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_ipv6_address(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event soporta direcciones IPv6."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="LOGIN",
            resource_type="user",
            resource_id=1,
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            user_agent="Mozilla/5.0"
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['ip_address'] == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        mock_audit_repo.create.assert_called_once()
    
    @patch('app.servicios.audit_service.AuditLog')
    def test_log_event_complex_details(self, mock_audit_log_class, audit_service, mock_audit_repo):
        """Test que log_event soporta detalles complejos en formato JSON."""
        # Arrange
        mock_audit_log_instance = Mock()
        mock_audit_log_class.return_value = mock_audit_log_instance
        
        complex_details = {
            "changes": [
                {"field": "email", "old": "old@example.com", "new": "new@example.com"},
                {"field": "roles", "old": ["USER"], "new": ["USER", "ADMIN"]}
            ],
            "metadata": {
                "browser": "Chrome",
                "version": "120.0",
                "platform": "Windows"
            }
        }
        
        # Act
        audit_service.log_event(
            user_id=1,
            action="USER_UPDATE",
            resource_type="user",
            resource_id=2,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details=complex_details
        )
        
        # Assert
        assert mock_audit_log_class.call_args[1]['details'] == complex_details
        assert "changes" in mock_audit_log_class.call_args[1]['details']
        assert "metadata" in mock_audit_log_class.call_args[1]['details']
        mock_audit_repo.create.assert_called_once()
