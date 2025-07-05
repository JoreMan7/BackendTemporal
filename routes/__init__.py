"""
Inicialización del módulo de rutas
Registra todos los blueprints de la aplicación
"""
from .AuthRoutes import auth_bp
from .indexRoutes import index_bp

def register_blueprints(app):
    """
    Registra todos los blueprints en la aplicación
    
    Args:
        app (Flask): Instancia de la aplicación Flask
    """
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(index_bp, url_prefix='/api')
