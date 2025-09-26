# src/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from flask import g
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- CHANGE HIGHLIGHT: Updated to modern SQLAlchemy 2.0 syntax ---
# The import for declarative_base has been changed, and the function is called directly.
Base = declarative_base()
# --- END CHANGE ---

def get_db():
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db

def close_db(e=None):
    try:
        db = g.pop('db', None)
        if db is not None:
            db.close()
    except RuntimeError:
        # Handle case where we're outside of application context
        # This can happen during test teardown
        pass

