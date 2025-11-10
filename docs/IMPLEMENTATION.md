# Notifications Service Micro - Documentación de Implementación

## Descripción General

El microservicio de Notificaciones es una aplicación desarrollada en Python con FastAPI que actúa como servicio de "Delivery" para el envío de notificaciones a través de múltiples canales (Email, SMS, WhatsApp, Push). Consume mensajes de RabbitMQ y realiza el envío real a los proveedores externos.

## Arquitectura

### Componentes Principales

El microservicio está estructurado en los siguientes componentes:

1. **API FastAPI**: Endpoints HTTP para recepción directa de notificaciones
2. **Worker**: Consumidor de RabbitMQ que procesa colas de notificaciones
3. **Scheduler**: Programador de tareas para envíos programados
4. **Channels**: Implementaciones de canales de envío (Strategy Pattern)
5. **Database**: Persistencia de configuraciones y métricas
6. **Messaging**: Gestión de conexión y publicación en RabbitMQ

### Tecnologías Utilizadas

- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM para acceso a base de datos
- **PostgreSQL**: Base de datos relacional
- **aio-pika**: Cliente asíncrono para RabbitMQ
- **APScheduler**: Programador de tareas asíncronas
- **Jinja2**: Motor de plantillas para emails
- **Pydantic**: Validación de datos y modelos
- **Passlib**: Hash de contraseñas
- **python-jose**: Manejo de tokens JWT

## Modelo de Datos

### NotificationChannelConfig

Configuración de canales de notificación almacenada en base de datos.

- **id** (Integer, PK): Identificador único
- **channel** (String): Nombre del canal (email, sms, whatsapp, push)
- **config** (JSON): Configuración específica del canal
- **enabled** (Boolean): Indica si el canal está habilitado
- **created_at** (DateTime): Fecha de creación
- **updated_at** (DateTime): Fecha de actualización

### Notification

Registro de notificaciones enviadas (opcional, para auditoría).

- **id** (Integer, PK): Identificador único
- **channel** (String): Canal utilizado
- **destination** (String): Destino de la notificación
- **status** (String): Estado (pending, sent, failed)
- **message** (Text): Contenido del mensaje
- **created_at** (DateTime): Fecha de creación
- **sent_at** (DateTime): Fecha de envío

### User

Usuarios para autenticación JWT (solo para pruebas).

- **id** (Integer, PK): Identificador único
- **username** (String, Unique): Nombre de usuario
- **email** (String, Unique): Correo electrónico
- **hashed_password** (String): Contraseña hasheada
- **created_at** (DateTime): Fecha de creación

## Endpoints de la API

### Health Checks

#### Health Endpoint

- **Endpoint**: `GET /health`
- **Descripción**: Verifica el estado de salud del servicio
- **Autenticación**: No requerida
- **Response**:
```json
{
  "status": "UP",
  "version": "1.0.0",
  "uptime": 3600,
  "checks": [
    {
      "name": "Application",
      "status": "UP",
      "data": {
        "from": "2024-01-01T00:00:00",
        "status": "RUNNING"
      }
    }
  ]
}
```

#### Liveness Endpoint

- **Endpoint**: `GET /health/live`
- **Descripción**: Verifica si el servicio está vivo
- **Autenticación**: No requerida

### Notificaciones

#### Envío Simple de Notificación

- **Endpoint**: `POST /v1/notifications`
- **Descripción**: Envía una notificación a un canal específico
- **Autenticación**: No requerida
- **Request Body**:
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
- **Request Body**:
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
- **Request Body** (form-urlencoded):
```
username=admin&password=admin_pass
```

#### Registro

- **Endpoint**: `POST /register`
- **Descripción**: Registra un nuevo usuario (solo para pruebas)
- **Autenticación**: No requerida

### Webhooks

#### Webhook de WhatsApp

- **Endpoint**: `POST /webhook/whatsapp`
- **Descripción**: Recibe webhooks de Twilio para WhatsApp
- **Autenticación**: No requerida (validación por firma de Twilio)

## Componentes de Implementación

### API (main.py)

Aplicación FastAPI principal que expone los endpoints HTTP.

**Funcionalidades**:
- Endpoints de health checks
- Endpoints de notificaciones
- Endpoints de autenticación
- Middleware de CORS
- Manejo de errores global

### Worker (worker.py)

Consumidor asíncrono de RabbitMQ que procesa colas de notificaciones.

**Funcionalidades**:
- Consume mensajes de `notifications.queue`
- Identifica canal y crea instancia correspondiente (Factory Pattern)
- Ejecuta envío usando el canal apropiado
- Gestiona reintentos con backoff exponencial
- Envía mensajes fallidos a DLQ después de agotar reintentos

**Flujo de procesamiento**:
1. Consume mensaje de la cola
2. Deserializa payload JSON
3. Identifica canal (email, sms, whatsapp, push)
4. Crea instancia de canal usando Factory
5. Ejecuta envío
6. Si falla, reencola en cola de reintento
7. Si agota reintentos, envía a DLQ

### Scheduler (scheduler.py)

Programador de tareas asíncronas para envíos programados.

**Funcionalidades**:
- Programa tareas para fecha futura
- Publica mensajes en RabbitMQ cuando llega la hora
- Gestiona múltiples schedules simultáneos
- Cancela schedules pendientes

### Channels (Strategy Pattern)

Implementaciones de canales de envío siguiendo el patrón Strategy.

#### Base Channel (base.py)

Interfaz abstracta que define el contrato para todos los canales.

**Métodos**:
- `send()`: Método abstracto para envío (debe ser implementado)

#### Email Channel (email.py)

Implementación para envío de emails vía SMTP.

**Configuración**:
- SMTP_HOST: Servidor SMTP
- SMTP_PORT: Puerto SMTP
- SMTP_USER: Usuario SMTP
- SMTP_PASSWORD: Contraseña SMTP
- FROM_EMAIL: Email remitente
- FROM_NAME: Nombre remitente

**Funcionalidades**:
- Envío de emails HTML
- Soporte para plantillas Jinja2
- Manejo de errores de SMTP

#### SMS Channel (sms.py)

Implementación para envío de SMS vía Twilio.

**Configuración**:
- TWILIO_ACCOUNT_SID: SID de cuenta Twilio
- TWILIO_AUTH_TOKEN: Token de autenticación Twilio
- TWILIO_FROM_NUMBER: Número remitente

**Funcionalidades**:
- Envío de SMS a números E.164
- Manejo de errores de Twilio
- Validación de formato de números

#### WhatsApp Channel (whatsapp.py)

Implementación para envío de mensajes WhatsApp vía Twilio.

**Configuración**:
- TWILIO_ACCOUNT_SID: SID de cuenta Twilio
- TWILIO_AUTH_TOKEN: Token de autenticación Twilio
- TWILIO_WHATSAPP_FROM: Número WhatsApp remitente
- WHATSAPP_WEBHOOK_URL: URL para recibir webhooks

**Funcionalidades**:
- Envío de mensajes WhatsApp
- Recepción de webhooks de estado
- Manejo de errores de Twilio

#### Push Channel (push.py)

Implementación para envío de notificaciones push vía Firebase Cloud Messaging.

**Configuración**:
- FIREBASE_PROJECT_ID: ID del proyecto Firebase
- FIREBASE_SERVICE_ACCOUNT_KEY: JSON de service account
- WEB_VAPID_PUBLIC_KEY: Clave pública VAPID
- WEB_VAPID_PRIVATE_KEY: Clave privada VAPID

**Funcionalidades**:
- Envío de notificaciones push a dispositivos
- Soporte para Android e iOS
- Manejo de tokens inválidos

#### Channel Factory (factory.py)

Factory que crea instancias de canales según el tipo.

**Métodos**:
- `create_channel(channel_type)`: Crea instancia del canal apropiado

### Messaging (messaging.py)

Gestión de conexión y publicación en RabbitMQ.

**Funcionalidades**:
- Conexión asíncrona a RabbitMQ
- Publicación de mensajes en exchanges
- Configuración de exchanges y colas
- Manejo de reconexión automática

### Database (db.py, models.py)

Gestión de base de datos con SQLAlchemy.

**Funcionalidades**:
- Configuración de sesión de base de datos
- Modelos ORM para tablas
- Migraciones de esquema
- Inicialización de datos por defecto

### Authentication (auth.py)

Utilidades de autenticación JWT.

**Funcionalidades**:
- Generación de tokens JWT
- Validación de tokens
- Hash de contraseñas con Passlib
- Verificación de credenciales

## Flujos de Procesamiento

### Flujo de Envío Directo (API)

1. Cliente envía `POST /v1/notifications` con datos de notificación
2. `main.py` recibe la solicitud y valida datos con Pydantic
3. `publish_message()` publica mensaje en RabbitMQ
4. Worker consume mensaje y procesa envío
5. Retorna respuesta HTTP 200 con confirmación

### Flujo de Envío Multi-Canal

1. Cliente envía `POST /v1/notifications/multi` con múltiples destinos
2. `main.py` recibe solicitud y valida estructura
3. Para cada canal en `destination`, publica mensaje separado en RabbitMQ
4. Workers procesan mensajes en paralelo
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

### Flujo de Envío Programado

1. Cliente envía `POST /notifications/schedule` con fecha futura
2. Scheduler programa tarea para fecha especificada
3. Cuando llega la hora, Scheduler publica mensaje en RabbitMQ
4. Worker procesa mensaje como flujo normal

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

## Integración con RabbitMQ

### Topología

- **Exchange**: `orquestador.events` (tipo topic, durable)
- **Cola Principal**: `notifications.queue` (durable, x-dead-letter-exchange=dlx)
- **Exchange DLX**: `dlx` (tipo topic) → Cola DLQ: `notifications.queue.dlq`
- **Binding**: `orquestador.events` → `notifications.queue` con routing key `notifications.*`
- **Retries**: Colas de reintento con TTL (opcional, gestionado por worker)

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

### Estructura de Tests

- **Unit Tests**: Pruebas de canales y lógica de negocio
- **Integration Tests**: Pruebas de endpoints con TestClient
- **Mocking**: Uso de mocks para proveedores externos

### Cobertura de Tests

El proyecto incluye tests para:
- Endpoints de API (30+ tests)
- Canales de envío
- Worker y procesamiento de mensajes
- Autenticación JWT

## Despliegue

### Docker

El microservicio incluye un `Dockerfile` para contenedorización.

### Docker Compose

Configurado en `docker-compose.unified.yml`:
- **API**: Puerto 8080
- **Worker**: Proceso separado
- **Scheduler**: Proceso separado
- Dependencias: PostgreSQL, RabbitMQ

## Monitoreo y Logging

### Health Checks

- **Health Endpoint**: `/health` - Estado general del servicio
- **Liveness Endpoint**: `/health/live` - Verificación de vida

### Logging

- **Structured Logging**: Logs en formato JSON
- **Niveles**: INFO, WARN, ERROR
- **Contexto**: Incluye información de request, usuario, etc.

## Consideraciones de Seguridad

1. **Autenticación JWT**: Validación de tokens en endpoints protegidos
2. **Validación de entrada**: Validación exhaustiva con Pydantic
3. **Credenciales**: Almacenadas en variables de entorno
4. **HTTPS**: Usar en producción para proteger datos en tránsito
5. **Rate Limiting**: Considerar implementar límites de solicitudes

## Mejoras Futuras

1. **Métricas**: Integración con Prometheus/Grafana
2. **Trazabilidad**: Distributed tracing con OpenTelemetry
3. **Rate Limiting**: Límites de envío por usuario/canal
4. **Plantillas**: Sistema de plantillas más robusto
5. **Analytics**: Dashboard de métricas de envío
6. **Webhooks**: Más endpoints de webhook para otros proveedores

