import os, threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.env import get_env_variable

DATABASE_URL = get_env_variable("SUPABASE_DB_URL") 
engine = create_engine(DATABASE_URL, future=True)  
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

_initialized = False
_lock = threading.Lock()

def init_db() -> None:
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        with engine.begin() as conn:
            conn.execute(text('create extension if not exists "pgcrypto";'))
        Base.metadata.create_all(bind=engine) 
        _initialized = True

from contextlib import contextmanager
@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()