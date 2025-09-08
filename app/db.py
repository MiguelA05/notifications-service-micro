import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DEFAULT_DB_URL = "postgresql+psycopg://notifications:notifications@localhost:5432/notifications"
DB_URL = os.getenv("DB_URL", DEFAULT_DB_URL)

# If a JDBC URL sneaks in (from previous Spring config), ignore it and use a sane default
if DB_URL.startswith("jdbc:"):
    DB_URL = DEFAULT_DB_URL

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


