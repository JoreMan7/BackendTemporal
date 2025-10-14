"""
Módulo de utilidades de autenticación y autorización
----------------------------------------------------
Proporciona funciones reutilizables para validar roles y permisos
de usuarios autenticados mediante JWT.
"""

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity
from functools import wraps
from database.db_mysql import execute_query

# ================================================================
# VALIDACIÓN DE ROLES
# ================================================================
def tiene_rol_permitido(roles_permitidos):
    """
    Verifica si el usuario actual tiene alguno de los roles permitidos.

    Args:
        roles_permitidos (list[str]): Lista de roles válidos (por ejemplo: ['admin', 'líder']).

    Returns:
        bool: True si el usuario tiene alguno de los roles permitidos, False en caso contrario.
    """
    claims = get_jwt()
    rol = claims.get('rol') or claims.get('role') or claims.get('tipo_usuario')
    rol = (rol or '').lower()
    return rol in [r.lower() for r in roles_permitidos]


# ================================================================
# VALIDACIÓN DE PERMISOS ESPECÍFICOS (para el futuro)
# ================================================================
def tiene_permiso(nombre_permiso):
    """
    Verifica si el usuario actual tiene un permiso específico asignado,
    ya sea por tipo de usuario (rol) o directamente.

    Args:
        nombre_permiso (str): Nombre interno del permiso (ej: 'eliminar_habitante').

    Returns:
        bool: True si el usuario tiene el permiso, False si no.
    """
    user_id = get_jwt_identity()

    # 1️⃣ Buscar permiso directo del usuario (si existe la tabla usuario_permisos)
    query_user_perm = """
        SELECT 1
        FROM usuario_permisos up
        JOIN permisos p ON p.id_permiso = up.id_permiso
        WHERE up.id_usuario = %s AND p.nombre = %s
    """
    direct = execute_query(query_user_perm, (user_id, nombre_permiso), fetch_one=True)
    if direct:
        return True

    # 2️⃣ Si no tiene permiso directo, buscarlo según su tipo de usuario
    query_tipo_perm = """
        SELECT 1
        FROM usuario u
        JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
        JOIN tipo_usuario_permisos tup ON tu.IdTipoUsuario = tup.IdTipoUsuario
        JOIN permisos p ON p.id_permiso = tup.id_permiso
        WHERE u.IdUsuario = %s AND p.nombre = %s
    """
    by_type = execute_query(query_tipo_perm, (user_id, nombre_permiso), fetch_one=True)
    return bool(by_type)


# ================================================================
# DECORADOR require_rol
# ================================================================
def require_rol(*roles):
    """
    Decorador para exigir ciertos roles antes de ejecutar una vista.
    Ejemplo:
        @require_rol('admin', 'líder')
        def crear_tarea():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not tiene_rol_permitido(list(roles)):
                return jsonify({
                    'success': False,
                    'message': 'No tiene permisos para acceder a esta función'
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
