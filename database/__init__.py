"""
Inicialización del módulo de base de datos
"""
from .db_mysql import init_db, get_db_connection, close_db_connection

__all__ = ['init_db', 'get_db_connection', 'close_db_connection']
