"""
Configuración global de pytest para mocks de dependencias externas
"""
import pytest
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock de aio_pika antes de importar cualquier módulo
mock_aio_pika = MagicMock()
mock_aio_pika.Message = MagicMock()
mock_aio_pika.DeliveryMode = MagicMock()
mock_aio_pika.DeliveryMode.PERSISTENT = 2

sys.modules['aio_pika'] = mock_aio_pika

# Mock de publish_message y setup_infrastructure
@pytest.fixture(autouse=True)
def mock_messaging():
    """Mock automático de messaging para todas las pruebas"""
    with patch('app.messaging.publish_message', new_callable=AsyncMock) as mock_pub, \
         patch('app.messaging.setup_infrastructure', new_callable=AsyncMock) as mock_setup:
        mock_pub.return_value = None
        mock_setup.return_value = None
        yield {
            'publish': mock_pub,
            'setup': mock_setup
        }

