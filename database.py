from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Use environment variables to configure the database URL
# SQLALCHEMY_DATABASE_URL = (
#     # f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
#     # f"@{os.getenv('DB_HOST_NAME', 'db')}:{os.getenv('DB_PORT', 5432)}/{os.getenv('POSTGRES_DB')}"
# )
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:root@localhost/video_transcript"
# Create the SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models
Base = declarative_base()

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)