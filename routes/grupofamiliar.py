"""
Rutas para gestión de grupos familiares
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query, get_db_connection
from utils import require_rol
from datetime import datetime

grupofamiliar_bp = Blueprint('grupofamiliar', __name__)

# =========================
# BÚSQUEDA DINÁMICA PARA AUTOCOMPLETADO
# =========================
@grupofamiliar_bp.route('/buscar_dinamico', methods=['GET'])
@jwt_required()
def buscar_grupos_dinamico():
    """
    Búsqueda dinámica de grupos familiares - para autocompletado
    """
    try:
        q = (request.args.get('q') or '').strip()
        
        if len(q) < 1:
            return jsonify({'success': True, 'grupos': []}), 200

        query = """
            SELECT 
                gf.IdGrupoFamiliar,
                gf.NombreGrupo,
                gf.Descripcion,
                CONCAT(COALESCE(h.Nombre,''), ' ', COALESCE(h.Apellido,'')) AS JefeFamilia,
                h.IdHabitante AS IdJefeFamilia
            FROM grupofamiliar gf
            LEFT JOIN habitantes h ON h.IdHabitante = gf.IdJefeFamilia
            WHERE gf.Activo = 1 
            AND (gf.NombreGrupo LIKE %s OR gf.Descripcion LIKE %s)
            ORDER BY gf.NombreGrupo
            LIMIT 10
        """
        like_term = f"%{q}%"
        grupos = execute_query(query, (like_term, like_term))
        
        return jsonify({'success': True, 'grupos': grupos}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f"Error en búsqueda dinámica: {str(e)}"}), 500

# =========================
# BUSCAR HABITANTES PARA ASIGNAR COMO JEFE
# =========================
@grupofamiliar_bp.route('/buscar_habitantes_jefe', methods=['GET'])
@jwt_required()
def buscar_habitantes_para_jefe():
    """
    Buscar habitantes para asignar como jefe de familia
    """
    try:
        q = (request.args.get('q') or '').strip()
        
        if len(q) < 1:
            return jsonify({'success': True, 'habitantes': []}), 200

        query = """
            SELECT 
                h.IdHabitante,
                h.Nombre,
                h.Apellido,
                h.NumeroDocumento,
                h.Telefono,
                COALESCE(gf.NombreGrupo, 'Sin grupo') AS GrupoActual
            FROM habitantes h
            LEFT JOIN grupofamiliar gf ON gf.IdGrupoFamiliar = h.IdGrupoFamiliar
            WHERE h.Activo = 1
            AND (h.Nombre LIKE %s OR h.Apellido LIKE %s OR h.NumeroDocumento LIKE %s)
            ORDER BY h.Apellido, h.Nombre
            LIMIT 10
        """
        like_term = f"%{q}%"
        habitantes = execute_query(query, (like_term, like_term, like_term))
        
        return jsonify({'success': True, 'habitantes': habitantes}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f"Error buscando habitantes: {str(e)}"}), 500

# =========================
# CREAR GRUPO FAMILIAR CON JEFE
# =========================
@grupofamiliar_bp.route('/crear_con_jefe', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_grupo_con_jefe():
    """
    Crea un nuevo grupo familiar y asigna un jefe de familia
    """
    try:
        data = request.get_json(silent=True) or {}
        nombre = (data.get('nombre') or '').strip()
        descripcion = (data.get('descripcion') or '').strip() or None
        id_jefe = data.get('id_jefe')  # puede ser None

        if not nombre:
            return jsonify({'success': False, 'message': 'El nombre del grupo familiar es obligatorio'}), 400

        # Verificar que el jefe existe si se proporciona
        if id_jefe:
            habitante_query = "SELECT IdHabitante FROM habitantes WHERE IdHabitante = %s AND Activo = 1"
            habitante = execute_query(habitante_query, (id_jefe,), fetch_one=True)
            if not habitante:
                return jsonify({'success': False, 'message': 'El habitante seleccionado no existe'}), 400

        # Crear grupo familiar
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO grupofamiliar (NombreGrupo, Descripcion, IdJefeFamilia, Activo)
            VALUES (%s, %s, %s, 1)
            """,
            (nombre, descripcion, id_jefe)
        )
        conn.commit()
        grupo_id = cur.lastrowid

        # Si se asignó un jefe, actualizar su grupo familiar
        if id_jefe:
            cur.execute(
                "UPDATE habitantes SET IdGrupoFamiliar = %s WHERE IdHabitante = %s",
                (grupo_id, id_jefe)
            )
            conn.commit()

        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Grupo familiar creado exitosamente',
            'id': int(grupo_id),
            'con_jefe': bool(id_jefe)
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al crear grupo familiar: {str(e)}"}), 500

# =========================
# RUTAS EXISTENTES (se mantienen)
# =========================
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
    try:
        q = (request.args.get('q') or '').strip()
        if len(q) < 2:
            return jsonify({'success': True, 'grupos': []}), 200

        query = """
            SELECT 
                gf.IdGrupoFamiliar,
                gf.NombreGrupo,
                gf.Descripcion,
                CONCAT(COALESCE(h.Nombre,''), ' ', COALESCE(h.Apellido,'')) AS JefeFamilia
            FROM grupofamiliar gf
            LEFT JOIN habitantes h ON h.IdHabitante = gf.IdJefeFamilia
            WHERE gf.Activo = 1 AND gf.NombreGrupo LIKE %s
            ORDER BY gf.NombreGrupo
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

# CREAR GRUPO FAMILIAR SIMPLE (SIN FAMILIAR ASOCIADO INICIAL)
@grupofamiliar_bp.route('/crear_simple', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_grupo_simple():
    """
    Crea un nuevo grupo familiar sin familiar asociado inicial
    """
    try:
        data = request.get_json(silent=True) or {}
        nombre = (data.get('nombre') or '').strip()
        # QUITAMOS LA DESCRIPCIÓN - se asignará automáticamente después

        if not nombre:
            return jsonify({'success': False, 'message': 'El nombre del grupo familiar es obligatorio'}), 400

        # Crear grupo familiar SIN familiar asociado y SIN descripción inicial
        insert_sql = """
            INSERT INTO grupofamiliar (NombreGrupo, Descripcion, IdJefeFamilia, Activo)
            VALUES (%s, NULL, NULL, 1)
        """
        grupo_id = execute_query(insert_sql, (nombre,))

        return jsonify({
            'success': True,
            'message': 'Grupo familiar creado exitosamente',
            'id': int(grupo_id)
        }), 201

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

@grupofamiliar_bp.route('/<int:id>/asignar_jefe/<int:id_habitante>', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def asignar_jefe(id, id_habitante):
    try:
        rows = execute_query(
        "UPDATE grupofamiliar SET IdJefeFamilia=%s WHERE IdGrupoFamiliar=%s",(id_habitante, id)
        )
        if rows is not None:
            return jsonify({'success': True, 'message': 'Jefe de familia asignado'}), 200
        return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al asignar jefe: {str(e)}"}), 500

@grupofamiliar_bp.route('/<int:id>/remover_jefe', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def remover_jefe(id):
    try:
        execute_query(
            "UPDATE grupofamiliar SET IdJefeFamilia=NULL WHERE IdGrupoFamiliar=%s",
            (id,)
        )
        return jsonify({'success': True, 'message': 'Jefe de familia removido'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al remover jefe: {str(e)}"}), 500