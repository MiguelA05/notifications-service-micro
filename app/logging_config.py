import logging, sys, structlog
import asyncio
from app.fluentd_client import init_fluentd_client, log_to_fluentd

def configure_logging(service_name: str, env: str = "dev"):
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    # Inicializar cliente de Fluentd
    try:
        init_fluentd_client(service_name, env)
    except Exception as e:
        logging.warning(f"No se pudo inicializar cliente Fluentd: {e}")

    # Processor personalizado que también envía a Fluentd
    def fluentd_processor(logger, method_name, event_dict):
        # Enviar a Fluentd de forma asíncrona (no bloquea)
        try:
            level = str(event_dict.get("level", "INFO"))
            message = str(event_dict.get("event", event_dict.get("msg", "")))
            # Crear copia sin campos internos de structlog
            fluentd_data = {k: v for k, v in event_dict.items() 
                          if k not in ["event", "logger", "level"] and 
                             not k.startswith("_")}
            # Enviar de forma asíncrona (sin bloquear)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Crear task sin esperar
                    asyncio.create_task(log_to_fluentd(level, message, **fluentd_data))
            except RuntimeError:
                # Si no hay loop, crear uno nuevo
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(log_to_fluentd(level, message, **fluentd_data))
                    loop.close()
                except Exception:
                    pass  # Ignorar errores de Fluentd
        except Exception:
            pass  # No fallar si Fluentd no está disponible
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,      # soporte contextvars
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            timestamper,
            fluentd_processor,  # Processor personalizado para Fluentd
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Puentea logging stdlib → structlog
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    structlog.bind(service=service_name, env=env)