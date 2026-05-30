import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Default to localhost PostgreSQL if not specified in .env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/kyc_db")

connect_args = {}
# AWS RDS prefers or requires SSL connections for security
if "amazonaws.com" in DATABASE_URL:
    connect_args["sslmode"] = "require"

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency function to inject a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()