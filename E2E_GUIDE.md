## Guía E2E: Trazabilidad entre Dominio, Orquestador y Notificaciones

Esta guía muestra cómo levantar el stack unificado, realizar registro y login en el servicio de dominio y verificar que:
- El orquestador procese los eventos y publique a `notifications.queue`.
- El worker de notificaciones envíe email y SMS.

Destinos para las pruebas:
- Email: miraortega2020@gmail.com
- SMS: +573225035863

### 1) Requisitos
- Docker Desktop en ejecución
- PowerShell (Windows)

### 2) Levantar el stack unificado
Ejecuta en el directorio `notifications-service-micro`:

```powershell
# Construir imágenes
docker compose -f docker-compose.unified.yml build

# Levantar servicios clave (ajusta si ya están arriba)
$services = @(
  'rabbitmq','postgres_notifications','postgres_domain','orchestrator-db',
  'notifications-api','notifications-worker','domain-service','orchestrator-service'
)
docker compose -f docker-compose.unified.yml up -d $services

# Verificar estado
docker compose -f docker-compose.unified.yml ps
```

### 3) Health de notificaciones API
```powershell
Invoke-RestMethod -Method GET -Uri http://localhost:8080/health | ConvertTo-Json -Depth 4
```
Esperado: `{ "status": "ok" }`.

### 4) Registrar usuario en Dominio
Usa un usuario aleatorio para evitar conflictos:
```powershell
$u = "trace_" + ([guid]::NewGuid().ToString('N').Substring(0,8))
$register = @{ usuario=$u; correo=($u+"@example.com"); clave="demo123"; numeroTelefono="+573225035863" } |
  ConvertTo-Json -Compress
Invoke-RestMethod -Method POST -Uri http://localhost:8081/v1/usuarios -ContentType 'application/json' -Body $register
```
Esperado: 201 Created. En logs del dominio: publicación de `REGISTRO_USUARIO` (`auth.registered`).

### 5) Login en Dominio
```powershell
$login = @{ usuario=$u; clave="demo123" } | ConvertTo-Json -Compress
Invoke-RestMethod -Method POST -Uri http://localhost:8081/v1/sesiones -ContentType 'application/json' -Body $login |
  ConvertTo-Json -Depth 4
```
Esperado: 200 OK con token. En logs del dominio: publicación de `AUTENTICACION` (`auth.login`).

### 6) Verificar logs
- Orquestador:
```powershell
docker logs --since=5m orquestador-solicitudes-micro
```
Debe mostrar recepción de eventos y publicación a `notifications.queue` (HTML para email y texto SMS).

- Worker de notificaciones:
```powershell
docker logs --since=5m notifications-worker
```
Debe mostrar envíos:
- Email enviado (para paso 7 se usa `miraortega2020@gmail.com`).
- SMS a `+573225035863` con código 201 de Twilio.

### 7) Disparar eventos manualmente (opcional, via RabbitMQ HTTP API)
```powershell
$pair = "admin:admin_pass"
$b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$headers = @{ Authorization = "Basic $b64"; "Content-Type" = "application/json" }

# REGISTRO_USUARIO con email real
$inner = @{ usuario = "e2e_user"; correo = "miraortega2020@gmail.com"; numeroTelefono = "+573225035863"; codigo = $null; fecha = (Get-Date -Format o) } |
  ConvertTo-Json -Compress
$payload = @{ id = "evt-" + [guid]::NewGuid().ToString(); tipoAccion = "REGISTRO_USUARIO"; timestamp = (Get-Date -Format o); payload = (ConvertFrom-Json $inner) } |
  ConvertTo-Json -Compress
$body = @{ properties = @{}; routing_key = "auth.registered"; payload = $payload; payload_encoding = "string" } |
  ConvertTo-Json -Compress
Invoke-RestMethod -Method POST -Uri "http://localhost:15672/api/exchanges/foro/dominio.events/publish" -Headers $headers -Body $body |
  ConvertTo-Json -Depth 4

# AUTENTICACION (login)
$inner2 = @{ usuario = "e2e_user"; correo = "miraortega2020@gmail.com"; numeroTelefono = "+573225035863"; fecha = (Get-Date -Format o) } |
  ConvertTo-Json -Compress
$payload2 = @{ id = "evt-" + [guid]::NewGuid().ToString(); tipoAccion = "AUTENTICACION"; timestamp = (Get-Date -Format o); payload = (ConvertFrom-Json $inner2) } |
  ConvertTo-Json -Compress
$body2 = @{ properties = @{}; routing_key = "auth.login"; payload = $payload2; payload_encoding = "string" } |
  ConvertTo-Json -Compress
Invoke-RestMethod -Method POST -Uri "http://localhost:15672/api/exchanges/foro/dominio.events/publish" -Headers $headers -Body $body2 |
  ConvertTo-Json -Depth 4
```

### 8) Verificar persistencia en BD
Recomendado: psql interactivo para evitar problemas de comillas en PowerShell.

Orquestador:
```powershell
docker exec -it postgres-orchestrator psql -U user -d mydb
-- dentro de psql
SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='public';
SELECT id, tipoAccion, usuario, correo, timestamp FROM "Evento" ORDER BY timestamp DESC LIMIT 5;
\q
```

Notificaciones:
```powershell
docker exec -it postgres-notifications psql -U notifications -d notifications
-- dentro de psql
\dt
SELECT * FROM notifications ORDER BY created_at DESC LIMIT 5;
\q
```

Alternativa no interactiva (orquestador):
```powershell
docker exec -i postgres-orchestrator sh -lc "cat <<'SQL' | psql -U user -d mydb
SELECT id, tipoAccion, usuario, correo, timestamp FROM \"Evento\" ORDER BY timestamp DESC LIMIT 5;
SQL"
```

### 9) Problemas comunes
- Evita pipes ("| cat") y "&&" en PowerShell; ejecuta comandos por separado.
- Si el dominio devuelve 500/403/409 tras un reset de BD, espera unos segundos (Hibernate crea/actualiza el esquema) y reintenta.
- Si el worker no conecta a RabbitMQ, espera a que `rabbitmq` esté healthy y reinicia el worker.

### 10) Apagar el stack
```powershell
docker compose -f docker-compose.unified.yml down --remove-orphans
```

Con esto deberías lograr un flujo satisfactorio: dominio publica eventos, orquestador los procesa y el worker envía email a `miraortega2020@gmail.com` y SMS a `+573225035863`. 
