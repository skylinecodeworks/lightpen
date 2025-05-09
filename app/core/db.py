# app/core/db.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Carga de la URL completa desde la variable de entorno
# Asegúrate de tener en tu .env:
# DATABASE_URL=postgresql://usuario:password@host:puerto/base_de_datos
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida")

# Configuramos SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency de FastAPI para obtener una sesión de DB y luego cerrarla."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Crea las tablas si no existen (útil en development)."""
    from app.models import Invoice, Receipt  # importa directamente tus modelos
    Base.metadata.create_all(bind=engine)
