#!/bin/bash

# Script para probar el pipeline de Jenkins
# Uso: test-pipeline.sh

echo "🚀 Probando pipeline de Jenkins..."

# Verificar que todos los servicios estén ejecutándose
echo "📋 Verificando servicios..."
podman ps | grep -E "(jenkins|jwtmanual-taller1-micro|automation-tests|postgres-domain)" || {
    echo "❌ Algunos servicios no están ejecutándose"
    exit 1
}

# Verificar conectividad a Jenkins
echo "🔗 Verificando conectividad a Jenkins..."
if curl -s http://localhost:8083/ > /dev/null; then
    echo "✅ Jenkins está disponible en http://localhost:8083"
else
    echo "❌ Jenkins no está disponible"
    exit 1
fi

# Verificar conectividad al microservicio
echo "🔗 Verificando conectividad al microservicio..."
if curl -s http://localhost:8081/ > /dev/null; then
    echo "✅ Microservicio está disponible en http://localhost:8081"
else
    echo "❌ Microservicio no está disponible"
    exit 1
fi

# Verificar que el contenedor automation-tests esté ejecutándose
echo "🔗 Verificando contenedor automation-tests..."
if podman ps | grep automation-tests > /dev/null; then
    echo "✅ Contenedor automation-tests está ejecutándose"
else
    echo "❌ Contenedor automation-tests no está ejecutándose"
    exit 1
fi

echo ""
echo "🎯 Todos los servicios están funcionando correctamente!"
echo ""
echo "📝 Para probar el pipeline:"
echo "1. Abre http://localhost:8083 en tu navegador"
echo "2. Ve al job 'jwtmanual-pipeline'"
echo "3. Haz clic en 'Build with Parameters'"
echo "4. Ejecuta el pipeline"
echo ""
echo "🔍 Para monitorear los logs:"
echo "podman logs jenkins -f"
echo ""
echo "🔍 Para ver logs del contenedor automation-tests:"
echo "podman logs automation-tests -f"
