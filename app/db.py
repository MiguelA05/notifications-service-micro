import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Importar los modelos que cree
from .models import Base, Notification, NotificationChannel, NotificationChannelConfig, NotificationMetrics, User

#Configuracion de la conexion a la base de datos
DEFAULT_DB_URL = "postgresql+psycopg2://notifications:notifications@127.0.0.1:5432/notifications" #URL de la base de datos
DB_URL = os.getenv("DB_URL", DEFAULT_DB_URL) #Usamos la variable de entorno DB_URL, si no existe, usamos la URL por defecto

# Si una URL JDBC ingresa, ignoramos y usamos la URL por defecto
if DB_URL.startswith("jdbc:"):
    DB_URL = DEFAULT_DB_URL

#Motor de la base de datos
engine = create_engine(
    DB_URL, 
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=0,
    echo=False
) #Es el "motor" que maneja la conexion a la base de datos, pool_pre_ping verifica si la conexion esta activa antes de usarla
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) #Es el "fabricante" de sesiones para interactuar con la base de datos


def create_tables():
    """
    Crea todas las tablas de la base de datos usando únicamente SQLAlchemy.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas correctamente con SQLAlchemy")


def get_db():
    """
    Obtiene una sesion de la base de datos
    Se usa en todos los endpoints de FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_default_channels():
    """
    Inicializa los canales de notificacion por defecto
    Esta funcion se ejecuta cuando se inicia la aplicacion por primera vez
    """
    db = SessionLocal()
    try:
        #Verificar si ya existen canales
        existing_channels = db.query(NotificationChannelConfig).count()

        if existing_channels == 0:
            #Crear los canales por defecto
            default_channels = [
                NotificationChannelConfig(
                    name=NotificationChannel.EMAIL, 
                    enabled=True, 
                    config=json.dumps({
                        'provider': 'smtp',
                        'smtp_host': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'smtp_user': os.getenv('SMTP_USER'),
                        'smtp_password': os.getenv('SMTP_PASSWORD'),
                        'from_email': os.getenv('FROM_EMAIL', 'noreply@example.com'),
                        'from_name': os.getenv('FROM_NAME', 'Notification Service'),
                        'template_dir': 'app/templates'
                    })),
                NotificationChannelConfig(
                    name=NotificationChannel.SMS,
                    enabled=True,
                    config=json.dumps({
                        'provider': 'twilio',
                        'account_sid': os.getenv('TWILIO_ACCOUNT_SID'),
                        'auth_token': os.getenv('TWILIO_AUTH_TOKEN'),
                        'from_number': os.getenv('TWILIO_FROM_NUMBER')
                    })
                ),
                NotificationChannelConfig(
                    name=NotificationChannel.WHATSAPP,
                    enabled=True,
                    config=json.dumps({
                        "provider": "twilio",
                        "account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
                        "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
                        "from_number": os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+3225035863"),
                        "webhook_url": os.getenv("WHATSAPP_WEBHOOK_URL", "")
                    })
                ),
                NotificationChannelConfig(
                    name=NotificationChannel.PUSH,
                    enabled=True,
                    config=json.dumps({
                        "provider": "firebase",
                        "firebase_project_id": os.getenv("FIREBASE_PROJECT_ID", ""),
                        "firebase_service_account_key": os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", ""),
                        "web_vapid_public_key": os.getenv("WEB_VAPID_PUBLIC_KEY", ""),
                        "web_vapid_private_key": os.getenv("WEB_VAPID_PRIVATE_KEY", "")
                    })
                )
            ]
            
            for channel in default_channels:
                db.add(channel)

            db.commit()
            print("Canales de notificacion por defecto creados correctamente")
        else:
            print("Canales de notificacion por defecto ya existen")
    except Exception as e:
        print(f"Error al inicializar los canales de notificacion por defecto: {e}")
        db.rollback()
    finally:
        db.close()

def init_default_user():
    """Crea un usuario por defecto para pruebas"""
    db = SessionLocal()
    try:
        # Verificar si ya existe un usuario
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print("Usuario admin ya existe")
            return
        
        # Crear usuario admin por defecto
        from .auth import get_password_hash
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print("Usuario admin creado correctamente (username: admin, password: admin123)")
        
    except Exception as e:
        print(f"Error al crear usuario por defecto: {e}")
        db.rollback()
    finally:
        db.close()