from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.config import settings

# Determine if we are using SQLite
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Add connection arguments specific to SQLite if needed
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for models
Base = declarative_base()

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
