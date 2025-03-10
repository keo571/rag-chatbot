import sqlite3
from contextlib import contextmanager
from .settings import DB_PATH

def init_db():
    """Initialize the SQLite database with required tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT,
            source_type TEXT,
            source_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        yield conn
    finally:
        conn.close()

def dict_factory(cursor, row):
    """Convert database rows to dictionaries."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

def get_dict_cursor(conn):
    """Get a cursor that returns dictionaries."""
    conn.row_factory = dict_factory
    return conn.cursor() 