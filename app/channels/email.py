
from typing import Any, Optional, Dict
from .base import Channel
import logging
import re
import json

class EmailChannel(Channel):
    name = "email"

    def __init__(self, config: dict = None):
        """
        Inicializa el canal de email con configuracion SMTP

        Args:
            config: Diccionario con la configuracion del canal
                - smtp_host: Host de SMTP
                - smtp_port: Puerto de SMTP
                - smtp_user: Usuario de SMTP
                - smtp_password: Password de SMTP
                - from_email: Email de remitente
                - from_name: Nombre de remitente
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        
        #Configuraciones por defecto
        self.from_email = self.config.get("from_email", "noreply@tudominio.com")
        self.from_name = self.config.get("from_name", "Notifications Service")

        #Validar configuracion requerida
        if not self.config.get("smtp_host"):
            self.logger.warning("SMTP esta configurado, pero sin host")

    
    def validate_destination(self, destination: str) -> None:
        """
        Valida que el email de destino tenga el formato correcto
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, destination):
            raise ValueError(f"Email invalido: {destination}")

    async def send(self, destination: str, message: str, subject: Optional[str] = None) -> None:
        """Envia el email a la direccion de destino usando SMTP"""
        self.validate_destination(destination)
        await self.send_with_smtp(destination, message, subject)
    
    
    async def send_with_smtp(self, destination: str, message: str, subject: str = None) -> None:
        """Envia el email a la direccion de destino usando SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
        
            #Confiracion SMTP
            smtp_host = self.config.get("smtp_host", "smtp.gmail.com")
            smtp_port = self.config.get("smtp_port", 587)
            smtp_user = self.config.get("smtp_user")
            smtp_password = self.config.get("smtp_password")

            #Crear mensaje
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = destination
            msg["Subject"] = subject or "Notificacion"

            #Agregar contenido
            msg.attach(MIMEText(message, "html"))

            #Enviar
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            self.logger.info(f"Email enviado a {destination} con asunto {subject} via SMTP")

        except Exception as e:
            self.logger.error(f"Error al enviar email via SMTP: {str(e)}")
            raise

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Renderiza una plantilla HTML con el contexto proporcionado"""
        try:
            from jinja2 import Environment, FileSystemLoader

            #Directorio de plantillas
            env = Environment(loader=FileSystemLoader(self.template_dir))

            #Cargar y renderizar la plantilla
            template = env.get_template(f"{template_name}.html")
            return template.render(**context)

        except Exception as e:
            self.logger.error(f"Error al renderizar plantilla {template_name}: {str(e)}")
            #Fallback a mensaje simple
            return context.get("message", "")

    async def send_template(self, destination: str, template_name: str, context: Dict[str, Any], subject: str = None) -> None:
        """Envia un email con una plantilla HTML y un contexto proporcionado"""

        #Renderizar la plantilla
        html_content = self._render_template(template_name, context)

        #Envia usando el metodo normal
        await self.send(destination, html_content, subject)

