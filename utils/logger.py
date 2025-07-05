"""
Configuración del sistema de logging
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(app):
    """
    Configura el sistema de logging para la aplicación
    
    Args:
        app (Flask): Instancia de la aplicación Flask
    """
    
    # Crear directorio de logs si no existe
    log_dir = 'utils/log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configurar formato de logs
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s : %(message)s'
    )
    
    # Handler para archivo de logs
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if app.config['DEBUG'] else logging.INFO)
    
    # Configurar logger de la aplicación
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)
    
    # Log inicial
    app.logger.info('=== Sistema de Gestión Eclesial Iniciado ===')
    app.logger.info('Sistema de logging configurado correctamente')
    
    # Crear archivo de log inicial si no existe
    try:
        with open(log_file, 'a') as f:
            f.write(f'{datetime.now()} - Sistema iniciado\n')
    except Exception as e:
        print(f"Error creando archivo de log: {e}")

