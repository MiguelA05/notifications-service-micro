Notifications Service Micro (Python/FastAPI)

Descripción general
- Microservicio de “Delivery” de notificaciones. Recibe eventos por RabbitMQ y envía por Email/SMS/WhatsApp/Push.
- Pensado para convivir con un Orquestador de Notificaciones (otro servicio) y con los Microservicios de Dominio (usuarios, ventas, etc.).
- Infraestructura lista para producción mínima: Docker Compose, PostgreSQL, RabbitMQ, autenticación JWT, reintentos y DLQ, y un Scheduler para envíos programados.

Arquitectura y relación con otros servicios
- Servicios de Dominio: publican eventos al Orquestador.
- Orchestrator (servicio aparte): aplica reglas, elige canal y publica al exchange de notificaciones en RabbitMQ.
- Este proyecto (Delivery): consume la cola de notificaciones y realiza el envío real a los proveedores.

Vista general (diagrama)
```mermaid
flowchart LR
    A[Servicios de Dominio
    (Usuarios, Ventas,
    Envíos...)] -- Eventos --> B[Notification Orchestrator
    (reglas, plantillas,
    selección de canal)]
    B -- publica --> C{{RabbitMQ
    vhost: foro}}
    C -->|notifications.queue| D[MS Notificaciones (Delivery)
    worker.py]
    D -->|Email| E1[(SMTP/SendGrid)]
    D -->|SMS| E2[(Twilio SMS)]
    D -->|WhatsApp| E3[(Twilio WhatsApp)]
    D -->|Push| E4[(FCM/WebPush)]
    subgraph API
      F[FastAPI /notify,/login]
    end
    F -- publica --> C
    subgraph Scheduler
      G[APScheduler]
    end
    G -- publica (programado) --> C
```

Topología de RabbitMQ (simplificada)
```mermaid
flowchart TB
  subgraph Principal
    X[notifications.exchange\n(direct)]
    Q[notifications.queue\n(durable)\nDLX-> notifications.exchange.dlx]
    X -- notifications.key --> Q
  end

  subgraph Retries
    R1[queue.retry.1\nTTL=5s\nDLX-> notifications.exchange]
    R2[queue.retry.2\nTTL=30s\nDLX-> notifications.exchange]
    R3[queue.retry.3\nTTL=120s\nDLX-> notifications.exchange]
    XR1[exchange.retry.1]
    XR2[exchange.retry.2]
    XR3[exchange.retry.3]
    XR1 --> R1
    XR2 --> R2
    XR3 --> R3
  end

  subgraph DLQ
    DLX[notifications.exchange.dlx\n(fanout)]
    DLQ[notifications.queue.dlq]
    DLX --> DLQ
  end

  style X fill:#eef,stroke:#88f
  style Q fill:#efe,stroke:#5a5
  style DLX fill:#fee,stroke:#f88
  style DLQ fill:#fee,stroke:#f88
```

RabbitMQ (vhost foro)
- Usuarios (ejemplo de roles en este stack local):
  - orchestrator_user/orch_pass: permisos totales en vhost foro.
  - notifications_user/notif_pass: permisos sobre recursos notifications.* (exchanges y colas).
- Topología que crea el servicio:
  - Exchange principal: notifications.exchange (direct, durable)
  - Cola principal: notifications.queue (durable, x-dead-letter-exchange=notifications.exchange.dlx)
  - Exchange DLX: notifications.exchange.dlx (fanout) → Cola DLQ: notifications.queue.dlq
  - Retries con backoff: exchanges notifications.exchange.retry.{1..3} y colas notifications.queue.retry.{1..3} con TTLs crecientes y dead-letter de vuelta al exchange principal.

Componentes del proyecto (carpeta app/)
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

Flujos principales
1) Envío estándar (end-to-end):
   - Cliente/Orchestrator publica un evento con canal/destino/mensaje en notifications.exchange (routing key notifications.key).
   - Este servicio lo publica vía API (/notify) o el Orchestrator lo publica directamente.
   - Worker consume de notifications.queue, crea el Channel correcto (factory) y ejecuta el envío.
   - Si falla, reintenta con backoff. Si agota reintentos, se envía a DLQ.

2) Envío programado:
   - scheduler.py agenda un job (ejemplo demo) y, al llegar la hora, publica el payload en RabbitMQ.
   - El worker procesa el mensaje como en el flujo normal.

Variables de entorno (archivo .env)
RabbitMQ
- RABBITMQ_HOST=rabbitmq
- RABBITMQ_PORT=5672
- RABBITMQ_VHOST=foro
- RABBITMQ_USERNAME=notifications_user
- RABBITMQ_PASSWORD=notif_pass
- AMQP_EXCHANGE=notifications.exchange
- AMQP_QUEUE=notifications.queue
- AMQP_ROUTING_KEY=notifications.key

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

Scheduler (demo)
- SCHEDULER_DEMO_CHANNEL, SCHEDULER_DEMO_DESTINATION, SCHEDULER_DEMO_DELAY_SEC

Ejecución (Docker Compose)
1) docker compose build --no-cache
2) docker compose up -d
3) Verificar estado:
   - docker ps
   - RabbitMQ UI: http://localhost:15672 (admin/admin). Vhost: foro.
4) Logs rápidos:
   - API: docker logs notifications-service-micro --since=1m
   - Worker: docker logs notifications-worker --since=1m
   - Scheduler: docker logs notifications-scheduler --since=1m

Pruebas rápidas
Healthcheck
- curl http://localhost:8080/health → {"status":"ok"}

Publicar un mensaje (ejemplo push)
- docker exec notifications-service-micro curl -s -X POST http://localhost:8080/notify -H "Content-Type: application/json" -d '{"channel":"push","destination":"<TOKEN>","subject":"Hola","message":"Prueba"}'
- Monitorear worker: docker logs -f notifications-worker

Notas de seguridad
- No publiques el JSON de la service account de Firebase.
- Aísla usuarios y permisos por vhost; en producción, separa aún más los roles y usa TLS si es necesario.

Guía de extensibilidad (añadir un canal nuevo)
1) Crear app/channels/<nuevo>.py implementando Channel.
2) Registrar en app/channels/factory.py.
3) Añadir config por defecto en db.init_default_channels si aplica.
4) Documentar nuevas variables en este README.

Solución de problemas (FAQ)
- ACCESS_REFUSED (RabbitMQ):
  - Verifica usuario, contraseña, vhost y permisos. Este servicio usa notifications_user/notif_pass en el vhost foro.
- PRECONDITION_FAILED (inequivalent arg x-dead-letter-exchange):
  - Ocurre si la cola ya existía con otros argumentos. Borra la cola o usa get_queue sin redeclarar con otros args.
- python-multipart requerido:
  - Añadido en requirements. Si usas formularios, debe estar instalado.
- Template Jinja2 no encontrado:
  - Verifica rutas y que templates/ esté copiado al contenedor.

Glosario
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

Mantenimiento de este README
- Si se modifica la infraestructura (topología, variables, servicios o permisos), actualiza aquí los cambios.


