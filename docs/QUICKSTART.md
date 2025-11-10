# Guía de Inicio Rápido - Notifications Service Micro

Esta guía te permitirá poner en marcha el microservicio de notificaciones en tu entorno local y ejecutar pruebas básicas.

## Requisitos Previos

- Python 3.11 o superior
- pip y virtualenv
- PostgreSQL 12 o superior
- RabbitMQ 3.8 o superior
- Docker y Docker Compose (recomendado)

## Instalación Rápida

### 1. Clonar y Configurar Entorno Virtual

```bash
cd notifications-service-micro
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_VHOST=foro
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest
AMQP_EXCHANGE=orquestador.events
AMQP_EXCHANGE_TYPE=topic
AMQP_QUEUE=notifications.queue
AMQP_ROUTING_KEY=notifications.created

# Base de Datos
DB_URL=postgresql+psycopg2://notifications:notifications@localhost:5432/notifications

# JWT (opcional)
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email SMTP (opcional, para pruebas)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Notifications Service
```

### 3. Configurar Base de Datos

#### Opción A: PostgreSQL Local

```sql
CREATE DATABASE notifications;
CREATE USER notifications WITH PASSWORD 'notifications';
GRANT ALL PRIVILEGES ON DATABASE notifications TO notifications;
```

#### Opción B: PostgreSQL con Docker

```bash
docker run -d --name postgres-notifications \
  -e POSTGRES_DB=notifications \
  -e POSTGRES_USER=notifications \
  -e POSTGRES_PASSWORD=notifications \
  -p 5432:5432 \
  postgres:15
```

### 4. Inicializar Base de Datos

```bash
python -c "from app.db import init_db; init_db()"
```

### 5. Ejecutar API Localmente

```bash
uvicorn app.main:app --reload --port 8080
```

### 6. Ejecutar Worker (en otra terminal)

```bash
source venv/bin/activate
python -m app.worker
```

## Verificación Inicial

### Health Check

```bash
curl http://localhost:8080/health
```

Respuesta esperada:
```json
{
  "status": "UP",
  "version": "1.0.0",
  "uptime": 123,
  "checks": [...]
}
```

### Liveness Check

```bash
curl http://localhost:8080/health/live
```

## Pruebas Básicas

### 1. Envío Simple de Notificación (Email)

```bash
curl -X POST http://localhost:8080/v1/notifications \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "email",
    "destination": "test@example.com",
    "subject": "Prueba",
    "message": "Este es un mensaje de prueba"
  }'
```

Respuesta esperada: HTTP 200 con `{"queued": true}`

### 2. Envío Multi-Canal

```bash
curl -X POST http://localhost:8080/v1/notifications/multi \
  -H "Content-Type: application/json" \
  -d '{
    "destination": {
      "email": "test@example.com",
      "sms": "+573001234567"
    },
    "message": {
      "email": "<html><body><h1>Prueba</h1></body></html>",
      "sms": "Mensaje de prueba SMS"
    },
    "subject": "Prueba Multi-Canal"
  }'
```

### 3. Autenticación (Login)

```bash
curl -X POST http://localhost:8080/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin_pass"
```

Guardar el token:
```bash
TOKEN=$(curl -s -X POST http://localhost:8080/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin_pass" | jq -r '.access_token')
```

### 4. Envío con Autenticación

```bash
curl -X POST http://localhost:8080/v1/notifications/multi/auth \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": {
      "email": "test@example.com"
    },
    "message": {
      "email": "<html><body>Mensaje autenticado</body></html>"
    },
    "subject": "Prueba Autenticada"
  }'
```

## Verificar Worker

### Ver Logs del Worker

El worker debe mostrar mensajes como:
```
Consuming messages from notifications.queue...
Processing message: {...}
```

### Verificar Mensajes en RabbitMQ

Acceder a RabbitMQ Management UI:
```bash
# Si está corriendo en Docker
open http://localhost:15672
# Usuario: guest, Contraseña: guest
```

Navegar a la cola `notifications.queue` para ver mensajes pendientes.

## Ejecutar Tests

### Tests Unitarios

```bash
pytest tests/ -v
```

### Tests con Cobertura

```bash
pytest tests/ --cov=app --cov-report=html
```

Ver reporte en: `htmlcov/index.html`

### Tests Específicos

```bash
pytest tests/test_main_api.py::TestHealthEndpoints -v
```

## Verificar Base de Datos

### Conectar a PostgreSQL

```bash
psql -h localhost -U notifications -d notifications
```

### Verificar Tablas

```sql
\dt
SELECT * FROM notification_channel_config;
```

## Troubleshooting

### Error: ModuleNotFoundError

Asegurarse de que el entorno virtual esté activado y las dependencias instaladas:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Error: Connection refused a PostgreSQL

Verificar que PostgreSQL esté corriendo:
```bash
psql -h localhost -U postgres -c "SELECT version();"
```

### Error: Connection refused a RabbitMQ

Verificar que RabbitMQ esté corriendo:
```bash
curl http://localhost:15672
```

O iniciar con Docker:
```bash
docker run -d --name rabbitmq \
  -p 5672:5672 -p 15672:15672 \
  rabbitmq:3-management
```

### Error: Worker no procesa mensajes

Verificar que:
1. El worker esté corriendo
2. La cola `notifications.queue` exista en RabbitMQ
3. Los mensajes estén llegando a la cola
4. Revisar logs del worker para errores

### Error: SMTP no funciona

Para pruebas locales, puedes desactivar el envío real de emails y solo verificar que los mensajes se publiquen en RabbitMQ. El worker procesará los mensajes pero fallará silenciosamente si SMTP no está configurado.

## Próximos Pasos

- Revisar `docs/IMPLEMENTATION.md` para detalles de arquitectura
- Configurar proveedores externos (Twilio, Firebase) para SMS/Push
- Configurar Scheduler para envíos programados
- Explorar endpoints con herramientas como Postman o httpie

