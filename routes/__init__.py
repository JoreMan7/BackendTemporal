"""
Inicialización del módulo de rutas
Registra todos los blueprints de la aplicación
"""

from .AuthRoutes import auth_bp
from .indexRoutes import index_bp
from .habitantes import habitantes_bp
from .sacramentos import sacramentos_bp
from .opciones import opciones_bp
from .gruposAyudantes import grupos_bp
from .usuarios import usuarios_bp
from .tareas import tareas_bp
from .cursos import cursos_bp
from .grupofamiliar import grupofamiliar_bp

def register_blueprints(app):
    """
    Registra todos los blueprints en la aplicación
    
    Args:
        app (Flask): Instancia de la aplicación Flask
    """
    # Autenticación
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # Rutas de índice/general
    app.register_blueprint(index_bp, url_prefix='/api')
    
    # Habitantes
    app.register_blueprint(habitantes_bp, url_prefix='/api/habitantes')
    
    # Sacramentos
    app.register_blueprint(sacramentos_bp, url_prefix="/api/sacramentos")
    
    # Opciones
    app.register_blueprint(opciones_bp, url_prefix="/api/opciones")

    # Grupos y Ayudantes
    app.register_blueprint(grupos_bp, url_prefix='/api/grupos')

    # Usuarios
    app.register_blueprint(usuarios_bp, url_prefix="/api/usuarios")

    # Tareas
    app.register_blueprint(tareas_bp, url_prefix='/api/tareas')

    # Cursos
    app.register_blueprint(cursos_bp, url_prefix='/api/cursos')

    # Grupos Familiares
    app.register_blueprint(grupofamiliar_bp, url_prefix='/api/grupofamiliar')   