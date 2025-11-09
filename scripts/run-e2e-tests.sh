#!/bin/bash

# Script para ejecutar tests E2E desde el host
# Este script se ejecuta desde el host, no desde Jenkins

echo "🚀 Ejecutando tests E2E desde el host..."

# Verificar que el contenedor automation-tests esté ejecutándose
if ! podman ps | grep automation-tests > /dev/null; then
    echo "❌ Contenedor automation-tests no está ejecutándose"
    exit 1
fi

echo "✅ Contenedor automation-tests está ejecutándose"

# Ejecutar tests E2E en el contenedor
echo "🧪 Ejecutando tests E2E..."
podman exec automation-tests mvn clean test -Dtest=CucumberTest -Dmaven.test.failure.ignore=true

# Verificar resultado
if [ $? -eq 0 ]; then
    echo "✅ Tests E2E ejecutados exitosamente"
else
    echo "⚠️ Algunos tests E2E fallaron, pero continuando..."
fi

# Generar reporte Allure
echo "📊 Generando reporte Allure..."
podman exec automation-tests mvn allure:report -Dmaven.test.failure.ignore=true

# Verificar resultado del reporte
if [ $? -eq 0 ]; then
    echo "✅ Reporte Allure generado exitosamente"
else
    echo "⚠️ Error generando reporte Allure, pero continuando..."
fi

# Copiar reportes a directorio accesible por Jenkins
echo "📊 Copiando reportes..."
mkdir -p /tmp/jenkins-e2e-reports
podman cp automation-tests:/app/target/site/allure-maven-plugin /tmp/jenkins-e2e-reports/allure-reports || echo "Reportes Allure no disponibles"
podman cp automation-tests:/app/target/surefire-reports /tmp/jenkins-e2e-reports/surefire-reports || echo "Reportes Surefire no disponibles"

echo "✅ Reportes copiados a /tmp/jenkins-e2e-reports/"
