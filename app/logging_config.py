import logging, sys, structlog

def configure_logging(service_name: str, env: str = "dev"):
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,      # soporte contextvars
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            timestamper,
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