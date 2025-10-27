"""
Rutas para gestión de grupos ayudantes
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query
from utils import require_rol
from datetime import datetime

grupofamiliar_bp = Blueprint('grupofamiliar', __name__)

@grupofamiliar_bp.route('/', methods=['GET'])
@jwt_required()
def listar_grupofamiliar():
    """
    Lista todos los grupos familiares activos con su jefe de familia.
    """
    try:
        q = request.args.get('q', '')
        query = """
            SELECT 
                gf.IdGrupoFamiliar,
                gf.NombreGrupo,
                gf.Descripcion,
                gf.Activo,
                gf.IdJefeFamilia,
                CONCAT(h.Nombre, ' ', h.Apellido) AS JefeFamilia,
                h.NumeroDocumento AS DocumentoJefe,
                h.Telefono AS TelefonoJefe
            FROM grupofamiliar gf
            LEFT JOIN habitantes h ON h.IdHabitante = gf.IdJefeFamilia
            WHERE gf.Activo = 1 AND gf.NombreGrupo LIKE %s
            ORDER BY gf.IdGrupoFamiliar DESC
        """
        grupos = execute_query(query, (f"%{q}%",))
        return jsonify({'success': True, 'grupos': grupos}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al listar grupos familiares: {str(e)}"}), 500

@grupofamiliar_bp.route('/buscar', methods=['GET'])
@jwt_required()
def buscar_grupos_familiares():
    """
    Búsqueda simple de grupos familiares para autocomplete.
    """
    try:
        q = request.args.get('q', '').strip()
        
        if not q or len(q) < 2:
            return jsonify({'success': True, 'grupos': []}), 200

        query = """
            SELECT 
                IdGrupoFamiliar,
                NombreGrupo,
                Descripcion
            FROM grupofamiliar 
            WHERE Activo = 1 AND NombreGrupo LIKE %s
            ORDER BY NombreGrupo
            LIMIT 10
        """
        grupos = execute_query(query, (f"%{q}%",))
        
        return jsonify({'success': True, 'grupos': grupos}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error en búsqueda: {str(e)}"}), 500

@grupofamiliar_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_grupo_familiar(id):
    """
    Devuelve la información completa de un grupo familiar, incluyendo sus integrantes.
    """
    try:
        query_grupo = """
            SELECT 
                gf.IdGrupoFamiliar,
                gf.NombreGrupo,
                gf.Descripcion,
                gf.Activo,
                gf.IdJefeFamilia,
                CONCAT(h.Nombre, ' ', h.Apellido) AS JefeFamilia,
                h.NumeroDocumento AS DocumentoJefe,
                h.Telefono AS TelefonoJefe
            FROM grupofamiliar gf
            LEFT JOIN habitantes h ON h.IdHabitante = gf.IdJefeFamilia
            WHERE gf.IdGrupoFamiliar = %s
        """
        grupo = execute_query(query_grupo, (id,), fetch_one=True)
        if not grupo:
            return jsonify({'success': False, 'message': 'Grupo familiar no encontrado'}), 404

        query_integrantes = """
            SELECT 
                h.IdHabitante,
                h.Nombre,
                h.Apellido,
                h.NumeroDocumento,
                h.Telefono,
                h.CorreoElectronico,
                CASE 
                    WHEN h.IdHabitante = gf.IdJefeFamilia THEN 1 ELSE 0 
                END AS EsJefe
            FROM habitantes h
            JOIN grupofamiliar gf ON gf.IdGrupoFamiliar = h.IdGrupoFamiliar
            WHERE h.IdGrupoFamiliar = %s
            ORDER BY EsJefe DESC, h.Apellido, h.Nombre
        """
        integrantes = execute_query(query_integrantes, (id,))

        grupo['integrantes'] = integrantes
        return jsonify({'success': True, 'grupo': grupo}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al obtener grupo familiar: {str(e)}"}), 500

@grupofamiliar_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_grupo_familiar():
    """
    Crea un nuevo grupo familiar.
    """
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        id_jefe = data.get('id_jefe')

        if not nombre:
            return jsonify({'success': False, 'message': 'El nombre del grupo familiar es obligatorio'}), 400

        query = """
            INSERT INTO grupofamiliar (NombreGrupo, Descripcion, IdJefeFamilia, Activo)
            VALUES (%s, %s, %s, 1)
        """
        grupo_id = execute_query(query, (nombre, descripcion, id_jefe))
        return jsonify({'success': True, 'message': 'Grupo familiar creado exitosamente', 'id': grupo_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al crear grupo familiar: {str(e)}"}), 500

@grupofamiliar_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_grupo_familiar(id):
    try:
        data = request.get_json()
        query = """
            UPDATE grupofamiliar
            SET NombreGrupo = %s, Descripcion = %s, IdJefeFamilia = %s
            WHERE IdGrupoFamiliar = %s
        """
        updated = execute_query(query, (
            data.get('nombre'),
            data.get('descripcion'),
            data.get('id_jefe'),
            id
        ))
        if updated:
            return jsonify({'success': True, 'message': 'Grupo familiar actualizado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Grupo familiar no encontrado o no actualizado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al actualizar grupo familiar: {str(e)}"}), 500

@grupofamiliar_bp.route('/<int:id>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_grupo_familiar(id):
    try:
        rows = execute_query("""
            UPDATE grupofamiliar SET Activo = 0 WHERE IdGrupoFamiliar = %s
        """, (id,))
        if rows is not None:
            return jsonify({'success': True, 'message': 'Grupo familiar desactivado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al desactivar grupo: {str(e)}"}), 500

@grupofamiliar_bp.route('/<int:id>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_grupo_familiar(id):
    try:
        rows = execute_query("""
            UPDATE grupofamiliar SET Activo = 1 WHERE IdGrupoFamiliar = %s
        """, (id,))
        if rows is not None:
            return jsonify({'success': True, 'message': 'Grupo familiar activado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al activar grupo: {str(e)}"}), 500

@grupofamiliar_bp.route('/buscar_jefe', methods=['GET'])
@jwt_required()
def buscar_jefe():
    """
    Devuelve posibles jefes de familia activos que aún no están asignados como jefe en otro grupo.
    """
    try:
        q = request.args.get('q', '')
        query = """
            SELECT 
                h.IdHabitante,
                CONCAT(h.Nombre, ' ', h.Apellido) AS NombreCompleto,
                h.NumeroDocumento,
                h.Telefono
            FROM habitantes h
            WHERE h.Activo = 1
              AND (h.IdHabitante NOT IN (SELECT IdJefeFamilia FROM grupofamiliar WHERE Activo = 1))
              AND CONCAT(h.Nombre, ' ', h.Apellido) LIKE %s
            LIMIT 10
        """
        jefes = execute_query(query, (f"%{q}%",))
        return jsonify({'success': True, 'jefes': jefes}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al buscar jefes: {str(e)}"}), 500
    """
    Devuelve posibles jefes de familia activos que aún no están asignados como jefe en otro grupo.
    """
    try:
        q = request.args.get('q', '')
        query = """
            SELECT 
                h.IdHabitante,
                CONCAT(h.Nombre, ' ', h.Apellido) AS NombreCompleto,
                h.NumeroDocumento,
                h.Telefono
            FROM habitantes h
            WHERE h.Activo = 1
              AND (h.IdHabitante NOT IN (SELECT IdJefeFamilia FROM grupofamiliar WHERE Estado = 'Activo'))
              AND CONCAT(h.Nombre, ' ', h.Apellido) LIKE %s
            LIMIT 10
        """
        jefes = execute_query(query, (f"%{q}%",))
        return jsonify({'success': True, 'jefes': jefes}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al buscar jefes: {str(e)}"}), 500
