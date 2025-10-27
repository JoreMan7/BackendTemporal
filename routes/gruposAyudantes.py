"""
Rutas para gestión de grupos ayudantes
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query
from utils import require_rol
from datetime import datetime

grupos_bp = Blueprint('grupos', __name__)

# =============================================
# ENDPOINTS PRINCIPALES DE GRUPOS
# =============================================

# LISTAR TODOS LOS GRUPOS
@grupos_bp.route('/', methods=['GET'])
@jwt_required()
def listar_grupos():
    try:
        query = """
            SELECT 
                g.IdGrupoAyudantes,
                g.Nombre AS Grupo,
                g.IdHabitanteLider,
                h.Nombre AS NombreLider,
                h.Apellido AS ApellidoLider,
                h.NumeroDocumento AS DocumentoLider,
                h.Telefono AS TelefonoLider,
                g.Activo,
                COUNT(DISTINCT m.id_miembro) AS CantidadMiembros
            FROM grupoayudantes g
            JOIN habitantes h ON g.IdHabitanteLider = h.IdHabitante
            LEFT JOIN miembro_grupo_ayudantes m 
                   ON g.IdGrupoAyudantes = m.id_grupo_ayudantes AND m.Activo = 1
            WHERE g.Activo = 1
            GROUP BY g.IdGrupoAyudantes, g.Nombre, 
                     g.IdHabitanteLider, h.Nombre, h.Apellido, 
                     h.NumeroDocumento, h.Telefono, g.Activo
            ORDER BY g.IdGrupoAyudantes DESC
        """
        grupos = execute_query(query)
        return jsonify({"success": True, "grupos": grupos}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@grupos_bp.route('/<int:id>/miembros/<int:id_habitante>', methods=['GET'])
@jwt_required()
def obtener_miembro(id, id_habitante):
    """
    Devuelve la información detallada de un miembro específico de un grupo.
    """
    try:
        query = """
            SELECT 
                m.id_miembro,
                m.id_habitante,
                h.Nombre,
                h.Apellido,
                h.NumeroDocumento,
                h.Telefono,
                h.CorreoElectronico,
                h.Direccion,
                m.Activo
            FROM miembro_grupo_ayudantes m
            JOIN habitantes h ON m.id_habitante = h.IdHabitante
            WHERE m.id_grupo_ayudantes = %s AND m.id_habitante = %s
        """
        miembro = execute_query(query, (id, id_habitante), fetch_one=True)

        if not miembro:
            return jsonify({
                'success': False,
                'message': 'Miembro no encontrado o no pertenece a este grupo.'
            }), 404

        return jsonify({
            'success': True,
            'miembro': miembro
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Error al obtener miembro: {str(e)}"
        }), 500

# OBTENER GRUPO POR ID
@grupos_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_grupo(id):
    try:
        # Datos básicos del grupo
        query_grupo = """
            SELECT 
                g.IdGrupoAyudantes,
                g.Nombre,
                g.IdHabitanteLider,
                h.Nombre AS NombreLider,
                h.Apellido AS ApellidoLider,
                h.NumeroDocumento AS DocumentoLider,
                h.Telefono AS TelefonoLider,
                g.Activo
            FROM grupoayudantes g
            JOIN habitantes h ON g.IdHabitanteLider = h.IdHabitante
            WHERE g.IdGrupoAyudantes = %s AND g.Activo = 1
        """
        grupo = execute_query(query_grupo, (id,), fetch_one=True)
        if not grupo:
            return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404

        # Miembros
        query_miembros = """
            SELECT 
                m.id_miembro,
                m.id_habitante,
                h.Nombre,
                h.Apellido,
                h.NumeroDocumento,
                h.Telefono,
                h.CorreoElectronico
            FROM miembro_grupo_ayudantes m
            JOIN habitantes h ON m.id_habitante = h.IdHabitante
            WHERE m.id_grupo_ayudantes = %s AND m.Activo = 1
        """
        miembros = execute_query(query_miembros, (id,))

        # Cursos
        query_cursos = """
            SELECT 
                gc.id_grupo_ayudantes_curso,
                gc.id_tipo_curso,
                tc.Descripcion AS Curso,
                gc.fecha_asignacion,
                (SELECT MAX(cp.numero_paso) 
                 FROM curso_pasos cp 
                 WHERE cp.id_tipo_curso = gc.id_tipo_curso) AS total_pasos,
                (SELECT COUNT(*) 
                 FROM progreso_curso pc 
                 WHERE pc.id_grupo_ayudantes_curso = gc.id_grupo_ayudantes_curso) AS pasos_completados
            FROM grupo_ayudantes_curso gc
            JOIN tipocurso tc ON gc.id_tipo_curso = tc.IdTipoCurso
            WHERE gc.id_grupo_ayudantes = %s
        """
        cursos = execute_query(query_cursos, (id,))

        # Tareas
        query_tareas = """
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
        """
        tareas = execute_query(query_tareas, (id,))

        grupo_data = {
            "id": grupo['IdGrupoAyudantes'],
            "nombre": grupo['Nombre'],
            "lider": {
                "id": grupo['IdHabitanteLider'],
                "nombre": grupo['NombreLider'],
                "apellido": grupo['ApellidoLider'],
                "documento": grupo['DocumentoLider'],
                "telefono": grupo['TelefonoLider']
            },
            "miembros": miembros,
            "cursos": cursos,
            "tareas": tareas
        }

        return jsonify({'success': True, 'grupo': grupo_data}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al obtener grupo: {str(e)}"}), 500


# CREAR GRUPO (Solo Administrador)
@grupos_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_grupo():
    try:
        data = request.get_json()
        required_fields = ['nombre', 'id_habitante_lider']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'El campo {field} es requerido'}), 400

        # Validar líder
        query_lider = "SELECT IdHabitante FROM habitantes WHERE IdHabitante = %s AND Activo = 1"
        lider = execute_query(query_lider, (data['id_habitante_lider'],), fetch_one=True)
        if not lider:
            return jsonify({'success': False, 'message': 'El líder no existe o está inactivo'}), 400
        # Validar si el líder ya pertenece a otro grupo activo
        query_check_lider = """
            SELECT IdGrupoAyudantes, Nombre 
            FROM grupoayudantes 
            WHERE IdHabitanteLider = %s AND Activo = 1
        """
        lider_en_otro = execute_query(query_check_lider, (data['id_habitante_lider'],), fetch_one=True)
        if lider_en_otro:
            return jsonify({'success': False, 'message': f'El líder ya pertenece al grupo "{lider_en_otro["Nombre"]}".'}), 400

        # Crear grupo
        query = """
            INSERT INTO grupoayudantes (Nombre, IdHabitanteLider, Activo)
            VALUES (%s, %s, 1)
        """
        grupo_id = execute_query(query, (data['nombre'], data['id_habitante_lider']))

        # Agregar líder como miembro
        query_miembro = """
            INSERT INTO miembro_grupo_ayudantes (id_grupo_ayudantes, id_habitante, Activo)
            VALUES (%s, %s, 1)
        """
        execute_query(query_miembro, (grupo_id, data['id_habitante_lider']))

        return jsonify({'success': True, 'message': 'Grupo creado exitosamente', 'id': grupo_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al crear grupo: {str(e)}"}), 500


# ACTUALIZAR GRUPO (Solo Administrador)
@grupos_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_grupo(id):
    try:
        data = request.get_json()
        query = """
            UPDATE grupoayudantes
            SET Nombre = %s, IdHabitanteLider = %s
            WHERE IdGrupoAyudantes = %s AND Activo = 1
        """
        updated = execute_query(query, (data.get('nombre'), data.get('id_habitante_lider'), id))
        if updated:
            return jsonify({'success': True, 'message': 'Grupo actualizado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Grupo no encontrado o no actualizado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al actualizar grupo: {str(e)}"}), 500


# DESACTIVAR GRUPO (Solo Administrador)
@grupos_bp.route('/<int:id>/desactivar/', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_grupo(id):
    try:
        rows = execute_query("UPDATE grupoayudantes SET Activo = 0 WHERE IdGrupoAyudantes = %s", (id,))
        if rows is not None:
            execute_query("UPDATE miembro_grupo_ayudantes SET Activo = 0 WHERE id_grupo_ayudantes = %s", (id,))
            return jsonify({'success': True, 'message': 'Grupo desactivado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al desactivar grupo: {str(e)}"}), 500

# ACTIVAR GRUPO (Solo Administrador)
@grupos_bp.route('/<int:id>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_grupo(id):
    try:
        rows = execute_query("UPDATE grupoayudantes SET Activo = 1 WHERE IdGrupoAyudantes = %s", (id,))
        if rows is not None:
            execute_query("UPDATE miembro_grupo_ayudantes SET Activo = 1 WHERE id_grupo_ayudantes = %s", (id,))
            return jsonify({'success': True, 'message': 'Grupo activado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Grupo no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al activar grupo: {str(e)}"}), 500

# =============================================
# ENDPOINTS DE MIEMBROS
# =============================================

@grupos_bp.route('/<int:id>/miembros', methods=['GET'])
@jwt_required()
def listar_miembros(id):
    try:
        query = """
            SELECT 
                m.id_miembro,
                m.id_habitante,
                h.Nombre,
                h.Apellido,
                h.NumeroDocumento,
                h.Telefono,
                h.CorreoElectronico,
                h.Direccion
            FROM miembro_grupo_ayudantes m
            JOIN habitantes h ON m.id_habitante = h.IdHabitante
            WHERE m.id_grupo_ayudantes = %s AND m.Activo = 1
            ORDER BY h.Nombre, h.Apellido
        """
        miembros = execute_query(query, (id,))
        return jsonify({"success": True, "miembros": miembros}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@grupos_bp.route('/<int:id>/miembros', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def agregar_miembro(id):
    try:
        data = request.get_json()
        id_habitante = data.get('id_habitante')
        if not id_habitante:
            return jsonify({'success': False, 'message': 'El id_habitante es requerido'}), 400

        query = """
            INSERT INTO miembro_grupo_ayudantes (id_grupo_ayudantes, id_habitante, Activo)
            VALUES (%s, %s, 1)
        """
        miembro_id = execute_query(query, (id, id_habitante))
        return jsonify({'success': True, 'message': 'Miembro agregado exitosamente', 'id': miembro_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al agregar miembro: {str(e)}"}), 500


@grupos_bp.route('/<int:id>/miembros/<int:id_miembro>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_miembro(id, id_miembro):
    try:
        query = "UPDATE miembro_grupo_ayudantes SET Activo = 0 WHERE id_habitante = %s AND id_grupo_ayudantes = %s"
        updated = execute_query(query, (id_miembro, id))
        if updated:
            return jsonify({'success': True, 'message': 'Miembro desactivado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Miembro no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al desactivar miembro: {str(e)}"}), 500


# =============================================
# ENDPOINTS DE CURSOS
# =============================================

@grupos_bp.route('/<int:id>/cursos', methods=['GET'])
@jwt_required()
def listar_cursos(id):
    try:
        query = """
            SELECT 
                gc.id_grupo_ayudantes_curso,
                gc.id_tipo_curso,
                tc.Descripcion AS Curso,
                gc.fecha_asignacion
            FROM grupo_ayudantes_curso gc
            JOIN tipocurso tc ON gc.id_tipo_curso = tc.IdTipoCurso
            WHERE gc.id_grupo_ayudantes = %s
            ORDER BY gc.fecha_asignacion DESC
        """
        cursos = execute_query(query, (id,))
        return jsonify({"success": True, "cursos": cursos}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@grupos_bp.route('/<int:id>/cursos', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def asignar_curso(id):
    try:
        data = request.get_json()
        id_tipo_curso = data.get('id_tipo_curso')
        if not id_tipo_curso:
            return jsonify({'success': False, 'message': 'El id_tipo_curso es requerido'}), 400

        query = """
            INSERT INTO grupo_ayudantes_curso (id_grupo_ayudantes, id_tipo_curso, fecha_asignacion)
            VALUES (%s, %s, %s)
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        curso_id = execute_query(query, (id, id_tipo_curso, now))
        return jsonify({'success': True, 'message': 'Curso asignado exitosamente', 'id': curso_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al asignar curso: {str(e)}"}), 500


# =============================================
# ENDPOINTS DE TAREAS
# =============================================

@grupos_bp.route('/<int:id>/tareas', methods=['GET'])
@jwt_required()
def listar_tareas(id):
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
            ORDER BY at.FechaAsignacion DESC
        """
        tareas = execute_query(query, (id,))
        return jsonify({"success": True, "tareas": tareas}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@grupos_bp.route('/<int:id>/tareas', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def asignar_tarea(id):
    try:
        data = request.get_json()
        id_tipotarea = data.get('id_tipotarea')
        if not id_tipotarea:
            return jsonify({'success': False, 'message': 'El id_tipotarea es requerido'}), 400

        now = datetime.now().strftime('%Y-%m-%d')
        query = """
            INSERT INTO asignaciontarea (
                IdGrupoVoluntario, IdTipoTarea, FechaAsignacion, EstadoTarea, Activo
            ) VALUES (%s, %s, %s, %s, 1)
        """
        tarea_id = execute_query(query, (id, id_tipotarea, now, 'Pendiente'))
        return jsonify({'success': True, 'message': 'Tarea asignada exitosamente', 'id': tarea_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al asignar tarea: {str(e)}"}), 500


@grupos_bp.route('/<int:id>/tareas/<int:id_tarea>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_tarea(id, id_tarea):
    try:
        data = request.get_json()
        estado_tarea = data.get('estado_tarea')
        if estado_tarea not in ['Pendiente', 'En progreso', 'Cumplida', 'Cancelada']:
            return jsonify({'success': False, 'message': 'Estado de tarea inválido'}), 400

        query = """
            UPDATE asignaciontarea 
            SET EstadoTarea = %s 
            WHERE IdAsignacionTarea = %s AND IdGrupoVoluntario = %s AND Activo = 1
        """
        updated = execute_query(query, (estado_tarea, id_tarea, id))
        if updated:
            return jsonify({'success': True, 'message': 'Estado de tarea actualizado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Tarea no encontrada'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al actualizar tarea: {str(e)}"}), 500

# AVANZAR EN CURSO
@grupos_bp.route('/<int:id>/cursos/<int:id_curso>/avanzar', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def avanzar_curso(id, id_curso):
    """
    Avanza al siguiente paso secuencial en un curso asignado a un grupo.
    Registra el avance en la tabla progreso_curso.
    """
    try:
        from flask_jwt_extended import get_jwt_identity
        usuario_id = get_jwt_identity()

        # 1️⃣ Verificar que el curso esté asignado al grupo
        query_asignacion = """
            SELECT id_grupo_ayudantes_curso, id_tipo_curso
            FROM grupo_ayudantes_curso
            WHERE id_grupo_ayudantes = %s AND id_grupo_ayudantes_curso = %s
        """
        asignacion = execute_query(query_asignacion, (id, id_curso), fetch_one=True)
        if not asignacion:
            return jsonify({'success': False, 'message': 'El curso no está asignado a este grupo'}), 404

        id_grupo_curso = asignacion['id_grupo_ayudantes_curso']
        id_tipo_curso = asignacion['id_tipo_curso']

        # 2️⃣ Obtener el último paso completado
        query_ultimo_paso = """
            SELECT MAX(cp.numero_paso) AS ultimo_paso
            FROM progreso_curso pc
            JOIN curso_pasos cp ON pc.id_paso = cp.id_paso
            WHERE pc.id_grupo_ayudantes_curso = %s
        """
        ultimo = execute_query(query_ultimo_paso, (id_grupo_curso,), fetch_one=True)
        paso_actual = ultimo['ultimo_paso'] or 0  # si no hay progreso, inicia en 0

        # 3️⃣ Verificar el siguiente paso disponible
        query_siguiente_paso = """
            SELECT id_paso, numero_paso, descripcion
            FROM curso_pasos
            WHERE id_tipo_curso = %s AND numero_paso = %s
        """
        siguiente = execute_query(query_siguiente_paso, (id_tipo_curso, paso_actual + 1), fetch_one=True)
        if not siguiente:
            return jsonify({'success': True, 'message': '🎓 Curso completado! No hay más pasos por avanzar.'}), 200

        # 4️⃣ Registrar el avance
        query_insert = """
            INSERT INTO progreso_curso (id_grupo_ayudantes_curso, id_paso, completado_por)
            VALUES (%s, %s, %s)
        """
        execute_query(query_insert, (id_grupo_curso, siguiente['id_paso'], usuario_id))

        return jsonify({
            'success': True,
            'message': f"✅ Avanzaste al paso {siguiente['numero_paso']}: {siguiente['descripcion']}"
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al avanzar curso: {str(e)}"}), 500
    

# AVANZAR PASO INDIVIDUAL EN CURSO
@grupos_bp.route('/<int:id>/cursos/<int:id_curso>/avanzar/miembro/<int:id_habitante>', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def avanzar_curso_miembro(id, id_curso, id_habitante):
    """
    Registra el avance individual de un miembro dentro de un curso asignado al grupo.
    No afecta el progreso grupal directamente.
    """
    try:
        from flask_jwt_extended import get_jwt_identity
        usuario_id = get_jwt_identity()

        # 1️⃣ Verificar que el habitante pertenezca al grupo
        query_miembro = """
            SELECT 1 FROM miembro_grupo_ayudantes
            WHERE id_grupo_ayudantes = %s AND id_habitante = %s AND Activo = 1
        """
        miembro = execute_query(query_miembro, (id, id_habitante), fetch_one=True)
        if not miembro:
            return jsonify({'success': False, 'message': 'El habitante no pertenece al grupo o está inactivo'}), 400

        # 2️⃣ Verificar el curso asignado al grupo
        query_asignacion = """
            SELECT id_grupo_ayudantes_curso, id_tipo_curso
            FROM grupo_ayudantes_curso
            WHERE id_grupo_ayudantes = %s AND id_grupo_ayudantes_curso = %s
        """
        asignacion = execute_query(query_asignacion, (id, id_curso), fetch_one=True)
        if not asignacion:
            return jsonify({'success': False, 'message': 'El curso no está asignado al grupo'}), 404

        id_grupo_curso = asignacion['id_grupo_ayudantes_curso']
        id_tipo_curso = asignacion['id_tipo_curso']

        # 3️⃣ Obtener el último paso completado por ese miembro
        query_ultimo = """
            SELECT MAX(cp.numero_paso) AS ultimo_paso
            FROM progreso_individual_curso pic
            JOIN curso_pasos cp ON pic.id_paso = cp.id_paso
            WHERE pic.id_grupo_ayudantes_curso = %s AND pic.id_habitante = %s
        """
        ultimo = execute_query(query_ultimo, (id_grupo_curso, id_habitante), fetch_one=True)
        paso_actual = ultimo['ultimo_paso'] or 0

        # 4️⃣ Buscar siguiente paso disponible
        query_siguiente = """
            SELECT id_paso, numero_paso, descripcion
            FROM curso_pasos
            WHERE id_tipo_curso = %s AND numero_paso = %s
        """
        siguiente = execute_query(query_siguiente, (id_tipo_curso, paso_actual + 1), fetch_one=True)
        if not siguiente:
            return jsonify({'success': True, 'message': '🎓 El miembro ya completó todos los pasos del curso'}), 200

        # 5️⃣ Registrar el avance individual
        query_insert = """
            INSERT INTO progreso_individual_curso (id_grupo_ayudantes_curso, id_habitante, id_paso, completado_por)
            VALUES (%s, %s, %s, %s)
        """
        execute_query(query_insert, (id_grupo_curso, id_habitante, siguiente['id_paso'], usuario_id))

        return jsonify({
            'success': True,
            'message': f"✅ El miembro avanzó al paso {siguiente['numero_paso']}: {siguiente['descripcion']}"
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al avanzar miembro: {str(e)}"}), 500

@grupos_bp.route('/<int:id>/cursos/<int:id_curso>/progreso-miembros', methods=['GET'])
@jwt_required()
def ver_progreso_miembros(id, id_curso):
    """
    Devuelve el progreso de cada miembro dentro de un curso específico.
    """
    try:
        query = """
            SELECT 
                h.IdHabitante,
                CONCAT(h.Nombre, ' ', h.Apellido) AS NombreCompleto,
                COUNT(DISTINCT pic.id_paso) AS pasos_realizados,
                (SELECT COUNT(*) FROM curso_pasos WHERE id_tipo_curso = gac.id_tipo_curso) AS total_pasos,
                ROUND(COUNT(DISTINCT pic.id_paso) / 
                      (SELECT COUNT(*) FROM curso_pasos WHERE id_tipo_curso = gac.id_tipo_curso) * 100, 0) AS progreso
            FROM miembro_grupo_ayudantes m
            JOIN habitantes h ON m.id_habitante = h.IdHabitante
            JOIN grupo_ayudantes_curso gac ON gac.id_grupo_ayudantes = m.id_grupo_ayudantes
            LEFT JOIN progreso_individual_curso pic 
                   ON pic.id_habitante = m.id_habitante 
                   AND pic.id_grupo_ayudantes_curso = gac.id_grupo_ayudantes_curso
            WHERE m.id_grupo_ayudantes = %s AND gac.id_grupo_ayudantes_curso = %s
            GROUP BY h.IdHabitante, NombreCompleto, gac.id_tipo_curso
            ORDER BY NombreCompleto
        """
        progreso = execute_query(query, (id, id_curso))
        return jsonify({'success': True, 'progreso_miembros': progreso}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@grupos_bp.route('/buscar_lider', methods=['GET'])
@jwt_required()
def buscar_lider():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'success': True, 'habitantes': []}), 200
    query = """
        SELECT IdHabitante, Nombre, Apellido, NumeroDocumento, Telefono
        FROM habitantes
        WHERE Activo = 1 AND (
            LOWER(Nombre) LIKE %s OR
            LOWER(Apellido) LIKE %s OR
            NumeroDocumento LIKE %s
        )
        LIMIT 100
    """
    like = f"%{q.lower()}%"
    results = execute_query(query, (like, like, like))
    return jsonify({'success': True, 'habitantes': results}), 200