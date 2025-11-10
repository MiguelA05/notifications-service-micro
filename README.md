# Notifications Service Micro

Microservicio desarrollado en Python con FastAPI que actúa como servicio de "Delivery" para el envío de notificaciones a través de múltiples canales (Email, SMS, WhatsApp, Push). Consume mensajes de RabbitMQ y realiza el envío real a los proveedores externos.

## Descripción General

Microservicio de "Delivery" de notificaciones que recibe eventos por RabbitMQ y envía por Email/SMS/WhatsApp/Push. Pensado para convivir con un Orquestador de Notificaciones y con los Microservicios de Dominio. Infraestructura lista para producción mínima: Docker Compose, PostgreSQL, RabbitMQ, autenticación JWT, reintentos y DLQ, y un Scheduler para envíos programados.

## Arquitectura

### Componentes Principales

- **API FastAPI**: Endpoints HTTP para recepción directa de notificaciones
- **Worker**: Consumidor de RabbitMQ que procesa colas de notificaciones
- **Scheduler**: Programador de tareas para envíos programados
- **Channels**: Implementaciones de canales de envío (Strategy Pattern)
- **Database**: Persistencia de configuraciones y métricas
- **Messaging**: Gestión de conexión y publicación en RabbitMQ

### Tecnologías

- FastAPI
- SQLAlchemy (ORM)
- PostgreSQL
- aio-pika (Cliente asíncrono para RabbitMQ)
- APScheduler
- Jinja2 (Motor de plantillas)
- Pydantic (Validación de datos)
- Passlib (Hash de contraseñas)
- python-jose (Manejo de tokens JWT)

## Endpoints de la API

### Health Checks

#### Health Endpoint

- **Endpoint**: `GET /health`
- **Descripción**: Verifica el estado de salud del servicio
- **Autenticación**: No requerida

#### Liveness Endpoint

- **Endpoint**: `GET /health/live`
- **Descripción**: Verifica si el servicio está vivo
- **Autenticación**: No requerida

### Notificaciones

#### Envío Simple de Notificación

- **Endpoint**: `POST /v1/notifications`
- **Descripción**: Envía una notificación a un canal específico
- **Autenticación**: No requerida

**Request Body**:
```json
{
  "channel": "email",
  "destination": "user@example.com",
  "message": "Mensaje de prueba",
  "subject": "Asunto del mensaje"
}
```

#### Envío Multi-Canal

- **Endpoint**: `POST /v1/notifications/multi`
- **Descripción**: Envía notificaciones a múltiples canales simultáneamente
- **Autenticación**: No requerida

**Request Body**:
```json
{
  "destination": {
    "email": "user@example.com",
    "sms": "+573001234567",
    "whatsapp": "+573001234567"
  },
  "message": {
    "email": "<html><body><h1>Mensaje HTML</h1></body></html>",
    "sms": "Mensaje de texto para SMS",
    "whatsapp": "Mensaje de texto para WhatsApp"
  },
  "subject": "Asunto del mensaje",
  "metadata": {
    "tenantId": "acme",
    "template": "welcome"
  }
}
```

#### Envío Multi-Canal con Autenticación

- **Endpoint**: `POST /v1/notifications/multi/auth`
- **Descripción**: Igual que multi pero requiere autenticación JWT
- **Autenticación**: Requerida (JWT Bearer Token)

### Autenticación

#### Login

- **Endpoint**: `POST /login`
- **Descripción**: Autentica un usuario y genera token JWT
- **Autenticación**: No requerida

#### Registro

- **Endpoint**: `POST /register`
- **Descripción**: Registra un nuevo usuario (solo para pruebas)
- **Autenticación**: No requerida

## Canales de Notificación

El sistema soporta los siguientes canales:

- **Email**: Envío vía SMTP con soporte HTML
- **SMS**: Envío vía Twilio
- **WhatsApp**: Envío vía Twilio WhatsApp API
- **Push**: Envío vía Firebase Cloud Messaging (FCM)

## Configuración

### Variables de Entorno

```env
# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_VHOST=foro
RABBITMQ_USERNAME=orchestrator_user
RABBITMQ_PASSWORD=orch_pass
AMQP_EXCHANGE=orquestador.events
AMQP_EXCHANGE_TYPE=topic
AMQP_QUEUE=notifications.queue
AMQP_ROUTING_KEY=notifications.created
AMQP_DLX_NAME=dlx
AMQP_DLX_TYPE=topic
MESSAGING_DECLARE_INFRA=false
WORKER_DECLARE_INFRA=false

# Base de Datos
DB_URL=postgresql+psycopg2://notifications:notifications@postgres:5432/notifications

# JWT
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Notifications Service

# Twilio (SMS/WhatsApp)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_NUMBER=+1234567890
TWILIO_WHATSAPP_FROM=whatsapp:+1234567890
WHATSAPP_WEBHOOK_URL=https://your-domain.com/webhook/whatsapp

# Firebase (Push)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_KEY={"type":"service_account",...}
WEB_VAPID_PUBLIC_KEY=your-public-key
WEB_VAPID_PRIVATE_KEY=your-private-key

# Worker
WORKER_MAX_RETRIES=3
WORKER_RETRY_DELAY_1=5
WORKER_RETRY_DELAY_2=30
WORKER_RETRY_DELAY_3=120
DEFAULT_CHANNEL=email
```

## Uso

### Quickstart

1. Configurar archivo `.env` con las variables necesarias
2. Levantar stack con Docker Compose:
```bash
docker compose build --no-cache
docker compose up -d
```

3. Verificar estado:
```bash
curl http://localhost:8080/health
docker ps
```

### Envío Simple

```bash
curl -X POST "http://localhost:8080/v1/notifications" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "sms",
    "destination": "+573225035863",
    "message": "Hola!"
  }'
```

### Envío Multi-Canal

```bash
curl -X POST "http://localhost:8080/v1/notifications/multi" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": {
      "email": "juan@example.com",
      "sms": "+573225035863"
    },
    "message": {
      "email": "<html><body><b>Hola</b></body></html>",
      "sms": "Hola por SMS"
    },
    "subject": "Prueba multi"
  }'
```

## Estructura del Proyecto

```
notifications-service-micro/
├── app/
│   ├── main.py
│   ├── messaging.py
│   ├── worker.py
│   ├── scheduler.py
│   ├── channels/
│   │   ├── base.py
│   │   ├── email.py
│   │   ├── sms.py
│   │   ├── whatsapp.py
│   │   ├── push.py
│   │   └── factory.py
│   ├── db.py
│   ├── models.py
│   └── auth.py
├── tests/
│   └── test_main_api.py
├── docs/
│   └── IMPLEMENTATION.md
├── Dockerfile
├── requirements.txt
├── pytest.ini
└── README.md
```

## Integración con RabbitMQ

### Topología

- **Exchange**: `orquestador.events` (tipo topic, durable)
- **Cola Principal**: `notifications.queue` (durable, x-dead-letter-exchange=dlx)
- **Exchange DLX**: `dlx` (tipo topic) → Cola DLQ: `notifications.queue.dlq`
- **Binding**: `orquestador.events` → `notifications.queue` con routing key `notifications.*`

### Formato de Mensajes

#### Formato Simple

```json
{
  "channel": "email",
  "destination": "user@example.com",
  "message": "Contenido del mensaje",
  "subject": "Asunto"
}
```

#### Formato Multi-Canal

```json
{
  "destination": {
    "email": "user@example.com",
    "sms": "+573001234567"
  },
  "message": {
    "email": "<html>...</html>",
    "sms": "Texto plano"
  },
  "subject": "Asunto",
  "metadata": {
    "tenantId": "acme",
    "template": "welcome"
  }
}
```

## Testing

El proyecto incluye una suite completa de tests:

- **Unit Tests**: Pruebas de canales y lógica de negocio
- **Integration Tests**: Pruebas de endpoints con TestClient (30+ tests)
- **Mocking**: Uso de mocks para proveedores externos

Ejecutar tests:
```bash
pytest
```

## Despliegue

### Docker Compose

Configurado en `docker-compose.unified.yml`:
- **API**: Puerto 8080
- **Worker**: Proceso separado
- **Scheduler**: Proceso separado
- Dependencias: PostgreSQL, RabbitMQ

### Logs

```bash
# API
docker logs notifications-service-micro --since=1m

# Worker
docker logs notifications-worker --since=1m

# Scheduler
docker logs notifications-scheduler --since=1m
```

## Flujos de Procesamiento

### Flujo de Envío Directo (API)

1. Cliente envía `POST /v1/notifications` con datos de notificación
2. API recibe la solicitud y valida datos con Pydantic
3. Publica mensaje en RabbitMQ
4. Worker consume mensaje y procesa envío
5. Retorna respuesta HTTP 200 con confirmación

### Flujo de Consumo de Worker

1. Worker consume mensaje de `notifications.queue`
2. Deserializa payload JSON
3. Identifica canal usando Factory
4. Crea instancia de canal apropiado
5. Ejecuta `channel.send()` con datos del mensaje
6. Si éxito, confirma mensaje (ACK)
7. Si fallo, reencola en cola de reintento
8. Si agota reintentos, envía a DLQ

### Flujo de Reintentos

1. Worker detecta fallo en envío
2. Incrementa contador de reintentos
3. Publica mensaje en cola de reintento con TTL:
   - Retry 1: 5 segundos
   - Retry 2: 30 segundos
   - Retry 3: 120 segundos
4. Mensaje expira y vuelve a cola principal
5. Worker reintenta envío
6. Si agota 3 reintentos, envía a DLQ

## Consideraciones de Seguridad

1. **Autenticación JWT**: Validación de tokens en endpoints protegidos
2. **Validación de entrada**: Validación exhaustiva con Pydantic
3. **Credenciales**: Almacenadas en variables de entorno
4. **HTTPS**: Usar en producción para proteger datos en tránsito
5. **Rate Limiting**: Considerar implementar límites de solicitudes

## Notas

- Para documentación detallada, consultar `docs/IMPLEMENTATION.md`
- Gmail SMTP: usar App Password (16 caracteres) con 2FA
- Twilio SMS: habilitar Geo Permissions para el país destino
- No publicar el JSON de la service account de Firebase

## Extensibilidad

Para añadir un canal nuevo:

1. Crear `app/channels/<nuevo>.py` implementando Channel
2. Registrar en `app/channels/factory.py`
3. Añadir config por defecto en `db.init_default_channels` si aplica
4. Documentar nuevas variables en este README
