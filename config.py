"""
Configuración principal de la aplicación Flask
Maneja diferentes entornos: desarrollo, producción, testing
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()


class Config:
    """Configuración base de la aplicación"""
    
    # Configuración básica de Flask
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Configuración de la base de datos MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST')
    MYSQL_USER = os.environ.get('MYSQL_USER')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
    MYSQL_DB = os.environ.get('MYSQL_DB')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
    
    # Configuración de JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'fallback-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_ACCESS_TOKEN_SECONDS", 3600))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_REFRESH_TOKEN_SECONDS", 604800))
    )

    # SISTEMA DE BLOQUEO PROGRESIVO CONFIGURABLE
    MAX_LOGIN_ATTEMPTS = int(os.environ.get("MAX_LOGIN_ATTEMPTS", 3))
    BASE_LOCK_DURATION_MINUTES = int(os.environ.get("BASE_LOCK_DURATION_MINUTES", 
    int(os.environ.get("LOGIN_LOCK_DURATION_SECONDS", 3600)) // 60  # Convierte segundos a minutos
))
    LOCK_MULTIPLIER = float(os.environ.get("LOCK_MULTIPLIER", 1.5))  # 1.5 = 50% más cada vez
    MAX_LOCK_DURATION_MINUTES = int(os.environ.get("MAX_LOCK_DURATION_MINUTES", 480))  # 8 horas máximo

    # ⚠️ MANTENER para compatibilidad (opcional, puedes eliminarla si quieres)
    LOGIN_LOCK_DURATION_SECONDS = BASE_LOCK_DURATION_MINUTES * 60

    # Configuración de CORS
    CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5500",   # Live Server
    "http://localhost:5500",   # Otra variante de Live Server
    "http://127.0.0.1:5501",   # Live Server 2
    "http://localhost:5501",   # Otra variante de Live Server 2
    "http://localhost:80"   
]
    
    # Configuración de archivos
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Configuración para testing"""
    DEBUG = True
    TESTING = True
    MYSQL_DB = 'test_gestion_eclesial'

# Diccionario de configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
