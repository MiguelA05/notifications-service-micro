"""
Pruebas automatizadas para el camino feliz de todas las operaciones del microservicio de notificaciones.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Agregar el directorio raíz al path para importar app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock de aio_pika y messaging ANTES de importar app
mock_publish = AsyncMock(return_value=None)
mock_setup = AsyncMock(return_value=None)

# Crear mock del módulo messaging
mock_messaging_module = MagicMock()
mock_messaging_module.publish_message = mock_publish
mock_messaging_module.setup_infrastructure = mock_setup

# Reemplazar el módulo antes de importar
sys.modules['app.messaging'] = mock_messaging_module

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestNotificationsHappyPath:
    """Tests del camino feliz para todas las operaciones"""

    def test_health_check(self):
        """Test: GET /health - Verificar salud del servicio"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "checks" in data

    def test_health_readiness(self):
        """Test: GET /health/ready - Verificar readiness"""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "checks" in data

    def test_health_liveness(self):
        """Test: GET /health/live - Verificar liveness"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"

    def test_notify_email_success(self):
        """Test: POST /v1/notifications - Enviar notificación email exitosamente"""
        payload = {
            "channel": "email",
            "destination": "test@example.com",
            "subject": "Test Subject",
            "message": "Test message"
        }
        
        response = client.post("/v1/notifications", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "queued" in data or "success" in data

    def test_notify_sms_success(self):
        """Test: POST /v1/notifications - Enviar notificación SMS exitosamente"""
        payload = {
            "channel": "sms",
            "destination": "+573001234567",
            "message": "Test SMS message"
        }
        
        response = client.post("/v1/notifications", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "queued" in data or "success" in data

    def test_notify_multi_channel_success(self):
        """Test: POST /v1/notifications/multi - Enviar notificación multi-canal exitosamente"""
        payload = {
            "destination": {
                "email": "test@example.com",
                "sms": "+573001234567"
            },
            "message": {
                "email": "<html>Email content</html>",
                "sms": "SMS content"
            },
            "subject": "Multi-channel test"
        }
        
        response = client.post("/v1/notifications/multi", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "queued" in data or "success" in data

    @patch('app.main.get_user_by_username')
    @patch('app.main.verify_password')
    @patch('app.main.create_access_token')
    def test_login_success(self, mock_token, mock_verify, mock_get_user):
        """Test: POST /login - Login exitoso"""
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.hashed_password = "hashed_pass"
        mock_get_user.return_value = mock_user
        mock_verify.return_value = True
        mock_token.return_value = "test_token"
        
        # OAuth2PasswordRequestForm requiere form-data
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        response = client.post("/login", data=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @patch('app.main.get_user_by_username')
    @patch('app.main.get_user_by_email')
    @patch('app.main.create_user')
    def test_register_success(self, mock_create, mock_get_email, mock_get_user):
        """Test: POST /register - Registro exitoso"""
        mock_get_user.return_value = None
        mock_get_email.return_value = None
        mock_user = MagicMock()
        mock_user.id = 1
        mock_create.return_value = mock_user
        
        payload = {
            "username": "newuser",
            "password": "newpass123",
            "email": "newuser@example.com"
        }
        
        response = client.post("/register", params=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "message" in data or "user_id" in data
