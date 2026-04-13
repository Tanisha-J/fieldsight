import os  # Reads environment variables 
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Determines whether necessary environment variables were read or not 
def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


# Read DB connection settings from environment 
DB_HOST = _required("DB_HOST")
DB_PORT = _required("DB_PORT")
DB_USER = _required("DB_USER")
DB_PASSWORD = _required("DB_PASSWORD")
DB_NAME = _required("DB_NAME")

# SQLAlchemy connection URL for MySQL via PyMySQL driver
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Creates the SQLAlchemy engine which manages connection between app and MYSQL
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Creates DB sessions assigned to this specific engine 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy ORM models
Base = declarative_base()

# Assigns 1 DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db    # hands db to endpoint   
    finally:
        db.close()  # closes even if error 