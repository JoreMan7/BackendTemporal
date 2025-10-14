"""
Rutas para gestión de habitantes
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query
from datetime import datetime
from utils import require_rol

habitantes_bp = Blueprint('habitantes', __name__)

#  LISTAR TODOS LOS HABITANTES
@habitantes_bp.route('/', methods=['GET'])
@jwt_required()
def listar_habitantes():
    try:
        query = """
            SELECT 
                h.IdHabitante,
                h.Nombre,
                h.Apellido,
                h.IdTipoDocumento,
                td.Descripcion AS TipoDocumento,
                h.NumeroDocumento,
                h.FechaNacimiento,
                h.Hijos,
                h.IdEstadoCivil,
                ec.Nombre AS EstadoCivil,
                h.IdSexo,
                s.Nombre AS Sexo,
                h.IdReligion,
                r.Nombre AS Religion,
                h.IdTipoPoblacion,
                tp.Nombre AS TipoPoblacion,
                tp.Descripcion AS DescripcionPoblacion,
                h.IdTipoSacramento,
                ts.Descripcion AS TipoSacramento,
                ts.Costo AS CostoSacramento,
                h.DiscapacidadParaAsistir,
                h.TieneImpedimentoSalud,
                h.MotivoImpedimentoSalud,
                h.IdGrupoFamiliar,
                h.IdSector,
                sec.Descripcion AS Sector,
                h.Direccion,
                h.Telefono,
                h.CorreoElectronico,
                h.Activo,
                h.FechaRegistro
            FROM habitantes h
            LEFT JOIN tipodocumento td     ON h.IdTipoDocumento = td.IdTipoDocumento
            LEFT JOIN estados_civiles ec   ON h.IdEstadoCivil = ec.IdEstadoCivil
            LEFT JOIN sexos s              ON h.IdSexo = s.IdSexo
            LEFT JOIN religiones r         ON h.IdReligion = r.IdReligion
            LEFT JOIN tipopoblacion tp     ON h.IdTipoPoblacion = tp.IdTipoPoblacion
            LEFT JOIN tiposacramentos ts   ON h.IdTipoSacramento = ts.IdSacramento
            LEFT JOIN sector sec           ON h.IdSector = sec.IdSector
            WHERE h.Activo = 1
            ORDER BY h.IdHabitante DESC
            LIMIT 1000
        """
        habitantes = execute_query(query)
        #print(habitantes)
        return jsonify({
            "success": True,
            "habitantes": habitantes
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


#  OBTENER HABITANTE POR ID
@habitantes_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_habitante(id):
    try:
        query = """
            SELECT 
                h.IdHabitante,
                h.Nombre,
                h.Apellido,
                h.IdTipoDocumento,
                td.Descripcion AS TipoDocumento,
                h.NumeroDocumento,
                h.FechaNacimiento,
                h.Hijos,
                h.IdEstadoCivil,
                ec.Nombre AS EstadoCivil,
                h.IdSexo,
                s.Nombre AS Sexo,
                h.IdReligion,
                r.Nombre AS Religion,
                h.IdTipoPoblacion,
                tp.Nombre AS TipoPoblacion,
                tp.Descripcion AS DescripcionPoblacion,
                h.IdTipoSacramento,
                ts.Descripcion AS TipoSacramento,
                ts.Costo AS CostoSacramento,
                h.DiscapacidadParaAsistir,
                h.TieneImpedimentoSalud,
                h.MotivoImpedimentoSalud,
                h.IdGrupoFamiliar,
                h.IdSector,
                sec.Descripcion AS Sector,
                h.Direccion,
                h.Telefono,
                h.CorreoElectronico,
                h.FechaRegistro
            FROM habitantes h
            LEFT JOIN tipodocumento td     ON h.IdTipoDocumento = td.IdTipoDocumento
            LEFT JOIN estados_civiles ec   ON h.IdEstadoCivil = ec.IdEstadoCivil
            LEFT JOIN sexos s              ON h.IdSexo = s.IdSexo
            LEFT JOIN religiones r         ON h.IdReligion = r.IdReligion
            LEFT JOIN tipopoblacion tp     ON h.IdTipoPoblacion = tp.IdTipoPoblacion
            LEFT JOIN tiposacramentos ts   ON h.IdTipoSacramento = ts.IdSacramento
            LEFT JOIN sector sec           ON h.IdSector = sec.IdSector
            WHERE h.IdHabitante = %s AND h.Activo = 1
        """
        habitante = execute_query(query, (id,), fetch_one=True)

        if not habitante:
            return jsonify({'success': False, 'message': 'Habitante no encontrado'}), 404

        return jsonify({'success': True, 'habitante': habitante}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al obtener habitante: {str(e)}"}), 500


#  CREAR HABITANTE
@habitantes_bp.route('/', methods=['POST'])
@jwt_required()
def crear_habitante():
    try:
        data = request.get_json()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query = """
            INSERT INTO habitantes (
                Nombre, Apellido, IdTipoDocumento, NumeroDocumento,
                FechaNacimiento, Hijos, IdSexo, IdReligion, IdEstadoCivil,
                IdTipoPoblacion, IdTipoSacramento, IdSector,
                Direccion, Telefono, CorreoElectronico,
                DiscapacidadParaAsistir, TieneImpedimentoSalud, MotivoImpedimentoSalud,
                IdGrupoFamiliar, FechaRegistro, Activo
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)
        """
        params = (
            data.get('nombre'),
            data.get('apellido'),
            data.get('id_tipo_documento'),
            data.get('numero_documento'),
            data.get('fecha_nacimiento'),
            data.get('hijos', 0),
            data.get('id_sexo'),
            data.get('id_religion'),
            data.get('id_estado_civil'),
            data.get('id_tipo_poblacion'),
            data.get('id_tipo_sacramento'),
            data.get('id_sector'),
            data.get('direccion'),
            data.get('telefono'),
            data.get('correo_electronico'),
            data.get('discapacidad_para_asistir', 'Ninguna'),
            data.get('tiene_impedimento_salud', False),
            data.get('motivo_impedimento_salud'),
            data.get('id_grupo_familiar'),
            now
        )
        habitante_id = execute_query(query, params)

        return jsonify({'success': True, 'message': 'Habitante creado exitosamente', 'id': habitante_id}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al crear habitante: {str(e)}"}), 500


#  ACTUALIZAR HABITANTE
@habitantes_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_habitante(id):
    try:
        data = request.get_json()
        query = """
            UPDATE habitantes
            SET Nombre=%s, Apellido=%s, NumeroDocumento=%s, CorreoElectronico=%s,
                Telefono=%s, Direccion=%s, Hijos=%s,
                IdSexo=%s, IdReligion=%s, IdEstadoCivil=%s,
                IdTipoPoblacion=%s, IdTipoSacramento=%s, IdSector=%s,
                DiscapacidadParaAsistir=%s, TieneImpedimentoSalud=%s, MotivoImpedimentoSalud=%s,
                FechaNacimiento=%s
            WHERE IdHabitante=%s AND Activo=1
        """
        params = (
            data.get('nombre'),
            data.get('apellido'),
            data.get('numero_documento'),
            data.get('correo_electronico'),
            data.get('telefono'),
            data.get('direccion'),
            data.get('hijos', 0),
            data.get('id_sexo'),
            data.get('id_religion'),
            data.get('id_estado_civil'),
            data.get('id_tipo_poblacion'),
            data.get('id_tipo_sacramento'),
            data.get('id_sector'),
            data.get('discapacidad_para_asistir'),
            data.get('tiene_impedimento_salud'),
            data.get('motivo_impedimento_salud'),
            data.get('fecha_nacimiento'),
            id
        )
        updated = execute_query(query, params)
        if updated:
            return jsonify({'success': True, 'message': 'Habitante actualizado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Habitante no encontrado o no actualizado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al actualizar habitante: {str(e)}"}), 500


#  DESACTIVAR HABITANTE (soft delete)
@habitantes_bp.route('/<int:id>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_habitante(id):
    try:
        query = "UPDATE habitantes SET Activo=0 WHERE IdHabitante=%s"
        updated = execute_query(query, (id,))
        if updated:
            return jsonify({'success': True, 'message': 'Habitante desactivado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Habitante no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al desactivar habitante: {str(e)}"}), 500

@habitantes_bp.route('/buscar_grupo', methods=['GET'])
@jwt_required()
def buscar_grupo_por_miembro():
    q = request.args.get('q', '').strip()
    query = """
        SELECT h.IdHabitante, h.Nombre, h.Apellido, h.NumeroDocumento, g.Nombre AS Grupo
        FROM habitantes h
        LEFT JOIN miembro_grupo_ayudantes m ON h.IdHabitante = m.id_habitante
        LEFT JOIN grupoayudantes g ON g.IdGrupoAyudantes = m.id_grupo_ayudantes
        WHERE LOWER(h.Nombre) LIKE %s OR LOWER(h.Apellido) LIKE %s OR h.NumeroDocumento LIKE %s
        LIMIT 100
    """
    like = f"%{q.lower()}%"
    result = execute_query(query, (like, like, like))
    return jsonify({'success': True, 'resultados': result}), 200
