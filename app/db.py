import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


DB_URL = os.getenv("DB_URL", "jdbc:h2:mem:notificationsdb")

# Expect a standard Postgres URL. If JDBC is provided by mistake, fall back to a sensible default
if DB_URL.startswith("jdbc:"):
    DB_URL = os.getenv("DB_URL", "postgresql+psycopg://notifications:notifications@localhost:5432/notifications")

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


