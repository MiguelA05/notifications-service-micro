import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Importar los modelos que cree
from .models import Base, Notification, NotificationChannel, NotificationChannelConfig, NotificationMetrics

#Configuracion de la conexion a la base de datos
DEFAULT_DB_URL = "postgresql+psycopg://notifications:notifications@localhost:5432/notifications" #URL de la base de datos
DB_URL = os.getenv("DB_URL", DEFAULT_DB_URL) #Usamos la variable de entorno DB_URL, si no existe, usamos la URL por defecto

# Si una URL JDBC ingresa, ignoramos y usamos la URL por defecto
if DB_URL.startswith("jdbc:"):
    DB_URL = DEFAULT_DB_URL

#Motor de la base de datos
engine = create_engine(DB_URL, pool_pre_ping=True) #Es el "motor" que maneja la conexion a la base de datos, pool_pre_ping verifica si la conexion esta activa antes de usarla
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) #Es el "fabricante" de sesiones para interactuar con la base de datos


def create_tables():
    """
    Crea todas las tablas de la base de datos
    Esta funcion se ejecuta cuando se inicia la aplicacion
    """
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente")

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
        #Verificar si ya existen cnales
        existing_channels = db.query(NotificationChannelConfig).count()

        if existing_channels == 0:
            #Crear los canales por defecto
            default_channels = [
                NotificationChannelConfig(
                    name=NotificationChannel.EMAIL, 
                    enabled=True, 
                    config='{"provider": "sendgrid", "template_engine": "jinja2"}'),
                NotificationChannelConfig(
                    name=NotificationChannel.SMS,
                    enabled=True,
                    config='{"provider": "twilio", "country_code": "+1"}'
                ),
                NotificationChannelConfig(
                    name=NotificationChannel.WHATSAPP,
                    enabled=True,
                    config='{"provider": "twilio", "business_number": "+1234567890"}'
                ),
                NotificationChannelConfig(
                    name=NotificationChannel.PUSH,
                    enabled=True,
                    config='{"provider": "firebase", "project_id": "your-project"}' #TODO: Cambiar por el proyecto de Firebase
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