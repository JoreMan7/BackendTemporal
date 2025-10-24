# =============================================
# MÓDULO DE TRANSACCIONES - GESTIÓN ECLESIAL
# =============================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query
from utils import require_rol
from datetime import datetime

transacciones_bp = Blueprint('transacciones', __name__)

# =============================================
# UTILIDADES PRIVADAS
# =============================================

def _tipo_movimiento_existe(id_tipo):
    row = execute_query(
        "SELECT IdTipoMovimiento FROM tipomovimiento WHERE IdTipoMovimiento = %s AND Activo = 1;",
        (id_tipo,), fetch_one=True
    )
    return bool(row)

def _concepto_existe(id_concepto):
    row = execute_query(
        "SELECT IdConcepto FROM conceptotransaccion WHERE IdConcepto = %s AND Activo = 1;",
        (id_concepto,), fetch_one=True
    )
    return bool(row)

# =============================================
# ENDPOINTS DE TIPOS DE MOVIMIENTO
# =============================================

@transacciones_bp.route('/movimientos', methods=['GET'])
@jwt_required()
def listar_tipos_movimiento():
    """Listar tipos de movimiento (Ingreso / Egreso) activos"""
    try:
        query = "SELECT IdTipoMovimiento, Descripcion, Activo FROM tipomovimiento ORDER BY IdTipoMovimiento DESC;"
        movimientos = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"movimientos": movimientos}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/movimientos', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_tipo_movimiento():
    """Crear nuevo tipo de movimiento"""
    try:
        data = request.get_json() or {}
        descripcion = (data.get('descripcion') or "").strip()

        if not descripcion:
            return jsonify({"success": False, "message": "La descripción es obligatoria"}), 400

        dup = execute_query(
            "SELECT COUNT(*) AS cnt FROM tipomovimiento WHERE Descripcion = %s AND Activo = 1;",
            (descripcion,), fetch_one=True
        )
        if dup and dup.get('cnt', 0) > 0:
            return jsonify({"success": False, "message": "Ya existe un tipo de movimiento activo con esa descripción"}), 409

        execute_query(
            "INSERT INTO tipomovimiento (Descripcion, Activo) VALUES (%s, 1);",
            (descripcion,)
        )
        nuevo = execute_query("SELECT LAST_INSERT_ID() AS id;", fetch_one=True)
        return jsonify({"success": True, "message": "Tipo de movimiento creado", "data": {"id": nuevo["id"]}}), 201
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/movimientos/<int:id>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_tipo_movimiento(id):
    """Desactivar tipo de movimiento y sus conceptos asociados"""
    try:
        # Desactivar tipo
        updated = execute_query(
            "UPDATE tipomovimiento SET Activo = 0 WHERE IdTipoMovimiento = %s AND Activo = 1;",
            (id,)
        )
        # Desactivar conceptos asociados (si los hay)
        execute_query(
            "UPDATE conceptotransaccion SET Activo = 0 WHERE IdTipoMovimiento = %s;",
            (id,)
        )
        return jsonify({"success": True, "message": "Tipo de movimiento desactivado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/movimientos/<int:id>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_tipo_movimiento(id):
    """Reactivar tipo de movimiento"""
    try:
        execute_query(
            "UPDATE tipomovimiento SET Activo = 1 WHERE IdTipoMovimiento = %s AND Activo = 0;",
            (id,)
        )
        return jsonify({"success": True, "message": "Tipo de movimiento activado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# ENDPOINTS DE CONCEPTOS DE TRANSACCIÓN
# =============================================

@transacciones_bp.route('/conceptos', methods=['GET'])
@jwt_required()
def listar_conceptos():
    """Listar conceptos activos con su tipo de movimiento"""
    try:
        query = """
            SELECT c.IdConcepto, c.Descripcion, c.IdTipoMovimiento, tm.Descripcion AS TipoMovimiento, c.Activo
            FROM conceptotransaccion c
            JOIN tipomovimiento tm ON c.IdTipoMovimiento = tm.IdTipoMovimiento
            WHERE c.Activo = 1
            ORDER BY c.IdConcepto DESC;
        """
        conceptos = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"conceptos": conceptos}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/conceptos', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_concepto():
    """Crear un concepto asociado a un tipo de movimiento"""
    try:
        data = request.get_json() or {}
        descripcion = (data.get('descripcion') or "").strip()
        id_tipo_movimiento = data.get('id_tipo_movimiento')

        if not descripcion or not id_tipo_movimiento:
            return jsonify({"success": False, "message": "descripcion e id_tipo_movimiento son obligatorios"}), 400

        if not _tipo_movimiento_existe(id_tipo_movimiento):
            return jsonify({"success": False, "message": "El tipo de movimiento no existe o está inactivo"}), 404

        dup = execute_query(
            "SELECT COUNT(*) AS cnt FROM conceptotransaccion WHERE Descripcion = %s AND IdTipoMovimiento = %s AND Activo = 1;",
            (descripcion, id_tipo_movimiento), fetch_one=True
        )
        if dup and dup.get('cnt', 0) > 0:
            return jsonify({"success": False, "message": "Ya existe un concepto activo con esa descripción para ese tipo de movimiento"}), 409

        execute_query(
            "INSERT INTO conceptotransaccion (Descripcion, IdTipoMovimiento, Activo) VALUES (%s, %s, 1);",
            (descripcion, id_tipo_movimiento)
        )
        nuevo = execute_query("SELECT LAST_INSERT_ID() AS id;", fetch_one=True)
        return jsonify({"success": True, "message": "Concepto creado", "data": {"id": nuevo["id"]}}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/conceptos/<int:id>', methods=['PUT'])
@jwt_required()
@require_rol('Administrador')
def actualizar_concepto(id):
    """Actualizar descripción o tipo de movimiento de un concepto"""
    try:
        data = request.get_json() or {}
        descripcion = data.get('descripcion')
        id_tipo_movimiento = data.get('id_tipo_movimiento')

        if not descripcion and not id_tipo_movimiento:
            return jsonify({"success": False, "message": "Al menos descripcion o id_tipo_movimiento requerido"}), 400

        if id_tipo_movimiento and not _tipo_movimiento_existe(id_tipo_movimiento):
            return jsonify({"success": False, "message": "El tipo de movimiento especificado no existe o está inactivo"}), 404

        # Si cambian ambos o alguno, hacer update seguro
        params = []
        sets = []
        if descripcion is not None:
            sets.append("Descripcion = %s")
            params.append(descripcion)
        if id_tipo_movimiento is not None:
            sets.append("IdTipoMovimiento = %s")
            params.append(id_tipo_movimiento)

        params.append(id)
        sql = "UPDATE conceptotransaccion SET " + ", ".join(sets) + " WHERE IdConcepto = %s;"
        execute_query(sql, tuple(params))
        return jsonify({"success": True, "message": "Concepto actualizado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/conceptos/<int:id>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_concepto(id):
    """Desactivar concepto"""
    try:
        execute_query("UPDATE conceptotransaccion SET Activo = 0 WHERE IdConcepto = %s;", (id,))
        return jsonify({"success": True, "message": "Concepto desactivado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/conceptos/<int:id>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_concepto(id):
    """Reactivar concepto"""
    try:
        execute_query("UPDATE conceptotransaccion SET Activo = 1 WHERE IdConcepto = %s;", (id,))
        return jsonify({"success": True, "message": "Concepto activado correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# ENDPOINTS DE TRANSACCIONES PARROQUIALES
# =============================================

@transacciones_bp.route('/', methods=['GET'])
@jwt_required()
def listar_transacciones():
    """Listar todas las transacciones activas con concepto y tipo de movimiento"""
    try:
        query = """
            SELECT 
                t.IdTransaccion,
                t.IdConcepto,
                c.Descripcion AS Concepto,
                c.IdTipoMovimiento,
                tm.Descripcion AS TipoMovimiento,
                t.Monto,
                t.FechaTransaccion,
                t.Observacion,
                t.Activo
            FROM transaccionparroquia t
            JOIN conceptotransaccion c ON t.IdConcepto = c.IdConcepto
            JOIN tipomovimiento tm ON c.IdTipoMovimiento = tm.IdTipoMovimiento
            WHERE t.Activo = 1
            ORDER BY t.FechaTransaccion DESC, t.IdTransaccion DESC;
        """
        transacciones = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "data": {"transacciones": transacciones}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_transaccion(id):
    """Obtener detalle de una transacción"""
    try:
        query = """
            SELECT 
                t.IdTransaccion,
                t.IdConcepto,
                c.Descripcion AS Concepto,
                c.IdTipoMovimiento,
                tm.Descripcion AS TipoMovimiento,
                t.Monto,
                t.FechaTransaccion,
                t.Observacion,
                t.Activo
            FROM transaccionparroquia t
            JOIN conceptotransaccion c ON t.IdConcepto = c.IdConcepto
            JOIN tipomovimiento tm ON c.IdTipoMovimiento = tm.IdTipoMovimiento
            WHERE t.IdTransaccion = %s;
        """
        trans = execute_query(query, (id,), fetch_one=True)
        if not trans:
            return jsonify({"success": False, "message": "Transacción no encontrada"}), 404
        return jsonify({"success": True, "data": {"transaccion": trans}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def crear_transaccion():
    """Crear nueva transacción parroquial"""
    try:
        data = request.get_json() or {}
        id_concepto = data.get('id_concepto')
        monto = data.get('monto')
        fecha_str = data.get('fecha_transaccion')  # aceptar 'YYYY-MM-DD'
        observacion = data.get('observacion') or None

        # Validaciones básicas
        if not id_concepto or monto is None:
            return jsonify({"success": False, "message": "id_concepto y monto son obligatorios"}), 400

        # Validar concepto activo
        if not _concepto_existe(id_concepto):
            return jsonify({"success": False, "message": "El concepto no existe o está inactivo"}), 404

        # Monto > 0
        try:
            monto_val = float(monto)
        except Exception:
            return jsonify({"success": False, "message": "Monto inválido"}), 400

        if monto_val <= 0:
            return jsonify({"success": False, "message": "El monto debe ser mayor a 0"}), 400

        # Fecha: si no viene, usar hoy
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"success": False, "message": "fecha_transaccion debe tener formato YYYY-MM-DD"}), 400
        else:
            fecha = datetime.now().date()

        execute_query(
            "INSERT INTO transaccionparroquia (IdConcepto, Monto, FechaTransaccion, Observacion, Activo) VALUES (%s, %s, %s, %s, 1);",
            (id_concepto, monto_val, fecha, observacion)
        )
        nuevo = execute_query("SELECT LAST_INSERT_ID() AS id;", fetch_one=True)
        return jsonify({"success": True, "message": "Transacción registrada", "data": {"id": nuevo["id"]}}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/<int:id>/desactivar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def desactivar_transaccion(id):
    """Desactivar (soft delete) transacción"""
    try:
        execute_query("UPDATE transaccionparroquia SET Activo = 0 WHERE IdTransaccion = %s;", (id,))
        return jsonify({"success": True, "message": "Transacción desactivada correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@transacciones_bp.route('/<int:id>/activar', methods=['PATCH'])
@jwt_required()
@require_rol('Administrador')
def activar_transaccion(id):
    """Reactivar transacción"""
    try:
        execute_query("UPDATE transaccionparroquia SET Activo = 1 WHERE IdTransaccion = %s;", (id,))
        return jsonify({"success": True, "message": "Transacción activada correctamente"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# =============================================
# FIN DEL MÓDULO TRANSACCIONES
# =============================================
