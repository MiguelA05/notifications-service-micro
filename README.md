## Notifications Service Micro (Python/FastAPI)

### Descripción general
- Microservicio de “Delivery” de notificaciones. Recibe eventos por RabbitMQ y envía por Email/SMS/WhatsApp/Push.
- Pensado para convivir con un Orquestador de Notificaciones (otro servicio) y con los Microservicios de Dominio (usuarios, ventas, etc.).
- Infraestructura lista para producción mínima: Docker Compose, PostgreSQL, RabbitMQ, autenticación JWT, reintentos y DLQ, y un Scheduler para envíos programados.

---

## Arquitectura y relación con otros servicios
- Servicios de Dominio: publican eventos al Orquestador.
- Orchestrator (servicio aparte): aplica reglas, elige canal y publica al exchange de notificaciones en RabbitMQ.
- Este proyecto (Delivery): consume la cola de notificaciones y realiza el envío real a los proveedores.

### Vista general (diagrama)
```mermaid
flowchart LR
    A[Servicios de Dominio] -->|Eventos| B[Notification Orchestrator]
    B -->|publica| C[RabbitMQ vhost foro]
    C -->|notifications.queue| D[Delivery Worker]
    D --> E1[SMTP SendGrid]
    D --> E2[Twilio SMS]
    D --> E3[Twilio WhatsApp]
    D --> E4[FCM WebPush]
    subgraph API
        F[FastAPI notify]
    end
    F --> C
    subgraph Scheduler
        G[APScheduler]
    end
    G -->|publica programado| C
```

### Topología de RabbitMQ (simplificada)
```mermaid
flowchart TB
    X[notifications.exchange] -->|notifications.key| Q[notifications.queue]

    subgraph Retries
        XR1[exchange.retry.1] --> R1[queue.retry.1 TTL5s]
        XR2[exchange.retry.2] --> R2[queue.retry.2 TTL30s]
        XR3[exchange.retry.3] --> R3[queue.retry.3 TTL120s]
    end

    subgraph DeadLetter
        DLX_EX[notifications.exchange.dlx] --> DLQ_Q[notifications.queue.dlq]
    end
```

### Diagrama general de la plataforma (con BDs)
```mermaid
flowchart LR
    subgraph Dominio
        APP[Aplicacion de Dominio];
        DB_APP[(BD Dominio)];
        APP <--> DB_APP;
    end

    subgraph Orquestador
        ORCH[Orquestador de Notificaciones];
        DB_ORCH[(BD Orquestador)];
        ORCH <--> DB_ORCH;
    end

    subgraph Delivery
        API[Servicio de Notificaciones API];
        WRK[Worker de Entrega];
        SCH[Scheduler];
    end

    MQ[(RabbitMQ)];

    APP -->|Eventos| ORCH;
    ORCH -->|publica| MQ;
    API -->|/notify| MQ;
    SCH -->|programa| MQ;
    MQ --> WRK;

    WRK --> SMTP[SMTP SendGrid];
    WRK --> SMS[Twilio SMS];
    WRK --> WA[Twilio WhatsApp];
    WRK --> PUSH[FCM WebPush];
```

### Flujo completo de microservicios (interacciones detalladas)
```mermaid
sequenceDiagram
    participant U as Usuario/Cliente
    participant D as Servicio Dominio
    participant O as Orquestador
    participant MQ as RabbitMQ
    participant API as API Notificaciones
    participant W as Worker
    participant S as Scheduler
    participant P as Proveedores Externos

    Note over U,P: Flujo 1: Notificación inmediata
    U->>D: Acción del usuario (registro, compra, etc.)
    D->>D: Procesa lógica de negocio
    D->>O: Evento: {event_type, user, template, params}
    O->>O: Aplica reglas de orquestación
    O->>O: Selecciona canal y resuelve plantilla
    O->>MQ: Publica mensaje listo para envío
    MQ->>W: Consume de notifications.queue
    W->>W: Identifica canal (email/sms/whatsapp/push)
    W->>P: Envía notificación al proveedor
    P-->>W: Respuesta (éxito/fallo)
    
    alt Fallo temporal
        W->>MQ: Reencola en retry.1 (5s)
        MQ->>W: Reintenta después de 5s
        W->>P: Reintenta envío
    else Fallo persistente
        W->>MQ: Envía a DLQ
    end

    Note over U,P: Flujo 2: Notificación programada
    U->>API: POST /notifications/schedule
    API->>API: Valida y almacena en BD
    API->>S: Programa tarea para fecha futura
    S->>S: Espera hasta fecha programada
    S->>MQ: Publica mensaje cuando llega la hora
    MQ->>W: Procesa como flujo normal

    Note over U,P: Flujo 3: Consulta y gestión
    U->>API: GET /notifications (con filtros)
    API->>API: Consulta BD con filtros/paginación
    API-->>U: Lista de notificaciones
    
    U->>API: GET /schedules
    API->>API: Consulta schedules pendientes
    API-->>U: Lista de schedules programados
    
    U->>API: DELETE /schedules/{id}
    API->>API: Cancela schedule pendiente
    API-->>U: Confirmación de cancelación

    Note over U,P: Flujo 4: Webhooks y respuestas
    P->>API: Webhook (WhatsApp, SMS status)
    API->>API: Procesa respuesta del proveedor
    API->>API: Actualiza estado en BD
```

---

## RabbitMQ (vhost foro)

#### Notas de persistencia por componente
- BD Dominio:
  - Datos de negocio (usuarios, pedidos, etc.).
  - Fuente de verdad para la Aplicación de Dominio y autenticación externa si aplica.
- BD Orquestador:
  - Reglas de orquestación, plantillas base, preferencias/opt‑in por usuario, historial de orquestaciones y correlación de eventos.
  - Útil para trazabilidad entre evento de negocio y mensajes construidos (trace_id, event_id).
- BD del Servicio de Notificaciones (Delivery):
  - `NotificationChannelConfig`: credenciales y parámetros por canal (SMTP/Twilio/FCM, etc.).
  - `Notification`: registro mínimo de envíos (opcional si lo requiere auditoría).
  - `NotificationMetrics`: agregados simples para monitoreo.
  - `User`: soporte de autenticación JWT del propio servicio (login/register de pruebas).
  - Este servicio no almacena plantillas fuertes ni reglas; recibe el mensaje ya construido desde el Orquestador.
- Usuarios (ejemplo de roles en este stack local):
  - orchestrator_user/orch_pass: permisos totales en vhost foro.
  - notifications_user/notif_pass: permisos sobre recursos notifications.* (exchanges y colas).
- Topología que crea el servicio:
  - Exchange principal: notifications.exchange (direct, durable)
  - Cola principal: notifications.queue (durable, x-dead-letter-exchange=notifications.exchange.dlx)
  - Exchange DLX: notifications.exchange.dlx (fanout) → Cola DLQ: notifications.queue.dlq
  - Retries con backoff: exchanges notifications.exchange.retry.{1..3} y colas notifications.queue.retry.{1..3} con TTLs crecientes y dead-letter de vuelta al exchange principal.

---

## Componentes del proyecto (carpeta app/)
- main.py: API FastAPI.
  - /health: healthcheck.
  - /notify: publica un payload en RabbitMQ.
  - /notify-auth: igual que /notify pero protegido con JWT.
  - /login y /register: autenticación/registro básica para pruebas.
  - /webhook/whatsapp: ejemplo de recepción de webhooks.
- messaging.py: conexión a RabbitMQ (publicación y setup básico compatible con la topología del worker).
- worker.py: consumidor de RabbitMQ.
  - Lee de notifications.queue, ejecuta el envío usando el Strategy de canales y gestiona reintentos/DLQ.
- scheduler.py: Scheduler (APScheduler) para programar envíos y publicar en RabbitMQ cuando corresponda.
- channels/*: canales concretos con Strategy Pattern.
  - base.py: interfaz abstracta Channel.
  - email.py, sms.py, whatsapp.py, push.py.
  - factory.py: mapea enum → implementación correspondiente.
- db.py, models.py: SQLAlchemy ORM (tablas, modelos y semillas de configuración de canales) y sesión a PostgreSQL.
- auth.py: utilidades de JWT y hashing de contraseñas (passlib/python-jose).
- templates/: plantillas Jinja2 para correos.

---

## Flujos principales
1) Envío estándar (end-to-end):
   - Cliente/Orchestrator publica un evento con canal/destino/mensaje en notifications.exchange (routing key notifications.key).
   - Este servicio lo publica vía API (/notify) o el Orchestrator lo publica directamente.
   - Worker consume de notifications.queue, crea el Channel correcto (factory) y ejecuta el envío.
   - Si falla, reintenta con backoff. Si agota reintentos, se envía a DLQ.

2) Envío programado:
   - scheduler.py agenda un job (ejemplo demo) y, al llegar la hora, publica el payload en RabbitMQ.
   - El worker procesa el mensaje como en el flujo normal.

---

## Variables de entorno (archivo .env)
RabbitMQ
- RABBITMQ_HOST=rabbitmq
- RABBITMQ_PORT=5672
- RABBITMQ_VHOST=foro
- RABBITMQ_USERNAME=notifications_user
- RABBITMQ_PASSWORD=notif_pass
- AMQP_EXCHANGE=notifications.exchange
- AMQP_EXCHANGE_TYPE=direct   # Cambiar a "topic" si usas orquestador.events
- AMQP_QUEUE=notifications.queue
- AMQP_ROUTING_KEY=notifications.key
- MESSAGING_DECLARE_INFRA=true # false si el broker ya trae la topología

JWT
- SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

Base de datos
- DB_URL=postgresql+psycopg2://notifications:notifications@postgres:5432/notifications

Email (SMTP/SendGrid)
- SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, FROM_NAME, SENDGRID_API_KEY

Twilio (SMS/WhatsApp)
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, TWILIO_WHATSAPP_FROM, WHATSAPP_WEBHOOK_URL

Push (Firebase / Web Push)
- FIREBASE_PROJECT_ID, FIREBASE_SERVICE_ACCOUNT_KEY (JSON de service account en una sola línea)
- WEB_VAPID_PUBLIC_KEY, WEB_VAPID_PRIVATE_KEY

Worker (reintentos)
- WORKER_MAX_RETRIES=3
- WORKER_RETRY_DELAY_1=5
- WORKER_RETRY_DELAY_2=30
- WORKER_RETRY_DELAY_3=120
- DEFAULT_CHANNEL=email
- WORKER_DECLARE_INFRA=true # false si el broker ya trae la topología

Scheduler (demo)
- SCHEDULER_DEMO_CHANNEL, SCHEDULER_DEMO_DESTINATION, SCHEDULER_DEMO_DELAY_SEC

---

## Ejecución (Docker Compose)
1) docker compose build --no-cache
2) docker compose up -d
3) Verificar estado:
   - docker ps
   - RabbitMQ UI: http://localhost:15672 (admin/admin). Vhost: foro.
4) Logs rápidos:
   - API: docker logs notifications-service-micro --since=1m
   - Worker: docker logs notifications-worker --since=1m
   - Scheduler: docker logs notifications-scheduler --since=1m

---

## Pruebas rápidas
Healthcheck
- curl http://localhost:8080/health → {"status":"ok"}

Publicar un mensaje (ejemplo push)
- docker exec notifications-service-micro curl -s -X POST http://localhost:8080/notify -H "Content-Type: application/json" -d '{"channel":"push","destination":"<TOKEN>","subject":"Hola","message":"Prueba"}'
- Monitorear worker: docker logs -f notifications-worker

### Manejo de Mensajes HTML vs Texto

El sistema ahora soporta mensajes específicos por canal:

- **Email**: Recibe contenido HTML que se renderiza directamente
- **SMS**: Recibe texto plano (sin HTML)
- **WhatsApp**: Recibe texto plano con soporte para emojis y saltos de línea
- **Push**: Recibe texto plano

Los templates HTML son manejados por el orquestador, no por este servicio.

### Nuevos endpoints multi-canal

**POST /notify-multi** - Envío a múltiples canales (sin autenticación)
```bash
curl -X POST "http://localhost:8080/notify-multi" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": {
      "email": "juan@example.com",
      "sms": "+573225035863",
      "whatsapp": "+573225035863"
    },
    "message": {
      "email": "<html><body><h1>¡Hola Juan!</h1><p>Mensaje HTML para email</p></body></html>",
      "sms": "¡Hola Juan! Mensaje de texto para SMS",
      "whatsapp": "¡Hola Juan! 👋\n\nMensaje de texto para WhatsApp"
    },
    "subject": "Mensaje de prueba",
    "metadata": {
      "tenantId": "acme",
      "template": "welcome"
    }
  }'
```

**POST /notify-multi-auth** - Envío a múltiples canales (con autenticación JWT)
```bash
# Primero obtener token
curl -X POST "http://localhost:8080/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin_pass"

# Luego enviar notificación
curl -X POST "http://localhost:8080/notify-multi-auth" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": {
      "email": "juan@example.com",
      "sms": "+573225035863"
    },
    "message": {
      "email": "<html><body><h1>Mensaje importante</h1><p>Contenido HTML autenticado</p></body></html>",
      "sms": "Mensaje importante - Contenido texto autenticado"
    },
    "subject": "Mensaje importante"
  }'
```

---

## Notas de seguridad
- No publiques el JSON de la service account de Firebase.
- Aísla usuarios y permisos por vhost; en producción, separa aún más los roles y usa TLS si es necesario.

---

## Guía de extensibilidad (añadir un canal nuevo)
1) Crear app/channels/<nuevo>.py implementando Channel.
2) Registrar en app/channels/factory.py.
3) Añadir config por defecto en db.init_default_channels si aplica.
4) Documentar nuevas variables en este README.

---

## Solución de problemas (FAQ)
- ACCESS_REFUSED (RabbitMQ):
  - Verifica usuario, contraseña, vhost y permisos. Este servicio usa notifications_user/notif_pass en el vhost foro.
- PRECONDITION_FAILED (inequivalent arg x-dead-letter-exchange):
  - Ocurre si la cola ya existía con otros argumentos. Borra la cola o usa get_queue sin redeclarar con otros args.
- python-multipart requerido:
  - Añadido en requirements. Si usas formularios, debe estar instalado.
- Template Jinja2 no encontrado:
  - Verifica rutas y que templates/ esté copiado al contenedor.

---

## Glosario
- Exchange: Punto de distribución donde se publican mensajes en RabbitMQ.
- Queue (Cola): Buzón del que consumen los workers.
- Routing Key: Etiqueta usada por el exchange para direccionar mensajes.
- DLQ (Dead Letter Queue): Cola para mensajes que no pudieron procesarse definitivamente.
- DLX (Dead Letter Exchange): Exchange que recibe mensajes muertos y los redirige a la DLQ.
- TTL (Time-To-Live): Tiempo de vida de un mensaje en una cola; al expirar puede redirigirse vía DLX.
- Backoff exponencial: Reintentos con esperas crecientes (p.ej., 5s, 30s, 120s).
- Strategy Pattern: Patrón que permite cambiar el “cómo enviar” (email/sms/etc.) sin cambiar el consumidor.
- Factory Pattern: Componente que crea la implementación correcta de Channel según el enum.
- Vhost: Espacio lógico aislado dentro de RabbitMQ; permite separar permisos y recursos.
- APScheduler: Librería para programar tareas/asignar triggers (DateTrigger, intervalos, cron, etc.).
- JWT: Token de autenticación para proteger endpoints.

---

## Mantenimiento de este README
- Si se modifica la infraestructura (topología, variables, servicios o permisos), actualiza aquí los cambios.

---

## Contratos de datos entre microservicios (mensajes y ejemplo práctico)
### 1) Evento desde un Servicio de Dominio → Orquestador
- El dominio envía información “de intención” (qué pasó y a quién), NO un mensaje listo para enviar.
```json
{
  "event_id": "evt_1a2b3c",
  "event_type": "user.welcome",
  "user": {
    "id": 123,
    "email": "ana@example.com",
    "phone_e164": "+573001112233",
    "whatsapp_e164": "+573001112233",
    "push_token": "fcm_device_token"
  },
  "template": "welcome",
  "params": {"first_name": "Ana"},
  "preferred_channels": ["email", "push"],
  "schedule_at": null,
  "metadata": {"source": "app-web"}
}
```

### 2) Mensaje del Orquestador → RabbitMQ (consumido por este servicio)
- El orquestador "construye" el mensaje listo para entrega: selecciona canal(es), resuelve plantillas y datos.

#### Formato Multi-Canal (NUEVO)
```json
{
  "destination": {
    "email": "ana@example.com",
    "sms": "+573225035863",
    "whatsapp": "+573225035863",
    "push": "fcm_device_token_12345"
  },
  "message": {
    "email": "<html><body><h1>¡Bienvenida Ana!</h1><p>Gracias por registrarte en nuestro servicio.</p><p>Tu cuenta ha sido activada exitosamente.</p></body></html>",
    "sms": "¡Bienvenida Ana! Gracias por registrarte. Tu cuenta ha sido activada.",
    "whatsapp": "¡Hola Ana! 👋\n\nGracias por registrarte en nuestro servicio.\n\nTu cuenta ha sido activada exitosamente. 🎉",
    "push": "¡Bienvenida Ana! Tu cuenta ha sido activada."
  },
  "subject": "¡Bienvenida, Ana!",
  "metadata": {
    "tenantId": "acme",
    "template": "welcome",
    "event_id": "evt_1a2b3c",
    "event_type": "user.welcome",
    "trace_id": "tr_9x8y7z"
  }
}
```

#### Formato Simple (Compatible con versión anterior)
```json
{
  "channel": "email",
  "destination": "ana@example.com",
  "subject": "¡Bienvenida, Ana!",
  "message": "Hola Ana, gracias por registrarte.",
  "metadata": {
    "event_id": "evt_1a2b3c",
    "event_type": "user.welcome",
    "trace_id": "tr_9x8y7z"
  }
}
```

### Variantes por canal (payload esperado por el Delivery)
- email:
```json
{"channel":"email","destination":"ana@example.com","subject":"Asunto","message":"Cuerpo"}
```
- sms:
```json
{"channel":"sms","destination":"+573001112233","message":"Texto corto"}
```
- whatsapp:
```json
{"channel":"whatsapp","destination":"+573001112233","message":"Texto WA"}
```
- push:
```json
{"channel":"push","destination":"fcm_device_token","subject":"Título","message":"Body"}
```

### Ejemplo práctico (user.welcome)
1) Dominio emite el evento (intención): ver ejemplo 1.
2) Orquestador aplica reglas:
   - Elige canal “email” si existe email válido; como fallback, “push”.
   - Resuelve plantilla "welcome" con {first_name:"Ana"} → subject y body renderizados.
   - Publica a RabbitMQ (exchange notifications.exchange, routing key notifications.key) el payload del ejemplo 2.
3) Este Delivery consume de notifications.queue y envía por el canal indicado.

### Diagrama de secuencia (resumen)
```mermaid
sequenceDiagram
    participant D as Dominio
    participant O as Orchestrator
    participant MQ as RabbitMQ
    participant W as Delivery-Worker
    participant P as Proveedor (Email/SMS/Push/WA)

    D->>O: Evento {event_type, user, template, params}
    O->>O: Reglas + Plantillas + Selección de canal
    O->>MQ: Publish {channel, destination, subject, message, data}
    W->>MQ: Consume notifications.queue
    W->>P: Enviar por canal (proveedor)
    P-->>W: Respuesta OK/Fail
    alt fallo temporal
        W->>MQ: Reencola en retry.{1..3}
    else fallo definitivo
        W->>MQ: Envía a DLQ
    end
```

### Validaciones mínimas que hace el Delivery
- Requiere `channel` válido y `destination` con formato del canal (email válido, E.164 para SMS/WA, token para push).
- Si faltan campos o el proveedor responde error no recuperable, el mensaje terminará en DLQ tras reintentos.


