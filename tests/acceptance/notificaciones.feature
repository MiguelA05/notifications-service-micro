# language: es
# =============================================================================
# ARCHIVO DE CARACTERÍSTICAS (FEATURES) - SERVICIO DE NOTIFICACIONES
# =============================================================================

Característica: Envío de Notificaciones Multi-Canal
  
  Antecedentes:
    Dado que el servicio de notificaciones está disponible

  # ===== ENVÍO DE EMAIL =====
  Escenario: Enviar notificación por email
    Cuando envío una notificación por email con datos válidos
    Entonces la respuesta debe tener estado 200
    Y el cuerpo debe indicar que la notificación fue encolada

  # ===== ENVÍO DE SMS =====
  Escenario: Enviar notificación por SMS
    Cuando envío una notificación por SMS con datos válidos
    Entonces la respuesta debe tener estado 200
    Y el cuerpo debe indicar que la notificación fue encolada

  # ===== ENVÍO MULTI-CANAL =====
  Escenario: Enviar notificación multi-canal
    Cuando envío una notificación multi-canal con datos válidos
    Entonces la respuesta debe tener estado 200
    Y el cuerpo debe indicar que la notificación fue encolada

  # ===== HEALTH CHECK =====
  Escenario: Verificar salud del servicio de notificaciones
    Cuando consulto el endpoint de health check
    Entonces la respuesta debe tener estado 200
    Y el cuerpo debe indicar que el servicio está UP

  Escenario: Verificar liveness del servicio
    Cuando consulto el endpoint de liveness
    Entonces la respuesta debe tener estado 200
    Y el cuerpo debe indicar que el servicio está vivo

