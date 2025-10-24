from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from utils import require_rol
from utils.Security import Security
from database import execute_query
from datetime import datetime

usuarios_bp = Blueprint('usuarios', __name__)

# =============================================
# ENDPOINTS DE USUARIOS - VERSIÓN COMPLETA
# =============================================

# ---------- 1. LISTAR USUARIOS ----------
@usuarios_bp.route('/', methods=['GET'])
@jwt_required()
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
            LEFT JOIN habitantes h ON u.IdHabitante = h.IdHabitante
            LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
            ORDER BY u.IdUsuario DESC
            LIMIT 500;
        """
        data = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"usuarios": data}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- 2. OBTENER USUARIO POR ID ----------
@usuarios_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
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
            LEFT JOIN habitantes h ON u.IdHabitante = h.IdHabitante
            LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
            WHERE u.IdUsuario = %s;
        """
        usuario = execute_query(query, (id,), fetch_one=True)
        if not usuario:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404

        return jsonify({"success": True, "data": usuario}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- 3. VERIFICAR HABITANTE ----------
@usuarios_bp.route('/verificar_habitante', methods=['GET'])
@jwt_required()
def verificar_habitante():
    """
    Endpoint útil para el frontend: verifica si un habitante existe y puede tener usuario
    """
    try:
        tipo_documento = request.args.get('tipo_documento')
        numero_documento = request.args.get('numero_documento')

        if not tipo_documento or not numero_documento:
            return jsonify({
                "success": False, 
                "message": "Se requieren tipo_documento y numero_documento"
            }), 400

        query = """
            SELECT 
                h.IdHabitante,
                h.Nombre,
                h.Apellido,
                h.Activo,
                td.Descripcion AS TipoDocumento,
                h.NumeroDocumento,
                u.IdUsuario AS TieneUsuario
            FROM habitantes h
            INNER JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
            LEFT JOIN usuario u ON h.IdHabitante = u.IdHabitante AND u.Activo = 1
            WHERE td.Descripcion = %s AND h.NumeroDocumento = %s
        """
        
        resultado = execute_query(query, (tipo_documento, numero_documento), fetch_one=True)
        
        if not resultado:
            return jsonify({
                "success": False,
                "message": f"No se encontró habitante con {tipo_documento}: {numero_documento}",
                "existe": False
            }), 404

        # Analizar situación del habitante
        if not resultado['Activo']:
            return jsonify({
                "success": False,
                "message": "El habitante está inactivo",
                "existe": True,
                "activo": False,
                "tiene_usuario": resultado['TieneUsuario'] is not None,
                "habitante": {
                    "id": resultado['IdHabitante'],
                    "nombre": resultado['Nombre'],
                    "apellido": resultado['Apellido'],
                    "tipo_documento": resultado['TipoDocumento'],
                    "numero_documento": resultado['NumeroDocumento']
                }
            }), 400

        if resultado['TieneUsuario']:
            return jsonify({
                "success": False,
                "message": "El habitante ya tiene un usuario activo",
                "existe": True,
                "activo": True,
                "tiene_usuario": True,
                "habitante": {
                    "id": resultado['IdHabitante'],
                    "nombre": resultado['Nombre'],
                    "apellido": resultado['Apellido'],
                    "tipo_documento": resultado['TipoDocumento'],
                    "numero_documento": resultado['NumeroDocumento']
                }
            }), 409

        # Habitante válido para crear usuario
        return jsonify({
            "success": True,
            "message": "Habitante encontrado y puede crear usuario",
            "existe": True,
            "activo": True,
            "tiene_usuario": False,
            "habitante": {
                "id": resultado['IdHabitante'],
                "nombre": resultado['Nombre'],
                "apellido": resultado['Apellido'],
                "tipo_documento": resultado['TipoDocumento'],
                "numero_documento": resultado['NumeroDocumento']
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- 4. CREAR USUARIO ----------
@usuarios_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_usuario():
    try:
        data = request.get_json()
        
        # Recibimos tipo_documento y numero_documento en lugar de id_habitante
        tipo_documento = data.get("tipo_documento")  # Ej: "CC", "TI", "CE"
        numero_documento = data.get("numero_documento")
        id_tipo_usuario = data.get("id_tipo_usuario")
        password = data.get("password")

        if not tipo_documento or not numero_documento or not id_tipo_usuario or not password:
            return jsonify({
                "success": False, 
                "message": "Faltan campos requeridos: tipo_documento, numero_documento, id_tipo_usuario, password"
            }), 400

        # PRIMERO: Buscar el habitante por tipo y número de documento
        habitante = execute_query(
            """SELECT h.IdHabitante, h.Activo 
               FROM habitantes h 
               INNER JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
               WHERE td.Descripcion = %s AND h.NumeroDocumento = %s""",
            (tipo_documento, numero_documento), 
            fetch_one=True
        )
        
        if not habitante:
            return jsonify({
                "success": False, 
                "message": f"No se encontró habitante con {tipo_documento}: {numero_documento}"
            }), 404

        if not habitante['Activo']:
            return jsonify({
                "success": False, 
                "message": "El habitante existe pero está inactivo"
            }), 400

        id_habitante = habitante['IdHabitante']

        # SEGUNDO: Verificar si ya tiene usuario activo
        usuario_existente = execute_query(
            "SELECT IdUsuario FROM usuario WHERE IdHabitante = %s AND Activo = 1",
            (id_habitante,), 
            fetch_one=True
        )
        
        if usuario_existente:
            return jsonify({
                "success": False, 
                "message": "El habitante ya tiene un usuario activo"
            }), 409

        # TERCERO: Validar y crear usuario
        valid, msg = Security.validate_password(password)
        if not valid:
            return jsonify({"success": False, "message": msg}), 400

        hashed = Security.generate_password_hash(password)
        insert = """
            INSERT INTO usuario (IdTipoUsuario, Contraseña, IdHabitante, Activo, FechaRegistro)
            VALUES (%s, %s, %s, 1, NOW());
        """
        execute_query(insert, (id_tipo_usuario, hashed, id_habitante))
        
        return jsonify({
            "success": True, 
            "message": f"Usuario creado exitosamente para {tipo_documento} {numero_documento}"
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- 5. ACTUALIZAR ROL DE USUARIO ----------
@usuarios_bp.route('/<int:id>/rol', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_rol_usuario(id):
    try:
        data = request.get_json()
        id_tipo_usuario = data.get("id_tipo_usuario")

        if not id_tipo_usuario:
            return jsonify({"success": False, "message": "Debe proporcionar el ID del nuevo rol"}), 400

        # Verificar existencia y actualizar en una sola operación
        result = execute_query(
            "UPDATE usuario SET IdTipoUsuario = %s WHERE IdUsuario = %s AND Activo = 1;",
            (id_tipo_usuario, id)
        )
        
        if result and getattr(result, 'rowcount', 0) == 0:
            return jsonify({"success": False, "message": "Usuario no encontrado o inactivo"}), 404

        return jsonify({"success": True, "message": "Rol actualizado exitosamente"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- 6. CAMBIAR CONTRASEÑA ----------
@usuarios_bp.route('/<int:id>/password', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def cambiar_contraseña(id):
    try:
        data = request.get_json()
        password = data.get("password")

        if not password:
            return jsonify({"success": False, "message": "Debe proporcionar una nueva contraseña"}), 400

        valid, msg = Security.validate_password(password)
        if not valid:
            return jsonify({"success": False, "message": msg}), 400

        hashed = Security.generate_password_hash(password)
        result = execute_query(
            "UPDATE usuario SET Contraseña = %s WHERE IdUsuario = %s AND Activo = 1;",
            (hashed, id)
        )
        
        if result and getattr(result, 'rowcount', 0) == 0:
            return jsonify({"success": False, "message": "Usuario no encontrado o inactivo"}), 404

        return jsonify({"success": True, "message": "Contraseña actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- 7. ACTIVAR / DESACTIVAR USUARIO ----------
@usuarios_bp.route('/<int:id>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_usuario(id):
    try:
        result = execute_query(
            "UPDATE usuario SET Activo = 0 WHERE IdUsuario = %s AND Activo = 1;", 
            (id,)
        )
        
        if result and getattr(result, 'rowcount', 0) == 0:
            return jsonify({"success": False, "message": "Usuario no encontrado o ya inactivo"}), 404

        return jsonify({"success": True, "message": "Usuario desactivado exitosamente"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@usuarios_bp.route('/<int:id>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_usuario(id):
    try:
        result = execute_query(
            "UPDATE usuario SET Activo = 1 WHERE IdUsuario = %s AND Activo = 0;", 
            (id,)
        )
        
        if result and getattr(result, 'rowcount', 0) == 0:
            return jsonify({"success": False, "message": "Usuario no encontrado o ya activo"}), 404

        return jsonify({"success": True, "message": "Usuario activado exitosamente"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------- 8. LISTAR ROLES DISPONIBLES ----------
@usuarios_bp.route('/roles', methods=['GET'])
@jwt_required()
def listar_roles():
    try:
        query = "SELECT IdTipoUsuario, Perfil FROM tipousuario;"
        roles = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"roles": roles}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500