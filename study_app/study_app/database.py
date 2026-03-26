import psycopg2
import psycopg2.extras
from functools import lru_cache
from .config import get_settings


def get_db():
    settings = get_settings()
    conn = psycopg2.connect(settings.database_connection_uri)
    conn.autocommit = True
    return conn
