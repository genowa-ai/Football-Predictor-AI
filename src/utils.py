import pandas as pd
from sqlalchemy import create_engine
# Changed from '.config' to 'config' to avoid import errors
from src.config import DB_HOST, DB_NAME, DB_USER, DB_PASS

def get_db_engine():
    """Returns a SQLAlchemy engine for Pandas integration"""
    url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    return create_engine(url)