"""
Configuración y manejo de conexiones a MySQL
Utiliza PyMySQL para la conexión a la base de datos
"""
import pymysql
from flask import current_app, g
import logging

def init_db(app):
    """
    Inicializa la configuración de la base de datos
    
    Args:
        app (Flask): Instancia de la aplicación Flask
    """
    app.teardown_appcontext(close_db_connection)

def get_db_connection():
    """
    Obtiene una conexión a la base de datos MySQL
    Utiliza el contexto de aplicación de Flask para reutilizar conexiones
    
    Returns:
        pymysql.Connection: Conexión a la base de datos
    """
    if 'db_connection' not in g:
        try:
            g.db_connection = pymysql.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                password=current_app.config['MYSQL_PASSWORD'],
                database=current_app.config['MYSQL_DB'],
                port=current_app.config['MYSQL_PORT'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            logging.info("Conexión a base de datos establecida exitosamente")
        except Exception as e:
            logging.error(f"Error al conectar con la base de datos: {str(e)}")
            raise
    
    return g.db_connection

def close_db_connection(error):
    """
    Cierra la conexión a la base de datos
    
    Args:
        error: Error si existe
    """
    db_connection = g.pop('db_connection', None)
    
    if db_connection is not None:
        try:
            db_connection.close()
            logging.info("Conexión a base de datos cerrada")
        except Exception as e:
            logging.error(f"Error al cerrar conexión: {str(e)}")

def execute_query(query, params=None, fetch_one=False, fetch_all=True):
    """
    Ejecuta una consulta SQL de manera segura
    
    Args:
        query (str): Consulta SQL a ejecutar
        params (tuple): Parámetros para la consulta
        fetch_one (bool): Si debe retornar solo un registro
        fetch_all (bool): Si debe retornar todos los registros
        
    Returns:
        dict/list: Resultado de la consulta
    """
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute(query, params or ())
        
        if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
            connection.commit()
            return cursor.rowcount
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        
        return None
        
    except Exception as e:
        connection.rollback()
        logging.error(f"Error ejecutando consulta: {str(e)}")
        raise
    finally:
        cursor.close()
