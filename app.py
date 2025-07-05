"""
Archivo principal de la aplicación Flask
Punto de entrada del backend de Gestión Eclesial
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
from database import init_db
from routes import register_blueprints
from utils.logger import setup_logger

def create_app(config_name=None):
    """
    Factory function para crear la aplicación Flask
    
    Args:
        config_name (str): Nombre de la configuración a usar
        
    Returns:
        Flask: Instancia de la aplicación configurada
    """
    
    # Crear instancia de Flask
    app = Flask(__name__)
    
    # Determinar configuración
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    
    # Configurar CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Configurar JWT
    jwt = JWTManager(app)
    
    # Configurar logging
    setup_logger(app)
    
    # Inicializar base de datos
    init_db(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Crear directorio de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Manejador de errores JWT
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'message': 'Token ha expirado', 'error': 'token_expired'}, 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'message': 'Token inválido', 'error': 'invalid_token'}, 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'message': 'Token de autorización requerido', 'error': 'authorization_required'}, 401

    # Ruta raíz básica
    @app.route('/')
    def home():
        return jsonify({
            'message': 'Backend de Gestión Eclesial',
            'status': 'running',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'api': '/api/',
                'auth': '/api/auth/login',
                'register': '/api/auth/register'
            }
        })

    # Ruta de salud básica
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'message': 'Servidor funcionando correctamente'
        })
    
    return app

# Crear aplicación
app = create_app()

if __name__ == '__main__':
    # Ejecutar aplicación en modo desarrollo
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config['DEBUG']
    )
