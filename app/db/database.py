import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import settings

def get_db_connection():
    conn = psycopg2.connect(settings.database_url, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn
