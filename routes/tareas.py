# =============================================
# MÓDULO DE TAREAS - GESTIÓN ECLESIAL
# =============================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query
from utils import require_rol
from datetime import datetime

tareas_bp = Blueprint('tareas', __name__)

# =============================================
# ENDPOINTS DE TIPOS DE TAREA
# =============================================

@tareas_bp.route('/tipos', methods=['GET'])
@jwt_required()
def listar_tipos_tarea():
    try:
        query = "SELECT IdTipoTarea, Descripcion, Activo FROM tipotarea ORDER BY IdTipoTarea DESC;"
        tipos = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"tipos_tarea": tipos}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/tipos', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_tipo_tarea():
    try:
        data = request.get_json()
        descripcion = data.get("descripcion")

        if not descripcion or descripcion.strip() == "":
            return jsonify({"success": False, "message": "La descripción es obligatoria"}), 400

        # Verificar duplicado
        existe = execute_query(
            "SELECT COUNT(*) AS cnt FROM tipotarea WHERE Descripcion = %s;",
            (descripcion,), fetch_one=True
        )
        if existe and existe["cnt"] > 0:
            return jsonify({"success": False, "message": "Ya existe un tipo de tarea con esa descripción"}), 409

        execute_query("INSERT INTO tipotarea (Descripcion) VALUES (%s);", (descripcion,))
        return jsonify({"success": True, "message": "Tipo de tarea creado exitosamente"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/tipos/<int:id>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_tipo_tarea(id):
    try:
        data = request.get_json()
        descripcion = data.get("descripcion")

        if not descripcion or descripcion.strip() == "":
            return jsonify({"success": False, "message": "La descripción es obligatoria"}), 400

        result = execute_query(
            "UPDATE tipotarea SET Descripcion = %s WHERE IdTipoTarea = %s;",
            (descripcion, id)
        )

        return jsonify({"success": True, "message": "Tipo de tarea actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/tipos/<int:id>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_tipo_tarea(id):
    try:
        execute_query("UPDATE tipotarea SET Activo = 0 WHERE IdTipoTarea = %s;", (id,))
        execute_query("UPDATE asignaciontarea SET Activo = 0 WHERE IdTipoTarea = %s;", (id,))
        return jsonify({"success": True, "message": "Tipo de tarea desactivado exitosamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/tipos/<int:id>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_tipo_tarea(id):
    try:
        execute_query("UPDATE tipotarea SET Activo = 1 WHERE IdTipoTarea = %s;", (id,))
        return jsonify({"success": True, "message": "Tipo de tarea activado exitosamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# =============================================
# ENDPOINTS DE ASIGNACIÓN DE TAREAS A GRUPOS
# =============================================

@tareas_bp.route('/asignaciones/grupo/<int:id_grupo>', methods=['GET'])
@jwt_required()
def listar_tareas_grupo(id_grupo):
    try:
        query = """
            SELECT 
                at.IdAsignacionTarea,
                at.IdTipoTarea,
                tt.Descripcion AS Tarea,
                at.FechaAsignacion,
                at.EstadoTarea,
                at.Activo
            FROM asignaciontarea at
            JOIN tipotarea tt ON at.IdTipoTarea = tt.IdTipoTarea
            WHERE at.IdGrupoVoluntario = %s AND at.Activo = 1
            ORDER BY at.FechaAsignacion DESC;
        """
        tareas = execute_query(query, (id_grupo,), fetch_all=True)
        return jsonify({"success": True, "data": {"tareas": tareas}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/grupo/<int:id_grupo>', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def asignar_tarea(id_grupo):
    try:
        data = request.get_json()
        id_tipo_tarea = data.get("id_tipo_tarea")

        if not id_tipo_tarea:
            return jsonify({"success": False, "message": "Debe especificar el tipo de tarea"}), 400

        # Validar grupo activo
        grupo = execute_query(
            "SELECT IdGrupoAyudantes FROM grupoayudantes WHERE IdGrupoAyudantes = %s AND Activo = 1;",
            (id_grupo,), fetch_one=True
        )
        if not grupo:
            return jsonify({"success": False, "message": "El grupo no existe o está inactivo"}), 404

        # Verificar duplicado activo
        duplicado = execute_query(
            "SELECT Activo FROM asignaciontarea WHERE IdGrupoVoluntario = %s AND IdTipoTarea = %s;",
            (id_grupo, id_tipo_tarea), fetch_one=True
        )
        if duplicado and duplicado.get("Activo") == 1:
            return jsonify({"success": False, "message": "Ya existe una tarea activa de este tipo para el grupo"}), 409

        # Asignar
        query = """
            INSERT INTO asignaciontarea (IdGrupoVoluntario, IdTipoTarea, FechaAsignacion, EstadoTarea, Activo)
            VALUES (%s, %s, NOW(), 'Pendiente', 1);
        """
        execute_query(query, (id_grupo, id_tipo_tarea))
        return jsonify({"success": True, "message": "Tarea asignada correctamente al grupo"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/grupo/<int:id_grupo>/tarea/<int:id_tarea>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_estado_tarea(id_grupo, id_tarea):
    try:
        data = request.get_json()
        nuevo_estado = data.get("estado")

        estados_validos = ['Pendiente', 'En progreso', 'Cumplida', 'Cancelada']
        if nuevo_estado not in estados_validos:
            return jsonify({"success": False, "message": "Estado de tarea inválido"}), 400

        query = """
            UPDATE asignaciontarea 
            SET EstadoTarea = %s
            WHERE IdAsignacionTarea = %s AND IdGrupoVoluntario = %s AND Activo = 1;
        """
        execute_query(query, (nuevo_estado, id_tarea, id_grupo))
        return jsonify({"success": True, "message": "Estado de tarea actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/grupo/<int:id_grupo>/tarea/<int:id_tarea>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_tarea(id_grupo, id_tarea):
    try:
        query = """
            UPDATE asignaciontarea
            SET Activo = 0
            WHERE IdAsignacionTarea = %s AND IdGrupoVoluntario = %s;
        """
        execute_query(query, (id_tarea, id_grupo))
        return jsonify({"success": True, "message": "Tarea desactivada correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/grupo/<int:id_grupo>/tarea/<int:id_tarea>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_tarea(id_grupo, id_tarea):
    try:
        query = """
            UPDATE asignaciontarea
            SET Activo = 1
            WHERE IdAsignacionTarea = %s AND IdGrupoVoluntario = %s;
        """
        execute_query(query, (id_tarea, id_grupo))
        return jsonify({"success": True, "message": "Tarea activada correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# ENDPOINTS DE GESTIÓN GENERAL DE TAREAS
# =============================================

@tareas_bp.route('/', methods=['GET'])
@jwt_required()
def listar_tareas():
    try:
        query = """
            SELECT 
                at.IdAsignacionTarea,
                g.Nombre AS Grupo,
                tt.Descripcion AS TipoTarea,
                at.FechaAsignacion,
                at.EstadoTarea,
                at.Activo
            FROM asignaciontarea at
            JOIN grupoayudantes g ON at.IdGrupoVoluntario = g.IdGrupoAyudantes
            JOIN tipotarea tt ON at.IdTipoTarea = tt.IdTipoTarea
            WHERE at.Activo = 1
            ORDER BY at.FechaAsignacion DESC;
        """
        tareas = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"tareas": tareas}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_tarea(id):
    try:
        query = """
            SELECT 
                at.IdAsignacionTarea,
                g.Nombre AS Grupo,
                tt.Descripcion AS TipoTarea,
                at.FechaAsignacion,
                at.EstadoTarea,
                at.Activo
            FROM asignaciontarea at
            JOIN grupoayudantes g ON at.IdGrupoVoluntario = g.IdGrupoAyudantes
            JOIN tipotarea tt ON at.IdTipoTarea = tt.IdTipoTarea
            WHERE at.IdAsignacionTarea = %s;
        """
        tarea = execute_query(query, (id,), fetch_one=True)
        if not tarea:
            return jsonify({"success": False, "message": "Tarea no encontrada"}), 404
        return jsonify({"success": True, "data": tarea}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
