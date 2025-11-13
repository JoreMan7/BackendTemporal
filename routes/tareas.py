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
# 1) CATÁLOGO: TIPOS DE TAREA (tabla tipotarea)
# =============================================

@tareas_bp.route('/tipos/', methods=['GET'])
@jwt_required()
def listar_tipos_tarea():
    try:
        query = """
            SELECT 
                IdTipoTarea,
                Nombre,
                Descripcion,
                Activo
            FROM tipotarea
            ORDER BY IdTipoTarea DESC;
        """
        tipos = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"tipos_tarea": tipos}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/tipos/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_tipo_tarea():
    try:
        data = request.get_json() or {}
        nombre = (data.get("nombre") or "").strip()
        descripcion = (data.get("descripcion") or "").strip() or None

        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"}), 400

        # Verificar duplicado
        existe = execute_query(
            "SELECT COUNT(*) AS cnt FROM tipotarea WHERE Nombre = %s;",
            (nombre,), fetch_one=True
        )
        if existe and existe["cnt"] > 0:
            return jsonify({"success": False, "message": "Ya existe un tipo de tarea con ese nombre"}), 409

        execute_query(
            "INSERT INTO tipotarea (Nombre, Descripcion, Activo) VALUES (%s, %s, 1);",
            (nombre, descripcion)
        )
        return jsonify({"success": True, "message": "Tipo de tarea creado exitosamente"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/tipos/<int:id>/', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_tipo_tarea(id):
    try:
        data = request.get_json() or {}
        nombre = (data.get("nombre") or "").strip()
        descripcion = (data.get("descripcion") or "").strip() or None

        if not nombre:
            return jsonify({"success": False, "message": "El nombre es obligatorio"}), 400

        execute_query(
            "UPDATE tipotarea SET Nombre = %s, Descripcion = %s WHERE IdTipoTarea = %s;",
            (nombre, descripcion, id)
        )
        return jsonify({"success": True, "message": "Tipo de tarea actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/tipos/<int:id>/desactivar/', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_tipo_tarea(id):
    """
    Desactiva un tipo de tarea (y opcionalmente todas sus asignaciones activas).
    """
    try:
        # Marcar tipo como inactivo
        execute_query(
            "UPDATE tipotarea SET Activo = 0 WHERE IdTipoTarea = %s;",
            (id,)
        )
        # Desactivar todas las asignaciones activas de ese tipo
        execute_query(
            "UPDATE asignaciontarea SET Activo = 0 WHERE IdTipoTarea = %s AND Activo = 1;",
            (id,)
        )
        return jsonify({"success": True, "message": "Tipo de tarea y sus asignaciones activas fueron desactivadas"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/tipos/<int:id>/activar/', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_tipo_tarea(id):
    """
    Reactiva un tipo de tarea (no toca sus asignaciones).
    """
    try:
        execute_query(
            "UPDATE tipotarea SET Activo = 1 WHERE IdTipoTarea = %s;",
            (id,)
        )
        return jsonify({"success": True, "message": "Tipo de tarea activado nuevamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# 2) ASIGNACIONES DE TAREAS (tabla asignaciontarea)
#    - Vista general para módulo Tareas
# =============================================

@tareas_bp.route('/asignaciones/', methods=['GET'])
@jwt_required()
def listar_asignaciones():
    """
    Lista todas las tareas asignadas (asignaciontarea), activas.
    """
    try:
        query = """
            SELECT 
                at.IdAsignacionTarea,
                at.IdGrupoVoluntario,
                at.IdTipoTarea,
                g.Nombre AS Grupo,
                tt.Descripcion AS TipoTarea,
                at.FechaAsignacion,
                at.EstadoTarea,
                at.Activo
            FROM asignaciontarea at
            LEFT JOIN grupoayudantes g 
                ON at.IdGrupoVoluntario = g.IdGrupoAyudantes
            JOIN tipotarea tt 
                ON at.IdTipoTarea = tt.IdTipoTarea
            WHERE at.Activo = 1
            ORDER BY at.FechaAsignacion DESC, at.IdAsignacionTarea DESC;
        """
        asignaciones = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"asignaciones": asignaciones}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_asignacion():
    """
    Crea una nueva asignación de tarea:
    - id_tipo_tarea (obligatorio)
    - id_grupo_voluntario (obligatorio)
    - fecha_asignacion (obligatorio, formato YYYY-MM-DD)
    - estado_tarea (opcional, por defecto 'Pendiente')
    """
    try:
        data = request.get_json() or {}

        id_tipo_tarea = data.get("id_tipo_tarea")
        id_grupo = data.get("id_grupo_voluntario")
        fecha_asignacion = data.get("fecha_asignacion")
        estado_tarea = data.get("estado_tarea", "Pendiente")

        faltantes = []
        if not id_tipo_tarea:
            faltantes.append("id_tipo_tarea")
        if not id_grupo:
            faltantes.append("id_grupo_voluntario")
        if not fecha_asignacion:
            faltantes.append("fecha_asignacion")

        if faltantes:
            return jsonify({
                "success": False,
                "message": "Campos obligatorios faltantes: " + ", ".join(faltantes)
            }), 400

        # Validar fecha
        try:
            fecha_obj = datetime.strptime(fecha_asignacion, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Formato de fecha inválido. Use YYYY-MM-DD."}), 400

        # Validar tipo de tarea
        tipo = execute_query(
            "SELECT IdTipoTarea, Activo FROM tipotarea WHERE IdTipoTarea = %s;",
            (id_tipo_tarea,), fetch_one=True
        )
        if not tipo or tipo.get("Activo") == 0:
            return jsonify({"success": False, "message": "El tipo de tarea no existe o está inactivo"}), 400

        # Validar grupo
        grupo = execute_query(
            "SELECT IdGrupoAyudantes, Activo FROM grupoayudantes WHERE IdGrupoAyudantes = %s;",
            (id_grupo,), fetch_one=True
        )
        if not grupo or grupo.get("Activo") == 0:
            return jsonify({"success": False, "message": "El grupo no existe o está inactivo"}), 400

        # Validar estado
        estados_validos = {'Pendiente', 'En progreso', 'Cumplida', 'Cancelada'}
        if estado_tarea not in estados_validos:
            return jsonify({"success": False, "message": "Estado de tarea no válido"}), 400

        insert_query = """
            INSERT INTO asignaciontarea (EstadoTarea, FechaAsignacion, IdGrupoVoluntario, IdTipoTarea, Activo)
            VALUES (%s, %s, %s, %s, 1);
        """
        new_id = execute_query(insert_query, (estado_tarea, fecha_obj, id_grupo, id_tipo_tarea))

        return jsonify({"success": True, "message": "Asignación creada correctamente", "id": new_id}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/<int:id>/', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_asignacion(id):
    """
    Actualiza una asignación de tarea:
    - puede cambiar grupo, tipo de tarea, fecha y estado.
    """
    try:
        data = request.get_json() or {}

        id_grupo = data.get("id_grupo_voluntario")
        id_tipo_tarea = data.get("id_tipo_tarea")
        fecha_asignacion = data.get("fecha_asignacion")
        estado_tarea = data.get("estado_tarea")

        existente = execute_query(
            "SELECT * FROM asignaciontarea WHERE IdAsignacionTarea = %s AND Activo = 1;",
            (id,), fetch_one=True
        )
        if not existente:
            return jsonify({"success": False, "message": "La asignación no existe o está inactiva"}), 404

        # Fecha
        if fecha_asignacion:
            try:
                fecha_obj = datetime.strptime(fecha_asignacion, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"success": False, "message": "Formato de fecha inválido. Use YYYY-MM-DD."}), 400
        else:
            fecha_obj = existente["FechaAsignacion"]

        # Grupo
        if id_grupo:
            grupo = execute_query(
                "SELECT IdGrupoAyudantes, Activo FROM grupoayudantes WHERE IdGrupoAyudantes = %s;",
                (id_grupo,), fetch_one=True
            )
            if not grupo or grupo.get("Activo") == 0:
                return jsonify({"success": False, "message": "El grupo no existe o está inactivo"}), 400
        else:
            id_grupo = existente["IdGrupoVoluntario"]

        # Tipo de tarea
        if id_tipo_tarea:
            tipo = execute_query(
                "SELECT IdTipoTarea, Activo FROM tipotarea WHERE IdTipoTarea = %s;",
                (id_tipo_tarea,), fetch_one=True
            )
            if not tipo or tipo.get("Activo") == 0:
                return jsonify({"success": False, "message": "El tipo de tarea no existe o está inactivo"}), 400
        else:
            id_tipo_tarea = existente["IdTipoTarea"]

        # Estado
        if estado_tarea:
            estados_validos = {'Pendiente', 'En progreso', 'Cumplida', 'Cancelada'}
            if estado_tarea not in estados_validos:
                return jsonify({"success": False, "message": "Estado de tarea no válido"}), 400
        else:
            estado_tarea = existente["EstadoTarea"]

        update_query = """
            UPDATE asignaciontarea
            SET IdGrupoVoluntario = %s,
                IdTipoTarea = %s,
                FechaAsignacion = %s,
                EstadoTarea = %s
            WHERE IdAsignacionTarea = %s;
        """
        execute_query(update_query, (id_grupo, id_tipo_tarea, fecha_obj, estado_tarea, id))

        return jsonify({"success": True, "message": "Asignación actualizada correctamente"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/<int:id>/desactivar/', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_asignacion(id):
    """
    Desactiva (soft-delete) una asignación de tarea.
    """
    try:
        existente = execute_query(
            "SELECT IdAsignacionTarea FROM asignaciontarea WHERE IdAsignacionTarea = %s AND Activo = 1;",
            (id,), fetch_one=True
        )
        if not existente:
            return jsonify({"success": False, "message": "Asignación no encontrada o ya inactiva"}), 404

        execute_query(
            "UPDATE asignaciontarea SET Activo = 0 WHERE IdAsignacionTarea = %s;",
            (id,)
        )

        return jsonify({"success": True, "message": "Asignación desactivada correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/<int:id>/', methods=['GET'])
@jwt_required()
def obtener_asignacion(id):
    """
    Devuelve el detalle de una asignación de tarea.
    """
    try:
        query = """
            SELECT 
                at.IdAsignacionTarea,
                at.IdGrupoVoluntario,
                at.IdTipoTarea,
                g.Nombre AS Grupo,
                tt.Descripcion AS TipoTarea,
                at.FechaAsignacion,
                at.EstadoTarea,
                at.Activo
            FROM asignaciontarea at
            LEFT JOIN grupoayudantes g 
                ON at.IdGrupoVoluntario = g.IdGrupoAyudantes
            JOIN tipotarea tt 
                ON at.IdTipoTarea = tt.IdTipoTarea
            WHERE at.IdAsignacionTarea = %s;
        """
        asignacion = execute_query(query, (id,), fetch_one=True)
        if not asignacion:
            return jsonify({"success": False, "message": "Asignación no encontrada"}), 404
        return jsonify({"success": True, "data": asignacion}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# 3) ASIGNACIONES POR GRUPO (para usar desde módulo Grupos)
# =============================================

@tareas_bp.route('/asignaciones/grupo/<int:id_grupo>/', methods=['GET'])
@jwt_required()
def listar_tareas_grupo(id_grupo):
    """
    Lista tareas activas asignadas a un grupo específico.
    Ideal para usar desde el módulo de Grupos de Ayudantes.
    """
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
            ORDER BY at.FechaAsignacion DESC, at.IdAsignacionTarea DESC;
        """
        tareas = execute_query(query, (id_grupo,), fetch_all=True)
        return jsonify({"success": True, "data": {"tareas": tareas}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@tareas_bp.route('/asignaciones/grupo/<int:id_grupo>/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def asignar_tarea_a_grupo(id_grupo):
    """
    Crea asignación desde el contexto de un grupo (botón ASIGNAR TAREA en módulo Grupos).
    """
    try:
        data = request.get_json() or {}
        id_tipo_tarea = data.get("id_tipo_tarea")
        fecha_asignacion = data.get("fecha_asignacion")
        estado_tarea = data.get("estado_tarea", "Pendiente")

        if not id_tipo_tarea or not fecha_asignacion:
            return jsonify({"success": False, "message": "Debe especificar tipo de tarea y fecha"}), 400

        # Validar fecha
        try:
            fecha_obj = datetime.strptime(fecha_asignacion, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Formato de fecha inválido. Use YYYY-MM-DD."}), 400

        # Validar grupo
        grupo = execute_query(
            "SELECT IdGrupoAyudantes, Activo FROM grupoayudantes WHERE IdGrupoAyudantes = %s;",
            (id_grupo,), fetch_one=True
        )
        if not grupo or grupo.get("Activo") == 0:
            return jsonify({"success": False, "message": "El grupo no existe o está inactivo"}), 404

        # Validar tipo
        tipo = execute_query(
            "SELECT IdTipoTarea, Activo FROM tipotarea WHERE IdTipoTarea = %s;",
            (id_tipo_tarea,), fetch_one=True
        )
        if not tipo or tipo.get("Activo") == 0:
            return jsonify({"success": False, "message": "El tipo de tarea no existe o está inactivo"}), 400

        estados_validos = {'Pendiente', 'En progreso', 'Cumplida', 'Cancelada'}
        if estado_tarea not in estados_validos:
            return jsonify({"success": False, "message": "Estado de tarea inválido"}), 400

        insert_query = """
            INSERT INTO asignaciontarea (EstadoTarea, FechaAsignacion, IdGrupoVoluntario, IdTipoTarea, Activo)
            VALUES (%s, %s, %s, %s, 1);
        """
        new_id = execute_query(insert_query, (estado_tarea, fecha_obj, id_grupo, id_tipo_tarea))

        return jsonify({"success": True, "message": "Tarea asignada correctamente al grupo", "id": new_id}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
