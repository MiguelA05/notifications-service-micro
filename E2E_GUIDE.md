# Guía E2E: Sistema de Microservicios de Notificaciones

Esta guía te permitirá probar completamente el sistema de microservicios de notificaciones, desde el registro de usuarios hasta la entrega de notificaciones por email y SMS.

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Configuración del Entorno](#configuración-del-entorno)
3. [Verificación de Servicios](#verificación-de-servicios)
4. [Pruebas de Endpoints](#pruebas-de-endpoints)
5. [Verificación de Notificaciones](#verificación-de-notificaciones)
6. [Pruebas con Postman](#pruebas-con-postman)
7. [Solución de Problemas](#solución-de-problemas)
8. [Limpieza del Entorno](#limpieza-del-entorno)

---

## 🛠️ Requisitos Previos

- **Docker Desktop** instalado y ejecutándose
- **PowerShell** (Windows) o **Terminal** (Linux/Mac)
- **Postman** (opcional, para pruebas GUI)
- **Navegador web** para verificar RabbitMQ Management

---

## 🚀 Configuración del Entorno

### Paso 1: Preparar el Entorno

```powershell
# Navegar al directorio del proyecto
cd C:\Users\mirao\OneDrive\Documentos\GitHub\notifications-service-micro

# Limpiar contenedores y volúmenes existentes (opcional)
docker-compose -f docker-compose.unified.yml down --volumes --remove-orphans
docker system prune -a --volumes -f
```

### Paso 2: Construir y Levantar Servicios

```powershell
# Construir todas las imágenes
docker-compose -f docker-compose.unified.yml build --no-cache

# Levantar todos los servicios
docker-compose -f docker-compose.unified.yml up -d

# Verificar que todos los servicios estén funcionando
docker-compose -f docker-compose.unified.yml ps
```

**✅ Resultado Esperado:** Todos los servicios deben mostrar estado "Up" y "healthy" para las bases de datos.

---

## 🔍 Verificación de Servicios

### Verificar Health Checks

```powershell
# Servicio de Notificaciones (Puerto 8080)
Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing

# Servicio de Dominio (Puerto 8081)
Invoke-WebRequest -Uri "http://localhost:8081/v1/usuarios" -Method GET -UseBasicParsing

# Orquestador (Puerto 3000)
Invoke-WebRequest -Uri "http://localhost:3000/health" -UseBasicParsing

# RabbitMQ Management (Puerto 15672)
# Abrir en navegador: http://localhost:15672
# Usuario: admin, Contraseña: admin_pass
```

**✅ Resultado Esperado:** 
- Notificaciones: `{"status":"ok"}`
- Dominio: Error 401 (esperado, requiere autenticación)
- Orquestador: `{"ok":true}`
- RabbitMQ: Interfaz web accesible

---

## 🧪 Pruebas de Endpoints

### Prueba 1: Registro de Usuario

**Objetivo:** Crear un nuevo usuario y verificar que se genere una notificación de confirmación por email.

```powershell
# Generar datos únicos para evitar conflictos
$timestamp = Get-Date -Format 'yyyyMMddHHmmss'
$usuario = "testuser_$timestamp"
$correo = "test$timestamp@example.com"

# Crear payload de registro
$body = @{
    usuario = $usuario
    correo = $correo
    numeroTelefono = "+573225035863"
    clave = "TestPassword123!"
} | ConvertTo-Json

# Ejecutar registro
Write-Host "Registrando usuario: $usuario" -ForegroundColor Green
$response = Invoke-WebRequest -Uri "http://localhost:8081/v1/usuarios" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing

# Mostrar resultado
Write-Host "Status: $($response.StatusCode)" -ForegroundColor Yellow
Write-Host "Response: $($response.Content)" -ForegroundColor Cyan
```

**✅ Resultado Esperado:** 
- Status Code: 201
- Response: `{"error":false,"respuesta":"Usuario registrado exitosamente"}`

### Prueba 2: Login de Usuario

**Objetivo:** Autenticar el usuario y verificar que se generen notificaciones múltiples (email + SMS).

```powershell
# Crear payload de login
$loginBody = @{
    usuario = $usuario
    clave = "TestPassword123!"
} | ConvertTo-Json

# Ejecutar login
Write-Host "Iniciando sesión con usuario: $usuario" -ForegroundColor Green
$loginResponse = Invoke-WebRequest -Uri "http://localhost:8081/v1/sesiones" -Method POST -Body $loginBody -ContentType "application/json" -UseBasicParsing

# Mostrar resultado
Write-Host "Status: $($loginResponse.StatusCode)" -ForegroundColor Yellow
$tokenData = $loginResponse.Content | ConvertFrom-Json
Write-Host "Token generado: $($tokenData.respuesta.token.Substring(0,50))..." -ForegroundColor Cyan
```

**✅ Resultado Esperado:** 
- Status Code: 200
- Response: Token JWT válido

### Prueba 3: Solicitud de Cambio de Contraseña

**Objetivo:** Solicitar cambio de contraseña y verificar que se genere una notificación con código de verificación.

```powershell
# Crear payload para solicitud de código
$codigoBody = @{
    usuario = $usuario
} | ConvertTo-Json

# Ejecutar solicitud
Write-Host "Solicitando código de cambio de contraseña para: $usuario" -ForegroundColor Green
$codigoResponse = Invoke-WebRequest -Uri "http://localhost:8081/v1/codigos" -Method POST -Body $codigoBody -ContentType "application/json" -UseBasicParsing

# Mostrar resultado
Write-Host "Status: $($codigoResponse.StatusCode)" -ForegroundColor Yellow
Write-Host "Response: $($codigoResponse.Content)" -ForegroundColor Cyan
```

**✅ Resultado Esperado:** 
- Status Code: 200
- Response: `{"error":false,"respuesta":"Código de verificación enviado exitosamente al correo"}`

### Prueba 4: Notificaciones Directas (API de Notificaciones)

**Objetivo:** Probar el envío directo de notificaciones a través de la API.

```powershell
# Notificación por Email
$emailBody = @{
    channel = "email"
    destination = "miraortega2020@gmail.com"
    message = "Test de notificación directa por email"
    subject = "Test Directo - Email"
} | ConvertTo-Json

Write-Host "Enviando notificación por email..." -ForegroundColor Green
$emailResponse = Invoke-WebRequest -Uri "http://localhost:8080/v1/notifications" -Method POST -Body $emailBody -ContentType "application/json" -UseBasicParsing
Write-Host "Email Status: $($emailResponse.StatusCode)" -ForegroundColor Yellow

# Notificación por SMS
$smsBody = @{
    channel = "sms"
    destination = "+573225035863"
    message = "Test de notificación directa por SMS"
} | ConvertTo-Json

Write-Host "Enviando notificación por SMS..." -ForegroundColor Green
$smsResponse = Invoke-WebRequest -Uri "http://localhost:8080/v1/notifications" -Method POST -Body $smsBody -ContentType "application/json" -UseBasicParsing
Write-Host "SMS Status: $($smsResponse.StatusCode)" -ForegroundColor Yellow
```

**✅ Resultado Esperado:** 
- Status Code: 200 para ambos
- Response: `{"queued":true}`

---

## 📧 Verificación de Notificaciones

### Verificar Logs del Orquestador

```powershell
# Ver logs del orquestador (últimos 20 registros)
Write-Host "=== LOGS DEL ORQUESTADOR ===" -ForegroundColor Magenta
docker logs orquestador-solicitudes-micro --tail 20
```

**✅ Buscar en los logs:**
- `📤 Mensaje enviado a notifications.queue`
- Estructura JSON con `destination` y `message`
- Templates HTML para email y texto para SMS

### Verificar Logs del Worker de Notificaciones

```powershell
# Ver logs del worker (últimos 20 registros)
Write-Host "=== LOGS DEL WORKER ===" -ForegroundColor Magenta
docker logs notifications-worker --tail 20
```

**✅ Buscar en los logs:**
- `Email enviado a [email] con asunto [subject] via SMTP`
- `SMS enviado exitosamente. SID: [SID]`
- `Mensaje procesado correctamente`

### Verificar Logs del Servicio de Dominio

```powershell
# Ver logs del dominio (últimos 15 registros)
Write-Host "=== LOGS DEL DOMINIO ===" -ForegroundColor Magenta
docker logs jwtmanual-taller1-micro --tail 15
```

**✅ Buscar en los logs:**
- `Publicando evento: EventoDominio`
- `Routing key a usar: [routing_key]`
- `El evento fue publicado`

---

## 📮 Pruebas con Postman

### Colección de Postman

Crea una nueva colección en Postman con los siguientes requests:

#### 1. Health Check - Notificaciones
- **Method:** GET
- **URL:** `http://localhost:8080/health`
- **Expected:** `{"status":"ok"}`

#### 2. Health Check - Orquestador
- **Method:** GET
- **URL:** `http://localhost:3000/health`
- **Expected:** `{"ok":true}`

#### 3. Registro de Usuario
- **Method:** POST
- **URL:** `http://localhost:8081/v1/usuarios`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
```json
{
    "usuario": "testuser_postman",
    "correo": "test@example.com",
    "numeroTelefono": "+573225035863",
    "clave": "TestPassword123!"
}
```

#### 4. Login de Usuario
- **Method:** POST
- **URL:** `http://localhost:8081/v1/sesiones`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
```json
{
    "usuario": "testuser_postman",
    "clave": "TestPassword123!"
}
```

#### 5. Solicitud de Código
- **Method:** POST
- **URL:** `http://localhost:8081/v1/codigos`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
```json
{
    "usuario": "testuser_postman"
}
```

#### 6. Notificación Directa - Email (/v1/notifications)
- **Method:** POST
- **URL:** `http://localhost:8080/v1/notifications`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
```json
{
    "channel": "email",
    "destination": "miraortega2020@gmail.com",
    "message": "Test desde Postman - Email",
    "subject": "Test Postman"
}
```

#### 7. Notificación Directa - SMS (/v1/notifications)
- **Method:** POST
- **URL:** `http://localhost:8080/v1/notifications`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
```json
{
    "channel": "sms",
    "destination": "+573225035863",
    "message": "Test desde Postman - SMS"
}
```

#### 8. Notificación Multi-Canal - Email (/v1/notifications/multi)
- **Method:** POST
- **URL:** `http://localhost:8080/v1/notifications/multi`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
```json
{
    "destination": {
        "email": "miraortega2020@gmail.com"
    },
    "message": {
        "email": "Test desde Postman - Email Multi"
    },
    "subject": "Test Postman Multi"
}
```

#### 9. Notificación Multi-Canal - SMS (/v1/notifications/multi)
- **Method:** POST
- **URL:** `http://localhost:8080/v1/notifications/multi`
- **Headers:** `Content-Type: application/json`
- **Body (JSON):**
```json
{
    "destination": {
        "sms": "+573225035863"
    },
    "message": {
        "sms": "Test desde Postman - SMS Multi"
    }
}
```

---

## 🔄 Diferencias entre Endpoints de Notificaciones

### **Endpoint `/v1/notifications` - Notificaciones Directas**

**Uso recomendado:** Notificaciones simples y directas
**Esquema:** Simple y directo
```json
{
    "channel": "email|sms|whatsapp|push",
    "destination": "destino@ejemplo.com",
    "message": "Mensaje a enviar",
    "subject": "Asunto (opcional)"
}
```

**Ventajas:**
- ✅ Esquema simple y fácil de usar
- ✅ Ideal para notificaciones básicas
- ✅ Menos código para implementar

### **Endpoint `/v1/notifications/multi` - Notificaciones Multi-Canal**

**Uso recomendado:** Notificaciones complejas o múltiples canales
**Esquema:** Complejo y flexible
```json
{
    "destination": {
        "email": "destino@ejemplo.com",
        "sms": "+1234567890"
    },
    "message": {
        "email": "Mensaje HTML para email",
        "sms": "Mensaje de texto para SMS"
    },
    "subject": "Asunto (opcional)"
}
```

**Ventajas:**
- ✅ Soporte para múltiples canales simultáneos
- ✅ Mensajes personalizados por canal
- ✅ Mayor flexibilidad y control

### **¿Cuál usar?**

| **Caso de Uso** | **Endpoint Recomendado** | **Razón** |
|------------------|---------------------------|-----------|
| Notificación simple por email | `/notify` | Esquema más simple |
| Notificación simple por SMS | `/notify` | Esquema más simple |
| Notificación a múltiples canales | `/notify-multi` | Soporte nativo |
| Mensajes personalizados por canal | `/notify-multi` | Mayor flexibilidad |
| Integración rápida | `/notify` | Menos configuración |

---

## 🔧 Verificación de Base de Datos

### Verificar Eventos en Orquestador

```powershell
# Consultar eventos usando echo para evitar problemas de escape
echo 'SELECT id, "tipoAccion", usuario, correo FROM "Evento" ORDER BY timestamp DESC LIMIT 5;' | docker exec -i postgres-orchestrator psql -U user -d mydb
```

**✅ Resultado Esperado:** Debe mostrar los últimos 5 eventos con columnas:
- `id`: UUID del evento
- `tipoAccion`: Tipo de acción (REGISTRO_USUARIO, AUTENTICACION, RECUPERAR_PASSWORD)
- `usuario`: Nombre de usuario
- `correo`: Email del usuario

### Verificar Notificaciones

```powershell
# Consultar notificaciones usando echo para evitar problemas de escape
echo "SELECT id, channel, destination, status, created_at FROM notifications ORDER BY created_at DESC LIMIT 5;" | docker exec -i postgres-notifications psql -U notifications -d notifications
```

**✅ Resultado Esperado:** Debe mostrar las últimas 5 notificaciones con columnas:
- `id`: ID de la notificación
- `channel`: Canal usado (email, sms, etc.)
- `destination`: Destino de la notificación
- `status`: Estado de la notificación
- `created_at`: Fecha de creación

---

## 🐛 Solución de Problemas

### Problema: Error 500 en Registro
**Síntoma:** El servicio de dominio devuelve error 500
**Solución:**
```powershell
# Verificar logs del dominio
docker logs jwtmanual-taller1-micro --tail 10

# Si hay error de tabla faltante, ejecutar migraciones
docker exec orquestador-solicitudes-micro npx prisma db push --accept-data-loss
```

### Problema: Notificaciones no se envían
**Síntoma:** Los logs del worker no muestran envíos
**Solución:**
```powershell
# Verificar conexión a RabbitMQ
docker logs notifications-worker --tail 10

# Reiniciar worker si es necesario
docker-compose -f docker-compose.unified.yml restart notifications-worker
```

### Problema: Error de parsing en API de notificaciones
**Síntoma:** Error 400/422 en endpoints de notificaciones
**Solución:**
```powershell
# Reiniciar servicio de notificaciones
docker-compose -f docker-compose.unified.yml restart notifications-api

# Esperar 5 segundos y probar nuevamente
Start-Sleep -Seconds 5

# NOTA: El endpoint /notify puede tener problemas de parsing.
# Usar /notify-multi que es más estable y funcional.
```

### Problema: Error 400 en endpoint /notify
**Síntoma:** `{"detail":"There was an error parsing the body"}`
**Solución:**
```powershell
# Verificar que el payload tenga el esquema correcto para /notify:
$emailBody = @{
    channel = "email"
    destination = "miraortega2020@gmail.com"
    message = "Test de notificación"
    subject = "Test"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8080/notify" -Method POST -Body $emailBody -ContentType "application/json" -UseBasicParsing

# O usar /notify-multi para notificaciones más complejas:
$multiEmailBody = @{
    destination = @{ email = "miraortega2020@gmail.com" }
    message = @{ email = "Test de notificación" }
    subject = "Test"
} | ConvertTo-Json -Depth 3

Invoke-WebRequest -Uri "http://localhost:8080/notify-multi" -Method POST -Body $multiEmailBody -ContentType "application/json" -UseBasicParsing
```

### Problema: SMS no se entrega
**Síntoma:** Error en logs de Twilio
**Solución:**
- Verificar credenciales de Twilio en variables de entorno
- Verificar que el número de teléfono tenga formato internacional (+57...)
- Revisar logs de Twilio para códigos de error específicos

---

## 🧹 Limpieza del Entorno

### Parar Servicios

```powershell
# Parar todos los servicios
docker-compose -f docker-compose.unified.yml down

# Parar y eliminar volúmenes (opcional)
docker-compose -f docker-compose.unified.yml down --volumes --remove-orphans
```

### Limpieza Completa

```powershell
# Eliminar todas las imágenes y contenedores (CUIDADO: elimina todo)
docker system prune -a --volumes -f
```

---

## 📊 Flujo de Datos Esperado

```
1. Usuario → Dominio Service (Spring Boot:8081)
2. Dominio → RabbitMQ (Exchange: dominio.events)
3. RabbitMQ → Orquestador (Node.js:3000)
4. Orquestador → RabbitMQ (Queue: notifications.queue)
5. RabbitMQ → Worker (Python)
6. Worker → SMTP/Twilio → Usuario Final
```

## ✅ Checklist de Verificación

- [ ] Todos los servicios están "Up" y "healthy"
- [ ] Health checks responden correctamente
- [ ] Registro de usuario devuelve 201
- [ ] Login devuelve 200 con token
- [ ] Solicitud de código devuelve 200
- [ ] Notificaciones directas funcionan (/notify y /notify-multi)
- [ ] Logs del orquestador muestran procesamiento de eventos
- [ ] Logs del worker muestran envío de notificaciones
- [ ] Email llega a miraortega2020@gmail.com
- [ ] SMS llega a +573225035863
- [ ] Base de datos contiene registros de eventos
- [ ] Consultas SQL funcionan correctamente

---

## 🔍 Hallazgos de Pruebas Recientes

### ✅ **Funcionamiento Verificado (Última Prueba: 24/09/2025)**

**Endpoints que funcionan correctamente:**
- ✅ `/health` - Notificaciones y Orquestador
- ✅ `/v1/usuarios` - Registro de usuarios
- ✅ `/v1/sesiones` - Login de usuarios  
- ✅ `/v1/codigos` - Solicitud de cambio de contraseña
- ✅ `/v1/notifications` - Notificaciones directas (email, sms, whatsapp, push)
- ✅ `/v1/notifications/multi` - Notificaciones multi-canal (para casos complejos)

**Diferencias entre endpoints:**
- **`/v1/notifications`**: Esquema simple, ideal para notificaciones directas
- **`/v1/notifications/multi`**: Esquema complejo, ideal para notificaciones múltiples o personalizadas

**Flujo de datos verificado:**
1. **Registro** → Genera evento `REGISTRO_USUARIO` → Email de confirmación
2. **Login** → Genera evento `AUTENTICACION` → Email + SMS de notificación
3. **Cambio de contraseña** → Genera evento `RECUPERAR_PASSWORD` → Email con código

**Datos de prueba confirmados:**
- **Email:** `miraortega2020@gmail.com` ✅
- **SMS:** `+573225035863` ✅ (SID confirmado: SM3d84e7acfdc9444cc1e4ffd9bbfbdf60)

**Comandos SQL verificados:**
```powershell
# Eventos en orquestador
echo 'SELECT id, "tipoAccion", usuario, correo FROM "Evento" ORDER BY timestamp DESC LIMIT 5;' | docker exec -i postgres-orchestrator psql -U user -d mydb

# Notificaciones
echo "SELECT id, channel, destination, status, created_at FROM notifications ORDER BY created_at DESC LIMIT 5;" | docker exec -i postgres-notifications psql -U notifications -d notifications
```

---

## 📞 Contacto y Soporte

Si encuentras problemas durante las pruebas:

1. **Revisa los logs** de cada servicio
2. **Verifica la conectividad** entre servicios
3. **Confirma las credenciales** de servicios externos (Twilio, SMTP)
4. **Revisa el estado** de RabbitMQ en la interfaz web

**¡El sistema está diseñado para ser robusto y confiable!** 🚀