#!/bin/bash

echo "🔍 Verificando configuraciones de Jenkins y SonarQube..."

# Verificar que Jenkins esté funcionando
echo "📋 Verificando Jenkins..."
JENKINS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8083)
if [ "$JENKINS_STATUS" = "200" ]; then
    echo "✅ Jenkins está funcionando (puerto 8083)"
else
    echo "❌ Jenkins no está accesible"
    exit 1
fi

# Verificar que SonarQube esté funcionando
echo "📋 Verificando SonarQube..."
SONAR_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9001)
if [ "$SONAR_STATUS" = "200" ]; then
    echo "✅ SonarQube está funcionando (puerto 9001)"
else
    echo "⚠️  SonarQube está deshabilitado temporalmente (se agregará después)"
fi

# Verificar que el servicio de dominio esté funcionando
echo "📋 Verificando servicio de dominio..."
DOMAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/actuator/health)
if [ "$DOMAIN_STATUS" = "200" ]; then
    echo "✅ Servicio de dominio está funcionando (puerto 8081)"
else
    echo "⚠️  Servicio de dominio no está accesible (esto es normal si no se ha iniciado)"
fi

echo ""
echo "🎯 Configuraciones verificadas:"
echo "   • Jenkins: http://localhost:8083"
echo "   • SonarQube: http://localhost:9001"
echo "   • Servicio de dominio: http://localhost:8081"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Acceder a Jenkins y verificar que el job 'jwtmanual-pipeline' esté creado"
echo "   2. Ejecutar el pipeline para probar la integración completa"
echo "   3. Verificar reportes de pruebas y calidad de código"
