import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app


@pytest.fixture
def client():
    """Fixture para crear un cliente de pruebas"""
    return TestClient(app)


@pytest.fixture
def mock_publish():
    """Mock para publish_message"""
    with patch('app.main.publish_message', new_callable=AsyncMock) as mock:
        yield mock


class TestHealthEndpoints:
    """Tests para endpoints de health check"""

    def test_health_endpoint_returns_ok(self, client):
        """Test que /health retorna status OK"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "uptime" in data
        assert "checks" in data

    def test_health_includes_uptime(self, client):
        """Test que /health incluye uptime en segundos"""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data["uptime"], int)
        assert data["uptime"] >= 0

    def test_health_includes_service_name(self, client):
        """Test que /health incluye nombre del servicio"""
        response = client.get("/health")
        data = response.json()
        assert any(check.get("name") == "Application" for check in data.get("checks", []))

    def test_liveness_endpoint_returns_ok(self, client):
        """Test que /health/live retorna status OK"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "checks" in data


class TestNotificationsEndpoint:
    """Tests para el endpoint /v1/notifications"""

    @patch('app.main.publish_message', new_callable=AsyncMock)
    async def test_notify_success(self, mock_publish, client):
        """Test de envío de notificación exitosa"""
        payload = {
            "channel": "email",
            "destination": "test@example.com",
            "message": "Test message"
        }
        
        response = client.post("/v1/notifications", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["queued"] is True

    def test_notify_missing_required_fields(self, client):
        """Test que valida campos requeridos"""
        payload = {
            "channel": "email"
            # Missing destination and message
        }
        
        response = client.post("/v1/notifications", json=payload)
        assert response.status_code == 400

    def test_notify_missing_channel(self, client):
        """Test que valida campo channel"""
        payload = {
            "destination": "test@example.com",
            "message": "Test message"
        }
        
        response = client.post("/v1/notifications", json=payload)
        assert response.status_code == 400
        assert "channel" in response.json()["detail"].lower()

    def test_notify_missing_destination(self, client):
        """Test que valida campo destination"""
        payload = {
            "channel": "email",
            "message": "Test message"
        }
        
        response = client.post("/v1/notifications", json=payload)
        assert response.status_code == 400
        assert "destination" in response.json()["detail"].lower()

    def test_notify_missing_message(self, client):
        """Test que valida campo message"""
        payload = {
            "channel": "email",
            "destination": "test@example.com"
        }
        
        response = client.post("/v1/notifications", json=payload)
        assert response.status_code == 400
        assert "message" in response.json()["detail"].lower()

    def test_notify_handles_special_characters(self, client):
        """Test que maneja caracteres especiales correctamente"""
        payload = {
            "channel": "email",
            "destination": "test@example.com",
            "message": "Test message with special chars: áéíóú ñ"
        }
        
        with patch('app.main.publish_message', new_callable=AsyncMock):
            response = client.post("/v1/notifications", json=payload)
            assert response.status_code == 200

    def test_notify_invalid_json(self, client):
        """Test que maneja JSON inválido"""
        response = client.post(
            "/v1/notifications",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422 or response.status_code == 400

    @patch('app.main.publish_message', new_callable=AsyncMock)
    async def test_notify_with_optional_fields(self, mock_publish, client):
        """Test con campos opcionales"""
        payload = {
            "channel": "email",
            "destination": "test@example.com",
            "message": "Test message",
            "subject": "Test Subject",
            "template": "welcome"
        }
        
        response = client.post("/v1/notifications", json=payload)
        assert response.status_code == 200


class TestMultiNotificationsEndpoint:
    """Tests para el endpoint /v1/notifications/multi"""

    @patch('app.main.publish_message', new_callable=AsyncMock)
    async def test_notify_multi_success(self, mock_publish, client):
        """Test de envío múltiple exitoso"""
        payload = {
            "notifications": [
                {
                    "channel": "email",
                    "destination": "test1@example.com",
                    "message": "Message 1"
                },
                {
                    "channel": "sms",
                    "destination": "+1234567890",
                    "message": "Message 2"
                }
            ]
        }
        
        response = client.post("/v1/notifications/multi", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "queued" in data

    def test_notify_multi_empty_list(self, client):
        """Test con lista vacía de notificaciones"""
        payload = {
            "notifications": []
        }
        
        response = client.post("/v1/notifications/multi", json=payload)
        # Should fail or return specific error
        assert response.status_code >= 400 or response.status_code == 200

    def test_notify_multi_missing_notifications_field(self, client):
        """Test sin campo notifications"""
        payload = {}
        
        response = client.post("/v1/notifications/multi", json=payload)
        assert response.status_code == 400

    @patch('app.main.publish_message', new_callable=AsyncMock)
    async def test_notify_multi_with_different_channels(self, mock_publish, client):
        """Test con diferentes canales"""
        payload = {
            "notifications": [
                {
                    "channel": "email",
                    "destination": "test@example.com",
                    "message": "Email message"
                },
                {
                    "channel": "sms",
                    "destination": "+1234567890",
                    "message": "SMS message"
                },
                {
                    "channel": "whatsapp",
                    "destination": "+1234567890",
                    "message": "WhatsApp message"
                }
            ]
        }
        
        response = client.post("/v1/notifications/multi", json=payload)
        assert response.status_code == 200


class TestContentTypeValidation:
    """Tests para validación de Content-Type"""

    def test_accepts_application_json(self, client):
        """Test que acepta application/json"""
        payload = {
            "channel": "email",
            "destination": "test@example.com",
            "message": "Test"
        }
        
        with patch('app.main.publish_message', new_callable=AsyncMock):
            response = client.post(
                "/v1/notifications",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200

    def test_returns_json_content_type(self, client):
        """Test que retorna JSON"""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


class TestErrorHandling:
    """Tests para manejo de errores"""

    @patch('app.main.publish_message', side_effect=Exception("RabbitMQ connection failed"))
    async def test_handles_rabbitmq_failure(self, mock_publish, client):
        """Test que maneja fallo de RabbitMQ"""
        payload = {
            "channel": "email",
            "destination": "test@example.com",
            "message": "Test"
        }
        
        response = client.post("/v1/notifications", json=payload)
        assert response.status_code == 500

    def test_handles_malformed_request(self, client):
        """Test que maneja request malformada"""
        response = client.post("/v1/notifications", data="not a json")
        assert response.status_code >= 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

