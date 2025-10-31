from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime
from utils import require_rol,ValidacionDatos
from database import execute_query


habitantes_bp = Blueprint('habitantes', __name__)

def _asignar_jefe_si_vacio(id_grupo, id_habitante):
    execute_query("""
        UPDATE grupofamiliar
        SET IdJefeFamilia = %s
        WHERE IdGrupoFamiliar = %s
          AND (IdJefeFamilia IS NULL OR IdJefeFamilia = 0)
    """, (id_habitante, id_grupo))


# LISTAR TODOS LOS HABITANTES
# LISTAR TODOS LOS HABITANTES
@habitantes_bp.route('/', methods=['GET'])
@jwt_required()
def listar_habitantes():
    try:
        # En listar_habitantes() - Asegúrate que tenga este JOIN y columna:
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
        h.DiscapacidadParaAsistir,
        h.TieneImpedimentoSalud,
        h.MotivoImpedimentoSalud,
        h.IdGrupoFamiliar,
        COALESCE(gf.Descripcion, 'Sin familia') AS FamiliaDescripcion,  -- ← ESTA COLUMNA
        h.IdSector,
        sec.Descripcion AS Sector,
        h.Direccion,
        h.Telefono,
        h.CorreoElectronico,
        h.Activo,
        h.FechaRegistro,
        COALESCE(GROUP_CONCAT(DISTINCT ts.Descripcion SEPARATOR ', '), 'Ninguno') AS TipoSacramento
    FROM habitantes h
    LEFT JOIN tipodocumento td     ON h.IdTipoDocumento = td.IdTipoDocumento
    LEFT JOIN estados_civiles ec   ON h.IdEstadoCivil = ec.IdEstadoCivil
    LEFT JOIN sexos s              ON h.IdSexo = s.IdSexo
    LEFT JOIN religiones r         ON h.IdReligion = r.IdReligion
    LEFT JOIN tipopoblacion tp     ON h.IdTipoPoblacion = tp.IdTipoPoblacion
    LEFT JOIN sector sec           ON h.IdSector = sec.IdSector
    LEFT JOIN grupofamiliar gf     ON h.IdGrupoFamiliar = gf.IdGrupoFamiliar  -- ← ESTE JOIN
    LEFT JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
    LEFT JOIN tiposacramentos ts   ON hs.IdSacramento = ts.IdSacramento
    WHERE h.Activo = 1
    GROUP BY h.IdHabitante
    ORDER BY h.IdHabitante DESC
    LIMIT 1000
"""
        habitantes = execute_query(query)
        return jsonify({
            "success": True,
            "habitantes": habitantes
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# OBTENER HABITANTE POR ID
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
                h.DiscapacidadParaAsistir,
                h.TieneImpedimentoSalud,
                h.MotivoImpedimentoSalud,
                h.IdGrupoFamiliar,
                COALESCE(gf.Descripcion, 'Sin familia') AS FamiliaDescripcion,  # ← NUEVO
                h.IdSector,
                sec.Descripcion AS Sector,
                h.Direccion,
                h.Telefono,
                h.CorreoElectronico,
                h.FechaRegistro,
                COALESCE(GROUP_CONCAT(DISTINCT ts.Descripcion SEPARATOR ', '), 'Ninguno') AS TipoSacramento
            FROM habitantes h
            LEFT JOIN tipodocumento td     ON h.IdTipoDocumento = td.IdTipoDocumento
            LEFT JOIN estados_civiles ec   ON h.IdEstadoCivil = ec.IdEstadoCivil
            LEFT JOIN sexos s              ON h.IdSexo = s.IdSexo
            LEFT JOIN religiones r         ON h.IdReligion = r.IdReligion
            LEFT JOIN tipopoblacion tp     ON h.IdTipoPoblacion = tp.IdTipoPoblacion
            LEFT JOIN sector sec           ON h.IdSector = sec.IdSector
            LEFT JOIN grupofamiliar gf     ON h.IdGrupoFamiliar = gf.IdGrupoFamiliar  # ← NUEVO JOIN
            LEFT JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
            LEFT JOIN tiposacramentos ts   ON hs.IdSacramento = ts.IdSacramento
            WHERE h.IdHabitante = %s AND h.Activo = 1
            GROUP BY h.IdHabitante
        """
        habitante = execute_query(query, (id,), fetch_one=True)

        if not habitante:
            return jsonify({'success': False, 'message': 'Habitante no encontrado'}), 404

        return jsonify({'success': True, 'habitante': habitante}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al obtener habitante: {str(e)}"}), 500


# CREAR HABITANTE CON CREACIÓN AUTOMÁTICA DE GRUPO FAMILIAR
@habitantes_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_habitante():
    try:
        data = request.get_json() or {}
        

        
        # Campos obligatorios del habitante
        Nombre = data.get('Nombre')
        Apellido = data.get('Apellido')
        IdTipoDocumento = data.get('IdTipoDocumento')
        NumeroDocumento = data.get('NumeroDocumento')
        FechaNacimiento = data.get('FechaNacimiento')
        IdSexo = data.get('IdSexo')
        IdEstadoCivil = data.get('IdEstadoCivil')
        IdReligion = data.get('IdReligion')
        IdTipoPoblacion = data.get('IdTipoPoblacion')
        IdSector = data.get('IdSector')
        Direccion = data.get('Direccion')
        Telefono = data.get('Telefono')
        CorreoElectronico = data.get('CorreoElectronico')
        
        # Campos de grupo familiar
        IdGrupoFamiliar = data.get('IdGrupoFamiliar')
        GrupoFamiliarNombre = data.get('GrupoFamiliarNombre')

        # Campos con valores por defecto
        Hijos = data.get('Hijos', 0)
        DiscapacidadParaAsistir = data.get('DiscapacidadParaAsistir', 'Ninguna')
        TieneImpedimentoSalud = 1 if data.get('TieneImpedimentoSalud') in (1, True, '1', 'true', 'True') else 0
        MotivoImpedimentoSalud = data.get('MotivoImpedimentoSalud', 'Ninguno')
        Activo = 1 if data.get('Activo', 1) in (1, True, '1', 'true', 'True') else 0

        # Sacramentos - array de IDs
        Sacramentos = data.get('Sacramentos', []) or []

        # Validaciones de campos obligatorios del habitante
        campos_obligatorios = {
            'Nombre': Nombre,
            'Apellido': Apellido,
            'IdTipoDocumento': IdTipoDocumento,
            'NumeroDocumento': NumeroDocumento,
            'FechaNacimiento': FechaNacimiento,
            'IdSexo': IdSexo,
            'IdEstadoCivil': IdEstadoCivil,
            'IdReligion': IdReligion,
            'IdTipoPoblacion': IdTipoPoblacion,
            'IdSector': IdSector,
            'Direccion': Direccion,
            'Telefono': Telefono,
            'CorreoElectronico': CorreoElectronico
        }

        campos_faltantes = [campo for campo, valor in campos_obligatorios.items() if valor is None]
        if campos_faltantes:
            return jsonify({
                'success': False, 
                'message': f'Faltan campos obligatorios: {", ".join(campos_faltantes)}'
            }), 400

        # VERIFICAR O CREAR GRUPO FAMILIAR
        grupo_id = None
        
        if IdGrupoFamiliar:
            grupo_query = "SELECT IdGrupoFamiliar FROM grupofamiliar WHERE IdGrupoFamiliar = %s AND Activo = 1"
            grupo = execute_query(grupo_query, (IdGrupoFamiliar,), fetch_one=True)
            if grupo:
                grupo_id = IdGrupoFamiliar
            else:
                return jsonify({'success': False, 'message': 'El grupo familiar seleccionado no existe'}), 400
                
        elif GrupoFamiliarNombre and GrupoFamiliarNombre.strip():
            nombre_grupo = GrupoFamiliarNombre.strip()
            
            grupo_existente_query = "SELECT IdGrupoFamiliar FROM grupofamiliar WHERE NombreGrupo = %s AND Activo = 1"
            grupo_existente = execute_query(grupo_existente_query, (nombre_grupo,), fetch_one=True)
            
            if grupo_existente:
                grupo_id = grupo_existente['IdGrupoFamiliar']
            else:
                insert_grupo_sql = """
                    INSERT INTO grupofamiliar (NombreGrupo, Descripcion, IdJefeFamilia, Activo)
                    VALUES (%s, NULL, NULL, 1)
                """
                grupo_id = execute_query(insert_grupo_sql, (nombre_grupo,))
        else:
            return jsonify({'success': False, 'message': 'Se requiere un grupo familiar (seleccionar existente o crear nuevo)'}), 400

        # Insertar habitante
        insert_sql = """
            INSERT INTO habitantes
            (Nombre, Apellido, IdTipoDocumento, NumeroDocumento, FechaNacimiento, Hijos,
             DiscapacidadParaAsistir, IdTipoPoblacion, Direccion, Telefono, CorreoElectronico,
             IdGrupoFamiliar, TieneImpedimentoSalud, MotivoImpedimentoSalud, Activo,
             IdSexo, IdEstadoCivil, IdReligion, IdSector, FechaRegistro)
            VALUES (%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s,%s,%s, NOW())
        """
        habitante_id = execute_query(insert_sql, (
            Nombre, Apellido, IdTipoDocumento, NumeroDocumento, FechaNacimiento, Hijos,
            DiscapacidadParaAsistir, IdTipoPoblacion, Direccion, Telefono, CorreoElectronico,
            grupo_id, TieneImpedimentoSalud, MotivoImpedimentoSalud, Activo,
            IdSexo, IdEstadoCivil, IdReligion, IdSector
        ))

        # ASIGNAR AUTOMÁTICAMENTE COMO FAMILIAR ASOCIADO SI EL GRUPO NO TIENE UNO
        try:
            grupo_query = "SELECT IdJefeFamilia FROM grupofamiliar WHERE IdGrupoFamiliar = %s"
            grupo = execute_query(grupo_query, (grupo_id,), fetch_one=True)
            
            if grupo and grupo.get('IdJefeFamilia') is None:
                execute_query(
                    "UPDATE grupofamiliar SET IdJefeFamilia = %s WHERE IdGrupoFamiliar = %s",
                    (habitante_id, grupo_id)
                )
                
                descripcion_actualizada = f"{Apellido}"
                execute_query(
                    "UPDATE grupofamiliar SET Descripcion = %s WHERE IdGrupoFamiliar = %s",
                    (descripcion_actualizada, grupo_id)
                )
                
        except Exception as e:
            pass

        # Insertar sacramentos
        if Sacramentos:
            for sacramento_id in Sacramentos:
                try:
                    sacramento_query = "SELECT IdSacramento FROM tiposacramentos WHERE IdSacramento = %s"
                    sacramento = execute_query(sacramento_query, (sacramento_id,), fetch_one=True)
                    
                    if sacramento:
                        existe_query = "SELECT 1 FROM habitante_sacramento WHERE IdHabitante = %s AND IdSacramento = %s"
                        existe = execute_query(existe_query, (habitante_id, sacramento_id), fetch_one=True)
                        
                        if not existe:
                            insert_sacramento_sql = """
                                INSERT INTO habitante_sacramento (IdHabitante, IdSacramento, FechaSacramento)
                                VALUES (%s, %s, NULL)
                            """
                            execute_query(insert_sacramento_sql, (habitante_id, sacramento_id))
                            
                except Exception as e:
                    continue

        return jsonify({
            'success': True,
            'message': 'Habitante creado exitosamente',
            'IdHabitante': habitante_id,
            'IdGrupoFamiliar': grupo_id,
            'FechaRegistro': datetime.now().isoformat()
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al crear habitante: {str(e)}"}), 500

@habitantes_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_habitante(id):
    try:
        data = request.get_json() or {}

        fields = {
            'Nombre': data.get('Nombre'),
            'Apellido': data.get('Apellido'),
            'IdTipoDocumento': data.get('IdTipoDocumento'),
            'NumeroDocumento': data.get('NumeroDocumento'),
            'FechaNacimiento': data.get('FechaNacimiento'),
            'Hijos': data.get('Hijos'),
            'DiscapacidadParaAsistir': data.get('DiscapacidadParaAsistir'),
            'IdTipoPoblacion': data.get('IdTipoPoblacion'),
            'Direccion': data.get('Direccion'),
            'Telefono': data.get('Telefono'),
            'CorreoElectronico': data.get('CorreoElectronico'),
            'IdGrupoFamiliar': data.get('IdGrupoFamiliar'),
            'TieneImpedimentoSalud': 1 if data.get('TieneImpedimentoSalud') in (1, True, '1', 'true', 'True') else 0,
            'MotivoImpedimentoSalud': data.get('MotivoImpedimentoSalud'),
            'Activo': 1 if data.get('Activo', 1) in (1, True, '1', 'true', 'True') else 0,
            'IdSexo': data.get('IdSexo'),
            'IdEstadoCivil': data.get('IdEstadoCivil'),
            'IdReligion': data.get('IdReligion'),
            'IdSector': data.get('IdSector'),
            
        }

        # Construir UPDATE dinámico
        sets, vals = [], []
        for k, v in fields.items():
            if v is not None:
                sets.append(f"{k}=%s")
                vals.append(v)
        
        if not sets:
            return jsonify({'success': False, 'message': 'Nada para actualizar'}), 400

        vals.append(id)
        sql = f"UPDATE habitantes SET {', '.join(sets)} WHERE IdHabitante=%s"
        updated = execute_query(sql, tuple(vals))

        # Sacramentos
        Sacramentos = data.get('Sacramentos', [])
        if Sacramentos is not None:
            execute_query("DELETE FROM habitante_sacramento WHERE IdHabitante=%s", (id,))
            for sid in Sacramentos:
                execute_query(
                    "INSERT INTO habitante_sacramento (IdHabitante, IdSacramento) VALUES (%s,%s)",
                    (id, int(sid))
                )

        # Asignar jefe si se pide
        AsignarComoJefe = data.get('AsignarComoJefe', False)
        IdGrupoFamiliar = fields.get('IdGrupoFamiliar')
        if AsignarComoJefe and IdGrupoFamiliar:
            _asignar_jefe_si_vacio(IdGrupoFamiliar, id)

        if updated:
            return jsonify({'success': True, 'message': 'Habitante actualizado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Habitante no encontrado o sin cambios'}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al actualizar habitante: {str(e)}"}), 500


# DESACTIVAR HABITANTE (soft delete)
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


# BUSCAR GRUPO POR MIEMBRO
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