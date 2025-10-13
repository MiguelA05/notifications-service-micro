#!/bin/bash

# Script para inicializar volúmenes de RabbitMQ con Podman Compose
echo "Inicializando volúmenes de RabbitMQ..."

# Crear volúmenes si no existen
podman volume create rabbitmq_config 2>/dev/null || true
podman volume create rabbitmq_definitions 2>/dev/null || true

# Crear contenedores temporales para copiar archivos
echo "Copiando archivos de configuración..."

# Copiar rabbitmq.conf
podman run --rm -v rabbitmq_config:/data -v "$(pwd)":/host alpine sh -c "cp /host/rabbitmq.conf /data/rabbitmq.conf && chmod 644 /data/rabbitmq.conf"

# Copiar definitions.json
podman run --rm -v rabbitmq_definitions:/data -v "$(pwd)":/host alpine sh -c "cp /host/definitions.json /data/definitions.json && chmod 644 /data/definitions.json"

echo "Volúmenes inicializados correctamente."
echo "Ahora puedes ejecutar: podman-compose -f docker-compose.unified.yml up -d"
