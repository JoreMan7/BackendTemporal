"""
Rutas para gestión de CITAS (tabla: asignacioncita)
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query
from utils import require_rol
from datetime import datetime

citas_bp = Blueprint('citas', __name__)

# =========================
# LISTAR CITAS
# =========================
@citas_bp.route('/', methods=['GET'])
@jwt_required()
def listar_citas():
    """
    Lista citas con joins informativos.
    Filtros opcionales: ?estado=IdEstadoCita&tipo=IdTipoCita&desde=YYYY-MM-DD&hasta=YYYY-MM-DD&q=texto
    """
    try:
        estado = request.args.get('estado')
        tipo = request.args.get('tipo')
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        q = (request.args.get('q') or '').strip()

        filters, params = [], []

        if estado:
            filters.append('ac.IdEstadoCita = %s')
            params.append(estado)
        if tipo:
            filters.append('ac.IdTipoCita = %s')
            params.append(tipo)
        if desde:
            filters.append('ac.Fecha >= %s')
            params.append(desde)
        if hasta:
            filters.append('ac.Fecha <= %s')
            params.append(hasta)
        if q:
            like = f"%{q}%"
            filters.append('(ac.NombreSolicitante LIKE %s OR ac.Celular LIKE %s OR ac.Descripcion LIKE %s OR p.Nombre LIKE %s OR p.Apellido LIKE %s OR ac.NumeroDocumentoSolicitante LIKE %s)')
            params += [like, like, like, like, like, like]

        where = ('WHERE ' + ' AND '.join(filters)) if filters else ''
        
        # CONSULTA ACTUALIZADA con nuevos campos
        query = f"""
            SELECT
                ac.IdAsignacionCita,
                ac.NombreSolicitante,
                ac.Celular,
                ac.IdTipoDocumentoSolicitante,
                td.Descripcion AS TipoDocumentoSolicitante,
                ac.NumeroDocumentoSolicitante,
                ac.Fecha,
                TIME_FORMAT(ac.Hora, '%%H:%%i') AS Hora,
                ac.IdPadre,
                CONCAT(p.Nombre, ' ', p.Apellido) AS PadreNombre,
                ac.IdEstadoCita,
                ec.Descripcion AS EstadoDescripcion,
                ac.IdTipoCita,
                tc.Descripcion AS TipoDescripcion,
                ac.Descripcion,
                ac.Activo,
                ac.FechaRegistro
            FROM asignacioncita ac
            LEFT JOIN padre p        ON ac.IdPadre = p.IdPadre
            LEFT JOIN estadocita ec  ON ec.IdEstadoCita = ac.IdEstadoCita
            LEFT JOIN tipocita  tc   ON tc.IdTipoCita  = ac.IdTipoCita
            LEFT JOIN tipodocumento td ON td.IdTipoDocumento = ac.IdTipoDocumentoSolicitante
            {where}
            ORDER BY ac.Fecha DESC, ac.Hora DESC;
        """
        rows = execute_query(query, params, fetch_all=True)
        return jsonify({'success': True, 'citas': rows})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error listando citas: {str(e)}'}), 500

# =========================
# OBTENER DETALLE
# =========================
@citas_bp.route('/<int:id_cita>/', methods=['GET'])
@jwt_required()
def obtener_cita(id_cita):
    try:
        query = """
            SELECT
                ac.IdAsignacionCita,
                ac.NombreSolicitante,
                ac.Celular,
                ac.IdTipoDocumentoSolicitante,
                td.Descripcion AS TipoDocumentoSolicitante,
                ac.NumeroDocumentoSolicitante,
                ac.Fecha,
                TIME_FORMAT(ac.Hora, '%%H:%%i') AS Hora,
                ac.IdPadre,
                CONCAT(p.Nombre, ' ', p.Apellido) AS PadreNombre,
                ac.IdEstadoCita,
                ec.Descripcion AS EstadoDescripcion,
                ac.IdTipoCita,
                tc.Descripcion AS TipoDescripcion,
                ac.Descripcion,
                ac.Activo,
                ac.FechaRegistro
            FROM asignacioncita ac
            LEFT JOIN padre p        ON ac.IdPadre = p.IdPadre
            LEFT JOIN estadocita ec  ON ec.IdEstadoCita = ac.IdEstadoCita
            LEFT JOIN tipocita  tc   ON tc.IdTipoCita  = ac.IdTipoCita
            LEFT JOIN tipodocumento td ON td.IdTipoDocumento = ac.IdTipoDocumentoSolicitante
            WHERE ac.IdAsignacionCita = %s
            LIMIT 1;
        """
        row = execute_query(query, (id_cita,), fetch_one=True)
        if not row:
            return jsonify({'success': False, 'message': 'Cita no encontrada'}), 404
        return jsonify({'success': True, 'cita': row})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error obteniendo cita: {str(e)}'}), 500

# =========================
# CREAR CITA - VERSIÓN CORREGIDA
# =========================
# =========================
# CREAR CITA - SIMPLIFICADO
# =========================
@citas_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_cita():
    try:
        data = request.get_json() or {}
        print("Datos recibidos:", data)
        
        required = ['Fecha', 'Hora', 'IdPadre', 'IdTipoCita', 'NombreSolicitante', 'Celular', 'IdTipoDocumentoSolicitante', 'NumeroDocumentoSolicitante']
        missing = [k for k in required if data.get(k) in (None, '', [])]
        if missing:
            return jsonify({'success': False, 'message': f'Campos obligatorios faltantes: {", ".join(missing)}'}), 400

        # ID DIRECTO DEL ESTADO PENDIENTE (según tu BD)
        ID_ESTADO_PENDIENTE = 1

        query = """
            INSERT INTO asignacioncita
                (NombreSolicitante, Celular, IdTipoDocumentoSolicitante, NumeroDocumentoSolicitante, 
                 Fecha, Hora, IdPadre, Descripcion, IdEstadoCita, IdTipoCita, Activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1);
        """
        params = (
            data['NombreSolicitante'].strip(),
            data['Celular'].strip(),
            int(data['IdTipoDocumentoSolicitante']),
            data['NumeroDocumentoSolicitante'].strip(),
            data['Fecha'],
            data['Hora'],
            int(data['IdPadre']),
            (data.get('Descripcion') or '').strip(),
            ID_ESTADO_PENDIENTE,  # ✅ ID directo
            int(data['IdTipoCita'])
        )
        
        print("Ejecutando INSERT...")
        new_id = execute_query(query, params)
        return jsonify({'success': True, 'IdAsignacionCita': new_id})
        
    except Exception as e:
        print("Error:", str(e))
        return jsonify({'success': False, 'message': f'Error creando cita: {str(e)}'}), 500
    

# =========================
# EDITAR CITA
# =========================
@citas_bp.route('/<int:id_cita>/', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def editar_cita(id_cita):
    try:
        data = request.get_json() or {}
        fields = {
            'NombreSolicitante': data.get('NombreSolicitante'),
            'Celular': data.get('Celular'),
            'IdTipoDocumentoSolicitante': data.get('IdTipoDocumentoSolicitante'),
            'NumeroDocumentoSolicitante': data.get('NumeroDocumentoSolicitante'),
            'Fecha': data.get('Fecha'),
            'Hora': data.get('Hora'),
            'IdPadre': data.get('IdPadre'),
            'Descripcion': data.get('Descripcion'),
            'IdEstadoCita': data.get('IdEstadoCita'),  # En edición sí se puede cambiar el estado
            'IdTipoCita': data.get('IdTipoCita'),
        }
        sets, params = [], []
        for k, v in fields.items():
            if v is not None:
                sets.append(f"{k} = %s")
                params.append(v)
        if not sets:
            return jsonify({'success': False, 'message': 'Nada para actualizar'}), 400

        params.append(id_cita)
        query = f"UPDATE asignacioncita SET {', '.join(sets)} WHERE IdAsignacionCita = %s;"
        cnt = execute_query(query, tuple(params))
        return jsonify({'success': True, 'updated': cnt})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error editando cita: {str(e)}'}), 500

# =========================
# OPCIONES (catálogos actualizados)
# =========================
@citas_bp.route('/opciones/', methods=['GET'])
@jwt_required()
def opciones_citas():
    try:
        estados = execute_query("SELECT IdEstadoCita, Descripcion FROM estadocita ORDER BY IdEstadoCita ASC;", fetch_all=True)
        tipos = execute_query("SELECT IdTipoCita, Descripcion, Valor FROM tipocita ORDER BY IdTipoCita ASC;", fetch_all=True)
        tipos_documento = execute_query("SELECT IdTipoDocumento, Descripcion FROM tipodocumento ORDER BY IdTipoDocumento ASC;", fetch_all=True)
        
        return jsonify({
            'success': True, 
            'estadosCita': estados, 
            'tiposCita': tipos,
            'tiposDocumento': tipos_documento
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error cargando opciones: {str(e)}'}), 500

# =========================
# DESACTIVAR CITA
# =========================
@citas_bp.route('/<int:id_cita>/desactivar/', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_cita(id_cita):
    try:
        cnt = execute_query("UPDATE asignacioncita SET Activo = 0 WHERE IdAsignacionCita = %s;", (id_cita,))
        return jsonify({'success': True, 'updated': cnt})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error desactivando cita: {str(e)}'}), 500

# =========================
# RECORDATORIOS (placeholder)
# =========================
@citas_bp.route('/<int:id_cita>/recordatorios/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_recordatorio_cita(id_cita):
    """
    Placeholder de recordatorios: responde OK para que el frontend funcione.
    (En el dump no existe tabla de recordatorios; puedes crearla luego y persistir aquí.)
    Body esperado: {"minutos_antes": 30}
    """
    try:
        data = request.get_json() or {}
        minutos = int(data.get('minutos_antes') or 30)
        return jsonify({'success': True, 'message': f'Recordatorio aceptado ({minutos} min antes).'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error recordatorio: {str(e)}'}), 500

# =========================
# CITAS PARA DASHBOARD
# =========================
@citas_bp.route('/dashboard/', methods=['GET'])
@jwt_required()
def citas_dashboard():
    """
    Devuelve las próximas citas para el dashboard (máximo 12)
    """
    try:
        query = """
            SELECT
                ac.IdAsignacionCita,
                ac.NombreSolicitante,
                ac.Fecha,
                TIME_FORMAT(ac.Hora, '%%H:%%i') AS Hora,
                CONCAT(p.Nombre, ' ', p.Apellido) AS PadreNombre,
                tc.Descripcion AS TipoDescripcion,
                ec.Descripcion AS EstadoDescripcion
            FROM asignacioncita ac
            LEFT JOIN padre p ON ac.IdPadre = p.IdPadre
            LEFT JOIN tipocita tc ON ac.IdTipoCita = tc.IdTipoCita
            LEFT JOIN estadocita ec ON ac.IdEstadoCita = ec.IdEstadoCita
            WHERE ac.Activo = 1 
            AND ac.Fecha >= CURDATE()
            ORDER BY ac.Fecha ASC, ac.Hora ASC
            LIMIT 12;
        """
        citas = execute_query(query, fetch_all=True)
        return jsonify({'success': True, 'citas': citas})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error obteniendo citas para dashboard: {str(e)}'}), 500

@citas_bp.route('/dashboard/calendario/', methods=['GET'])
@jwt_required()
def citas_calendario():
    """
    Devuelve las fechas que tienen citas para resaltar en el calendario
    """
    try:
        # Obtener el mes y año actual (o especificado)
        mes = request.args.get('mes')
        año = request.args.get('año')
        
        if not mes or not año:
            hoy = datetime.now()
            mes = hoy.month
            año = hoy.year

        query = """
            SELECT DISTINCT DATE(Fecha) as Fecha
            FROM asignacioncita 
            WHERE Activo = 1 
            AND MONTH(Fecha) = %s 
            AND YEAR(Fecha) = %s
            ORDER BY Fecha;
        """
        fechas = execute_query(query, (mes, año), fetch_all=True)
        return jsonify({'success': True, 'fechas': [f['Fecha'] for f in fechas]})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error obteniendo fechas de citas: {str(e)}'}), 500