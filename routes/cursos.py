# =============================================
# MÓDULO DE CURSOS - GESTIÓN ECLESIAL
# =============================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import execute_query
from utils import require_rol
from datetime import datetime

cursos_bp = Blueprint('cursos', __name__)

# =============================================
# ENDPOINTS DE CURSOS (tipocurso)
# =============================================

@cursos_bp.route('/', methods=['GET'])
@jwt_required()
def listar_cursos():
    """Listar todos los cursos activos"""
    try:
        query = """
            SELECT IdTipoCurso, Descripcion
            FROM tipocurso
            WHERE Activo = 1
            ORDER BY IdTipoCurso DESC;
        """
        cursos = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"cursos": cursos}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/<int:id_curso>', methods=['GET'])
@jwt_required()
def obtener_curso(id_curso):
    """Obtener curso por ID, con pasos y asignaciones"""
    try:
        curso = execute_query(
            "SELECT IdTipoCurso, Descripcion, Activo FROM tipocurso WHERE IdTipoCurso = %s;",
            (id_curso,), fetch_one=True
        )
        if not curso:
            return jsonify({"success": False, "message": "Curso no encontrado"}), 404

        pasos = execute_query(
            """
            SELECT id_paso, numero_paso, descripcion
            FROM curso_pasos
            WHERE id_tipo_curso = %s
            ORDER BY numero_paso ASC;
            """,
            (id_curso,), fetch_all=True
        )

        asignaciones = execute_query(
            """
            SELECT 
                gc.id_grupo_ayudantes_curso,
                gc.id_grupo_ayudantes,
                gc.id_tipo_curso,
                gc.fecha_asignacion,
                gc.Activo,
                (SELECT MAX(cp2.numero_paso)
                 FROM curso_pasos cp2
                 WHERE cp2.id_tipo_curso = gc.id_tipo_curso) AS total_pasos,
                (SELECT COUNT(*)
                 FROM progreso_curso pc
                 WHERE pc.id_grupo_ayudantes_curso = gc.id_grupo_ayudantes_curso) AS pasos_completados
            FROM grupo_ayudantes_curso gc
            WHERE gc.id_tipo_curso = %s;
            """,
            (id_curso,), fetch_all=True
        )

        curso["pasos"] = pasos
        curso["asignaciones"] = asignaciones

        return jsonify({"success": True, "data": {"curso": curso}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_curso():
    """Crear nuevo curso"""
    try:
        data = request.get_json()
        descripcion = data.get("descripcion")

        if not descripcion or descripcion.strip() == "":
            return jsonify({"success": False, "message": "La descripción del curso es obligatoria"}), 400

        existe = execute_query(
            "SELECT COUNT(*) AS cnt FROM tipocurso WHERE Descripcion = %s AND Activo = 1;",
            (descripcion,), fetch_one=True
        )
        if existe and existe["cnt"] > 0:
            return jsonify({"success": False, "message": "Ya existe un curso activo con esa descripción"}), 409

        execute_query("INSERT INTO tipocurso (Descripcion, Activo) VALUES (%s, 1);", (descripcion,))
        nuevo = execute_query("SELECT LAST_INSERT_ID() AS id;", fetch_one=True)
        return jsonify({"success": True, "message": "Curso creado exitosamente", "id": nuevo["id"]}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/<int:id_curso>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_curso(id_curso):
    """Actualizar descripción del curso"""
    try:
        data = request.get_json()
        descripcion = data.get("descripcion")

        if not descripcion:
            return jsonify({"success": False, "message": "La descripción es obligatoria"}), 400

        result = execute_query(
            "UPDATE tipocurso SET Descripcion = %s WHERE IdTipoCurso = %s;",
            (descripcion, id_curso)
        )
        return jsonify({"success": True, "message": "Curso actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/<int:id_curso>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_curso(id_curso):
    """Desactivar curso y asignaciones relacionadas"""
    try:
        execute_query("UPDATE tipocurso SET Activo = 0 WHERE IdTipoCurso = %s;", (id_curso,))
        execute_query("UPDATE grupo_ayudantes_curso SET Activo = 0 WHERE id_tipo_curso = %s;", (id_curso,))
        return jsonify({"success": True, "message": "Curso desactivado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/<int:id_curso>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_curso(id_curso):
    """Activar curso"""
    try:
        execute_query("UPDATE tipocurso SET Activo = 1 WHERE IdTipoCurso = %s;", (id_curso,))
        return jsonify({"success": True, "message": "Curso activado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# ENDPOINTS DE PASOS DE CURSO (curso_pasos)
# =============================================

@cursos_bp.route('/<int:id_curso>/pasos', methods=['GET'])
@jwt_required()
def listar_pasos(id_curso):
    try:
        query = """
            SELECT id_paso, numero_paso, descripcion
            FROM curso_pasos
            WHERE id_tipo_curso = %s
            ORDER BY numero_paso ASC;
        """
        pasos = execute_query(query, (id_curso,), fetch_all=True)
        return jsonify({"success": True, "data": {"pasos": pasos}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/<int:id_curso>/pasos', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_paso(id_curso):
    try:
        data = request.get_json()
        numero_paso = data.get("numero_paso")
        descripcion = data.get("descripcion")

        if not numero_paso or not descripcion:
            return jsonify({"success": False, "message": "Campos requeridos: numero_paso y descripcion"}), 400

        dup = execute_query(
            "SELECT COUNT(*) AS cnt FROM curso_pasos WHERE id_tipo_curso = %s AND numero_paso = %s;",
            (id_curso, numero_paso), fetch_one=True
        )
        if dup["cnt"] > 0:
            return jsonify({"success": False, "message": "Ya existe un paso con ese número"}), 409

        execute_query(
            "INSERT INTO curso_pasos (id_tipo_curso, numero_paso, descripcion) VALUES (%s, %s, %s);",
            (id_curso, numero_paso, descripcion)
        )
        return jsonify({"success": True, "message": "Paso creado exitosamente"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/<int:id_curso>/pasos/<int:id_paso>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_paso(id_curso, id_paso):
    try:
        data = request.get_json()
        numero_paso = data.get("numero_paso")
        descripcion = data.get("descripcion")

        if not numero_paso or not descripcion:
            return jsonify({"success": False, "message": "Campos requeridos"}), 400

        dup = execute_query(
            "SELECT COUNT(*) AS cnt FROM curso_pasos WHERE id_tipo_curso = %s AND numero_paso = %s AND id_paso != %s;",
            (id_curso, numero_paso, id_paso), fetch_one=True
        )
        if dup["cnt"] > 0:
            return jsonify({"success": False, "message": "El número de paso ya está en uso"}), 409

        execute_query(
            "UPDATE curso_pasos SET numero_paso = %s, descripcion = %s WHERE id_paso = %s AND id_tipo_curso = %s;",
            (numero_paso, descripcion, id_paso, id_curso)
        )
        return jsonify({"success": True, "message": "Paso actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/<int:id_curso>/pasos/<int:id_paso>', methods=['DELETE'])
@jwt_required()
@require_rol('Administrador')
def eliminar_paso(id_curso, id_paso):
    try:
        existe = execute_query(
            "SELECT COUNT(*) AS cnt FROM progreso_curso WHERE id_paso = %s;",
            (id_paso,), fetch_one=True
        )
        if existe["cnt"] > 0:
            return jsonify({"success": False, "message": "No se puede eliminar un paso con progreso registrado"}), 400

        execute_query("DELETE FROM curso_pasos WHERE id_paso = %s AND id_tipo_curso = %s;", (id_paso, id_curso))
        return jsonify({"success": True, "message": "Paso eliminado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# ENDPOINTS DE ASIGNACIÓN CURSO ↔ GRUPO
# =============================================

@cursos_bp.route('/asignaciones/grupo/<int:id_grupo>', methods=['GET'])
@jwt_required()
def listar_cursos_grupo(id_grupo):
    try:
        query = """
            SELECT 
              gc.id_grupo_ayudantes_curso,
              gc.id_tipo_curso,
              tc.Descripcion AS Curso,
              gc.fecha_asignacion,
              gc.Activo,
              (SELECT MAX(cp.numero_paso) FROM curso_pasos cp WHERE cp.id_tipo_curso = gc.id_tipo_curso) AS total_pasos,
              (SELECT COUNT(*) FROM progreso_curso pc WHERE pc.id_grupo_ayudantes_curso = gc.id_grupo_ayudantes_curso) AS pasos_completados
            FROM grupo_ayudantes_curso gc
            JOIN tipocurso tc ON gc.id_tipo_curso = tc.IdTipoCurso
            WHERE gc.id_grupo_ayudantes = %s
            ORDER BY gc.fecha_asignacion DESC;
        """
        asignaciones = execute_query(query, (id_grupo,), fetch_all=True)
        return jsonify({"success": True, "data": {"asignaciones": asignaciones}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/asignaciones/grupo/<int:id_grupo>', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def asignar_curso(id_grupo):
    try:
        data = request.get_json()
        id_tipo_curso = data.get("id_tipo_curso")

        if not id_tipo_curso:
            return jsonify({"success": False, "message": "Debe especificar el id_tipo_curso"}), 400

        grupo = execute_query(
            "SELECT IdGrupoAyudantes FROM grupoayudantes WHERE IdGrupoAyudantes = %s AND Activo = 1;",
            (id_grupo,), fetch_one=True
        )
        if not grupo:
            return jsonify({"success": False, "message": "El grupo no existe o está inactivo"}), 404

        duplicado = execute_query(
            "SELECT Activo FROM grupo_ayudantes_curso WHERE id_grupo_ayudantes = %s AND id_tipo_curso = %s;",
            (id_grupo, id_tipo_curso), fetch_one=True
        )
        if duplicado and duplicado.get("Activo") == 1:
            return jsonify({"success": False, "message": "El grupo ya tiene este curso asignado"}), 409

        execute_query(
            "INSERT INTO grupo_ayudantes_curso (id_grupo_ayudantes, id_tipo_curso, fecha_asignacion, Activo) VALUES (%s, %s, NOW(), 1);",
            (id_grupo, id_tipo_curso)
        )
        return jsonify({"success": True, "message": "Curso asignado al grupo exitosamente"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/asignaciones/grupo/<int:id_grupo>/curso/<int:id_tipo_curso>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_asignacion(id_grupo, id_tipo_curso):
    try:
        execute_query(
            "UPDATE grupo_ayudantes_curso SET Activo = 0 WHERE id_grupo_ayudantes = %s AND id_tipo_curso = %s;",
            (id_grupo, id_tipo_curso)
        )
        return jsonify({"success": True, "message": "Asignación desactivada correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/asignaciones/grupo/<int:id_grupo>/curso/<int:id_tipo_curso>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_asignacion(id_grupo, id_tipo_curso):
    try:
        execute_query(
            "UPDATE grupo_ayudantes_curso SET Activo = 1 WHERE id_grupo_ayudantes = %s AND id_tipo_curso = %s;",
            (id_grupo, id_tipo_curso)
        )
        return jsonify({"success": True, "message": "Asignación activada correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# ENDPOINTS DE PROGRESO DEL CURSO
# =============================================

@cursos_bp.route('/progreso/grupo/<int:id_grupo>/curso/<int:id_tipo_curso>', methods=['GET'])
@jwt_required()
def ver_progreso(id_grupo, id_tipo_curso):
    try:
        total = execute_query(
            "SELECT COUNT(*) AS total FROM curso_pasos WHERE id_tipo_curso = %s;",
            (id_tipo_curso,), fetch_one=True
        )["total"]

        asignacion = execute_query(
            "SELECT id_grupo_ayudantes_curso FROM grupo_ayudantes_curso WHERE id_grupo_ayudantes = %s AND id_tipo_curso = %s AND Activo = 1;",
            (id_grupo, id_tipo_curso), fetch_one=True
        )
        if not asignacion:
            return jsonify({"success": False, "message": "No existe asignación activa"}), 404

        completados = execute_query(
            "SELECT COUNT(*) AS completados FROM progreso_curso WHERE id_grupo_ayudantes_curso = %s;",
            (asignacion["id_grupo_ayudantes_curso"],), fetch_one=True
        )["completados"]

        aprobado = completados >= total
        return jsonify({
            "success": True,
            "data": {"total_pasos": total, "completados": completados, "aprobado": aprobado}
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/progreso/grupo/<int:id_grupo>/curso/<int:id_tipo_curso>/paso/<int:id_paso>', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def completar_paso(id_grupo, id_tipo_curso, id_paso):
    try:
        asignacion = execute_query(
            "SELECT id_grupo_ayudantes_curso FROM grupo_ayudantes_curso WHERE id_grupo_ayudantes = %s AND id_tipo_curso = %s AND Activo = 1;",
            (id_grupo, id_tipo_curso), fetch_one=True
        )
        if not asignacion:
            return jsonify({"success": False, "message": "Asignación no encontrada"}), 404

        id_asignacion = asignacion["id_grupo_ayudantes_curso"]

        ultimo = execute_query(
            """
            SELECT MAX(cp.numero_paso) AS ultimo_paso
            FROM progreso_curso pc
            JOIN curso_pasos cp ON pc.id_paso = cp.id_paso
            WHERE pc.id_grupo_ayudantes_curso = %s;
            """,
            (id_asignacion,), fetch_one=True
        )["ultimo_paso"] or 0

        paso = execute_query(
            "SELECT id_paso, numero_paso FROM curso_pasos WHERE id_paso = %s AND id_tipo_curso = %s;",
            (id_paso, id_tipo_curso), fetch_one=True
        )
        if not paso:
            return jsonify({"success": False, "message": "Paso no pertenece a este curso"}), 400

        if paso["numero_paso"] != ultimo + 1:
            return jsonify({"success": False, "message": "Debe completar los pasos en orden secuencial"}), 400

        execute_query(
            "INSERT INTO progreso_curso (id_grupo_ayudantes_curso, id_paso, fecha_completado) VALUES (%s, %s, NOW());",
            (id_asignacion, id_paso))
        return jsonify({"success": True, "message": "Paso marcado como completado"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@cursos_bp.route('/progreso/grupo/<int:id_grupo>/curso/<int:id_tipo_curso>/paso/<int:id_paso>', methods=['DELETE'])
@jwt_required()
@require_rol('Administrador')
def revertir_paso(id_grupo, id_tipo_curso, id_paso):
    """Revertir (eliminar) el último paso completado — solo permite LIFO"""
    try:
        asignacion = execute_query(
            "SELECT id_grupo_ayudantes_curso FROM grupo_ayudantes_curso "
            "WHERE id_grupo_ayudantes = %s AND id_tipo_curso = %s AND Activo = 1;",
            (id_grupo, id_tipo_curso), fetch_one=True
        )
        if not asignacion:
            return jsonify({"success": False, "message": "Asignación no encontrada"}), 404

        id_asignacion = asignacion["id_grupo_ayudantes_curso"]

        ultimo = execute_query(
            """
            SELECT pc.id_progreso, cp.id_paso, cp.numero_paso
            FROM progreso_curso pc
            JOIN curso_pasos cp ON cp.id_paso = pc.id_paso
            WHERE pc.id_grupo_ayudantes_curso = %s
            ORDER BY cp.numero_paso DESC
            LIMIT 1;
            """,
            (id_asignacion,), fetch_one=True
        )
        if not ultimo:
            return jsonify({"success": False, "message": "No hay pasos completados para revertir"}), 404

        if ultimo["id_paso"] != id_paso:
            return jsonify({"success": False, "message": "Solo puede revertirse el último paso completado"}, ), 400

        # Borrar el registro de progreso específico (usamos id_progreso para evitar ambigüedades)
        execute_query(
            "DELETE FROM progreso_curso WHERE id_progreso = %s LIMIT 1;",
            (ultimo["id_progreso"],)
        )
        return jsonify({"success": True, "message": "Paso revertido correctamente"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# FIN DEL MÓDULO CURSOS
# =============================================
