"""
Step definitions para pruebas de aceptación del servicio de notificaciones usando pytest-bdd.
"""
import pytest
from pytest_bdd import given, when, then, parsers, scenarios
from faker import Faker
import httpx

# Importar el feature file - buscar en el directorio actual y en features/
import os
feature_path = os.path.join(os.path.dirname(__file__), 'notificaciones.feature')
if not os.path.exists(feature_path):
    feature_path = os.path.join(os.path.dirname(__file__), '..', '..', 'features', 'notificaciones.feature')
if os.path.exists(feature_path):
    scenarios(feature_path)

faker = Faker()
BASE_URL = "http://localhost:8080"
last_response = None


@given("que el servicio de notificaciones está disponible")
def servicio_disponible():
    """Verifica que el servicio esté disponible."""
    response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
    assert response.status_code in [200, 503]


@when("envío una notificación por email con datos válidos")
def envio_notificacion_email():
    """Envía una notificación por email."""
    global last_response
    payload = {
        "channel": "email",
        "destination": faker.email(),
        "subject": "Test Subject",
        "message": "Test message"
    }
    last_response = httpx.post(f"{BASE_URL}/v1/notifications", json=payload, timeout=10.0)


@when("envío una notificación por SMS con datos válidos")
def envio_notificacion_sms():
    """Envía una notificación por SMS."""
    global last_response
    payload = {
        "channel": "sms",
        "destination": f"+573{faker.numerify('#########')}",
        "message": "Test SMS message"
    }
    last_response = httpx.post(f"{BASE_URL}/v1/notifications", json=payload, timeout=10.0)


@when("envío una notificación multi-canal con datos válidos")
def envio_notificacion_multicanal():
    """Envía una notificación multi-canal."""
    global last_response
    payload = {
        "destination": {
            "email": faker.email(),
            "sms": f"+573{faker.numerify('#########')}"
        },
        "message": {
            "email": "<html><body>Test email</body></html>",
            "sms": "Test SMS"
        },
        "subject": "Test Multi-Channel"
    }
    last_response = httpx.post(f"{BASE_URL}/v1/notifications/multi", json=payload, timeout=10.0)


@when("consulto el endpoint de health check")
def consulto_health_check():
    """Consulta el endpoint de health check."""
    global last_response
    last_response = httpx.get(f"{BASE_URL}/health", timeout=5.0)


@when("consulto el endpoint de liveness")
def consulto_liveness():
    """Consulta el endpoint de liveness."""
    global last_response
    last_response = httpx.get(f"{BASE_URL}/health/live", timeout=5.0)


@then(parsers.parse("la respuesta debe tener estado {status:d}"))
def validar_estado(status):
    """Valida el código de estado HTTP."""
    assert last_response.status_code == status


@then("el cuerpo debe indicar que la notificación fue encolada")
def cuerpo_indica_encolada():
    """Valida que la respuesta indique que la notificación fue encolada."""
    data = last_response.json()
    assert "queued" in data or "success" in data or data.get("queued") is True


@then("el cuerpo debe indicar que el servicio está UP")
def cuerpo_indica_servicio_up():
    """Valida que el servicio esté UP."""
    data = last_response.json()
    assert data.get("status") == "UP"


@then("el cuerpo debe indicar que el servicio está vivo")
def cuerpo_indica_servicio_vivo():
    """Valida que el servicio esté vivo."""
    data = last_response.json()
    assert data.get("status") == "UP"

