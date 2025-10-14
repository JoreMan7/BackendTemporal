"""
Rutas para gestión de usuarios (autenticación/autorización)
- No modifica campos de 'habitantes': eso va en el módulo de habitantes.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from utils import require_rol
from utils.Security import Security
from database import execute_query

usuarios_bp = Blueprint('usuarios', __name__)

# =========================
# Utilidades internas
# =========================
def _usuario_existe(id_usuario):
    row = execute_query(
        "SELECT IdUsuario FROM usuario WHERE IdUsuario = %s",
        (id_usuario,), fetch_one=True
    )
    return bool(row)

def _habitante_activo(id_habitante):
    row = execute_query(
        "SELECT Activo FROM habitantes WHERE IdHabitante = %s",
        (id_habitante,), fetch_one=True
    )
    return bool(row and row.get('Activo') == 1)

# =========================
# LISTAR / VER
# =========================
@usuarios_bp.route('/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def listar_usuarios():
    try:
        query = """
            SELECT 
                u.IdUsuario,
                u.IdTipoUsuario,
                tu.Perfil AS Rol,
                u.IdHabitante,
                u.Activo,
                u.FechaRegistro,
                h.Nombre,
                h.Apellido,
                h.NumeroDocumento,
                td.Descripcion AS TipoDocumento
            FROM usuario u
            LEFT JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
            LEFT JOIN habitantes h    ON u.IdHabitante = h.IdHabitante
            LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
            ORDER BY u.IdUsuario DESC
            LIMIT 500
        """
        usuarios = execute_query(query)
        return jsonify({'success': True, 'usuarios': usuarios}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error listando usuarios: {str(e)}'}), 500


@usuarios_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def obtener_usuario(id):
    try:
        query = """
            SELECT 
                u.IdUsuario,
                u.IdTipoUsuario,
                tu.Perfil AS Rol,
                u.IdHabitante,
                u.Activo,
                u.FechaRegistro,
                h.Nombre,
                h.Apellido,
                h.NumeroDocumento,
                td.Descripcion AS TipoDocumento
            FROM usuario u
            LEFT JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
            LEFT JOIN habitantes h    ON u.IdHabitante = h.IdHabitante
            LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
            WHERE u.IdUsuario = %s
        """
        user = execute_query(query, (id,), fetch_one=True)
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        return jsonify({'success': True, 'usuario': user}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error obteniendo usuario: {str(e)}'}), 500

# =========================
# CREAR (ENLAZANDO A HABITANTE)
# =========================
@usuarios_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_usuario():
    """
    Crea usuario SOLO si ya existe el habitante.
    - Requiere: id_habitante, id_tipo_usuario, password
    - Hash de contraseña + validación.
    """
    try:
        data = request.get_json() or {}
        id_habitante   = data.get('id_habitante')
        id_tipo_usuario = data.get('id_tipo_usuario')
        password        = data.get('password')

        if not id_habitante or not id_tipo_usuario or not password:
            return jsonify({'success': False, 'message': 'id_habitante, id_tipo_usuario y password son requeridos'}), 400

        # Verificar habitante activo
        if not _habitante_activo(id_habitante):
            return jsonify({'success': False, 'message': 'El habitante no existe o está inactivo'}), 400

        # Validar contraseña
        policy = Security.validate_password(password)
        if not policy['valid']:
            return jsonify({'success': False, 'message': 'Contraseña inválida', 'errors': policy['errors']}), 400

        # Verificar que el habitante no tenga ya usuario activo
        dup = execute_query("""
            SELECT COUNT(*) AS total
            FROM usuario
            WHERE IdHabitante = %s AND Activo = 1
        """, (id_habitante,), fetch_one=True)
        if dup and dup['total'] > 0:
            return jsonify({'success': False, 'message': 'Ese habitante ya tiene un usuario activo'}), 409

        password_hash = Security.generate_password_hash(password)

        user_id = execute_query("""
            INSERT INTO usuario (IdTipoUsuario, Contraseña, IdHabitante, Activo)
            VALUES (%s, %s, %s, 1)
        """, (id_tipo_usuario, password_hash, id_habitante))

        return jsonify({'success': True, 'message': 'Usuario creado', 'id': user_id}), 201

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al crear usuario: {str(e)}'}), 500

# =========================
# CAMBIAR ROL
# =========================
@usuarios_bp.route('/<int:id>/rol', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_rol(id):
    try:
        if not _usuario_existe(id):
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404

        data = request.get_json() or {}
        id_tipo_usuario = data.get('id_tipo_usuario')
        if not id_tipo_usuario:
            return jsonify({'success': False, 'message': 'id_tipo_usuario es requerido'}), 400

        updated = execute_query(
            "UPDATE usuario SET IdTipoUsuario = %s WHERE IdUsuario = %s AND Activo = 1",
            (id_tipo_usuario, id)
        )
        if updated == 0:
            return jsonify({'success': False, 'message': 'No se pudo actualizar (usuario inactivo o sin cambios)'}), 400

        return jsonify({'success': True, 'message': 'Rol actualizado'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al actualizar rol: {str(e)}'}), 500

# =========================
# CAMBIAR CONTRASEÑA
# =========================
@usuarios_bp.route('/<int:id>/password', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def actualizar_password(id):
    try:
        if not _usuario_existe(id):
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404

        data = request.get_json() or {}
        new_password = data.get('password')
        if not new_password:
            return jsonify({'success': False, 'message': 'password es requerido'}), 400

        policy = Security.validate_password(new_password)
        if not policy['valid']:
            return jsonify({'success': False, 'message': 'Contraseña inválida', 'errors': policy['errors']}), 400

        password_hash = Security.generate_password_hash(new_password)
        updated = execute_query(
            "UPDATE usuario SET Contraseña = %s WHERE IdUsuario = %s AND Activo = 1",
            (password_hash, id)
        )
        if updated == 0:
            return jsonify({'success': False, 'message': 'No se pudo actualizar la contraseña (usuario inactivo?)'}), 400

        return jsonify({'success': True, 'message': 'Contraseña actualizada'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al actualizar contraseña: {str(e)}'}), 500

# =========================
# ACTIVAR / DESACTIVAR
# =========================
@usuarios_bp.route('/<int:id>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_usuario(id):
    try:
        updated = execute_query(
            "UPDATE usuario SET Activo = 0 WHERE IdUsuario = %s AND Activo = 1",
            (id,)
        )
        if updated == 0:
            return jsonify({'success': False, 'message': 'Usuario no encontrado o ya inactivo'}), 404
        return jsonify({'success': True, 'message': 'Usuario desactivado'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al desactivar usuario: {str(e)}'}), 500


@usuarios_bp.route('/<int:id>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_usuario(id):
    try:
        updated = execute_query(
            "UPDATE usuario SET Activo = 1 WHERE IdUsuario = %s AND Activo = 0",
            (id,)
        )
        if updated == 0:
            return jsonify({'success': False, 'message': 'Usuario no encontrado o ya activo'}), 404
        return jsonify({'success': True, 'message': 'Usuario activado'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al activar usuario: {str(e)}'}), 500
