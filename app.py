"""
Archivo principal de la aplicación Flask
Punto de entrada del backend de Gestión Eclesial
"""

import os
from dotenv import load_dotenv

# Forzar carga del archivo .env desde el mismo directorio
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
from database import init_db
from routes import register_blueprints
from utils.logger import setup_logger
from datetime import timedelta


def create_app(config_name=None):
    """
    Factory function para crear la aplicación Flask
    """
    app = Flask(__name__)

    # Determinar configuración
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    # Cargar configuración desde config.py
    app.config.from_object(config[config_name])

    # ===============================
    # 🌍 Configuración de CORS
    # ===============================
    CORS(
    app,
    resources={r"/api/*": {"origins": "*"}}, 
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],  
    expose_headers=[], 
    supports_credentials=False 
)

    # ===============================
    # 🔐 Configuración de JWT
    # ===============================
    jwt = JWTManager(app)
    # Tiempos de expiración (ya están también en config.py; mantener aquí no rompe)
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)
    app.config["JWT_ALGORITHM"] = "HS256"
    # Indicar claramente dónde está el token
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]   # leer desde header
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"
    # Margen por diferencias de reloj
    app.config["JWT_DECODE_LEEWAY"] = 60
    # === Manejo de errores de JWT ===
    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return {"msg": "token_expired", "error": "Token expirado"}, 401
    @jwt.invalid_token_loader
    def invalid_token(reason):
        return {"msg": "invalid_token", "error": reason}, 401
    @jwt.unauthorized_loader
    def missing_token(reason):
        # Te deja ver fácilmente si el backend "no ve" el Authorization
        return {"msg": "missing_token", "error": reason}, 401
    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):
        return {"msg": "token_revoked"}, 401
    # ===============================
    # 🔧 Inicialización de servicios
    # ===============================
    setup_logger(app)
    init_db(app)
    register_blueprints(app)

    # Crear directorio de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ===============================
    # 📡 Rutas básicas
    # ===============================
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
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config['DEBUG']
    )
