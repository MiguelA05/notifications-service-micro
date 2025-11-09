#!/bin/bash

# Script de inicialización para Jenkins con Podman
echo "Inicializando Jenkins con configuración automática..."

# Crear directorios necesarios
mkdir -p /var/jenkins_home/casc_configs
mkdir -p /var/jenkins_home/init.groovy.d

# Copiar archivos de configuración con permisos correctos
if [ -f "/etc/jenkins-config/jenkins.yaml" ]; then
    cp /etc/jenkins-config/jenkins.yaml /var/jenkins_home/casc_configs/jenkins.yaml
    chown jenkins:jenkins /var/jenkins_home/casc_configs/jenkins.yaml
    chmod 644 /var/jenkins_home/casc_configs/jenkins.yaml
    echo "Configuración jenkins.yaml copiada correctamente"
fi

if [ -d "/etc/jenkins-init" ]; then
    cp -r /etc/jenkins-init/* /var/jenkins_home/init.groovy.d/
    chown -R jenkins:jenkins /var/jenkins_home/init.groovy.d/
    chmod -R 644 /var/jenkins_home/init.groovy.d/*
    echo "Scripts de inicialización copiados correctamente"
fi

# Iniciar Jenkins
echo "Iniciando Jenkins..."
exec /usr/local/bin/jenkins.sh
