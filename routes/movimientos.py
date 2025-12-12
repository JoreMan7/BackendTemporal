# ============================================================
# MÓDULO DE MOVIMIENTOS DE CAJA - GESTIÓN ECLESIAL
# Tabla principal: movimientos_caja
# Se apoya en:
#  - tipomovimiento        (1=Ingreso, 2=Egreso, etc.)
#  - conceptotransaccion   (catálogo de conceptos por tipo)
# ============================================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query
from utils import require_rol
from datetime import datetime

movimientos_bp = Blueprint("movimientos", __name__)

# ============================================================
# UTILIDADES PRIVADAS
# ============================================================

def _obtener_tipo_movimiento(id_tipo):
    return execute_query(
        "SELECT IdTipoMovimiento FROM tipomovimiento WHERE IdTipoMovimiento = %s",
        (id_tipo,),
        fetch_one=True
    )

def _obtener_concepto(id_concepto):
    return execute_query(
        """
        SELECT 
            IdConceptoTransaccion,
            IdTipoMovimiento,
            Descripcion
        FROM conceptotransaccion
        WHERE IdConceptoTransaccion = %s
        """,
        (id_concepto,),
        fetch_one=True
    )

# ============================================================
# LISTAR MOVIMIENTOS
# GET /api/movimientos/?tipo=&desde=&hasta=&q=
# ============================================================

@movimientos_bp.route("/", methods=["GET"])
@jwt_required()
def listar_movimientos():
    """
    Lista movimientos de caja con joins a tipomovimiento y conceptotransaccion.
    Filtros opcionales:
      - tipo: IdTipoMovimiento (1=Ingreso, 2=Egreso)
      - desde: FechaMovimiento >= desde (YYYY-MM-DD)
      - hasta: FechaMovimiento <= hasta (YYYY-MM-DD)
      - q: texto en Motivo u Observaciones
    Solo se devuelven movimientos Activo = 1.
    """
    try:
        tipo = request.args.get("tipo")
        desde = request.args.get("desde")
        hasta = request.args.get("hasta")
        q = (request.args.get("q") or "").strip()

        condiciones = ["m.Activo = 1"]
        params = []

        if tipo and tipo.isdigit():
            condiciones.append("m.IdTipoMovimiento = %s")
            params.append(int(tipo))

        if desde:
            condiciones.append("m.FechaMovimiento >= %s")
            params.append(desde)

        if hasta:
            condiciones.append("m.FechaMovimiento <= %s")
            params.append(hasta)

        if q:
            like = f"%{q}%"
            condiciones.append("(m.Motivo LIKE %s OR m.Observaciones LIKE %s)")
            params.extend([like, like])

        where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""

        query = f"""
            SELECT 
                m.IdMovimiento,
                m.IdTipoMovimiento,
                tm.Descripcion AS TipoMovimientoNombre,
                m.IdConceptoTransaccion,
                c.Descripcion AS ConceptoNombre,
                m.Motivo,
                m.Valor,
                m.FechaMovimiento,
                m.Observaciones,
                m.FechaRegistro,
                m.Activo
            FROM movimientos_caja m
            LEFT JOIN tipomovimiento tm 
                ON m.IdTipoMovimiento = tm.IdTipoMovimiento
            LEFT JOIN conceptotransaccion c
                ON m.IdConceptoTransaccion = c.IdConceptoTransaccion
            {where_clause}
            ORDER BY 
                m.FechaMovimiento DESC,
                m.IdMovimiento DESC
        """

        movimientos = execute_query(query, tuple(params) if params else None)
        # Igual que otros módulos: success + payload plano
        return jsonify({"success": True, "movimientos": movimientos}), 200

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Error listando movimientos: {str(e)}"}
            ),
            500,
        )

# ============================================================
# OBTENER DETALLE
# GET /api/movimientos/<id>/
# ============================================================

@movimientos_bp.route("/<int:id_movimiento>/", methods=["GET"])
@jwt_required()
def obtener_movimiento(id_movimiento):
    """
    Obtiene el detalle de un movimiento de caja por su ID.
    """
    try:
        query = """
            SELECT 
                m.IdMovimiento,
                m.IdTipoMovimiento,
                tm.Descripcion AS TipoMovimientoNombre,
                m.IdConceptoTransaccion,
                c.Descripcion AS ConceptoNombre,
                m.Motivo,
                m.Valor,
                m.FechaMovimiento,
                m.Observaciones,
                m.FechaRegistro,
                m.Activo
            FROM movimientos_caja m
            LEFT JOIN tipomovimiento tm 
                ON m.IdTipoMovimiento = tm.IdTipoMovimiento
            LEFT JOIN conceptotransaccion c
                ON m.IdConceptoTransaccion = c.IdConceptoTransaccion
            WHERE m.IdMovimiento = %s
        """
        movimiento = execute_query(query, (id_movimiento,), fetch_one=True)

        if not movimiento:
            return jsonify({"success": False, "message": "Movimiento no encontrado"}), 404

        return jsonify({"success": True, "movimiento": movimiento}), 200

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Error obteniendo movimiento: {str(e)}"},
            ),
            500,
        )

# ============================================================
# CREAR MOVIMIENTO
# POST /api/movimientos/
# ============================================================

@movimientos_bp.route("/", methods=["POST"])
@jwt_required()
@require_rol("Administrador")
def crear_movimiento():
    """
    Crea un nuevo movimiento de caja.
    Campos esperados en JSON:
      - IdTipoMovimiento (int, requerido)
      - IdConceptoTransaccion (int, opcional pero recomendado)
      - Motivo (str, requerido, texto libre)
      - Valor (decimal > 0, requerido)
      - FechaMovimiento (YYYY-MM-DD, opcional -> por defecto hoy)
      - Observaciones (str, opcional)
      - Activo (0/1, opcional -> por defecto 1)
    """
    try:
        data = request.get_json() or {}

        required = ["IdTipoMovimiento", "Motivo", "Valor"]
        missing = [k for k in required if data.get(k) in (None, "", [])]
        if missing:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Campos obligatorios faltantes: {', '.join(missing)}",
                    }
                ),
                400,
            )

        # Tipo de movimiento
        try:
            id_tipo = int(data.get("IdTipoMovimiento"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "IdTipoMovimiento debe ser entero."}), 400

        if not _obtener_tipo_movimiento(id_tipo):
            return jsonify({"success": False, "message": "El tipo de movimiento no existe."}), 400

        # Motivo
        motivo = (data.get("Motivo") or "").strip()
        if not motivo:
            return jsonify({"success": False, "message": "El campo Motivo es obligatorio."}), 400

        # Valor
        try:
            valor = float(data.get("Valor"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "El campo Valor debe ser numérico."}), 400

        if valor <= 0:
            return jsonify({"success": False, "message": "El valor debe ser mayor a 0."}), 400

        # Fecha
        fecha_mov = data.get("FechaMovimiento")
        if not fecha_mov:
            fecha_mov = datetime.now().strftime("%Y-%m-%d")

        # Observaciones
        observaciones = (data.get("Observaciones") or "").strip() or None

        # Activo
        activo = data.get("Activo", 1)
        activo = 1 if str(activo) in ("1", "true", "True") else 0

        # Concepto (opcional pero validado si viene)
        id_concepto = data.get("IdConceptoTransaccion")
        if id_concepto not in (None, "", []):
            try:
                id_concepto = int(id_concepto)
            except (TypeError, ValueError):
                return jsonify({"success": False, "message": "IdConceptoTransaccion debe ser entero."}), 400

            concepto = _obtener_concepto(id_concepto)
            if not concepto:
                return jsonify({"success": False, "message": "El concepto especificado no existe."}), 400

            # Validar coherencia tipo-concepto
            concepto_tipo = concepto.get("IdTipoMovimiento")
            if concepto_tipo and int(concepto_tipo) != id_tipo:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "El concepto pertenece a un tipo de movimiento diferente.",
                        }
                    ),
                    400,
                )
        else:
            id_concepto = None

        insert_query = """
            INSERT INTO movimientos_caja (
                IdTipoMovimiento,
                IdConceptoTransaccion,
                Motivo,
                Valor,
                FechaMovimiento,
                Observaciones,
                Activo,
                FechaRegistro
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        new_id = execute_query(
            insert_query,
            (id_tipo, id_concepto, motivo, valor, fecha_mov, observaciones, activo),
            fetch_one=False,
            fetch_all=False,
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Movimiento creado correctamente.",
                    "id": new_id,
                }
            ),
            201,
        )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Error creando movimiento: {str(e)}"}
            ),
            500,
        )

# ============================================================
# EDITAR MOVIMIENTO
# PUT /api/movimientos/<id>/
# ============================================================

@movimientos_bp.route("/<int:id_movimiento>/", methods=["PUT"])
@jwt_required()
@require_rol("Administrador")
def actualizar_movimiento(id_movimiento):
    """
    Actualiza un movimiento existente.
    Campos posibles:
      - IdTipoMovimiento
      - IdConceptoTransaccion
      - Motivo
      - Valor
      - FechaMovimiento
      - Observaciones
      - Activo
    """
    try:
        data = request.get_json() or {}

        # Verificar que el movimiento exista
        existe = execute_query(
            "SELECT IdMovimiento FROM movimientos_caja WHERE IdMovimiento = %s",
            (id_movimiento,),
            fetch_one=True,
        )
        if not existe:
            return jsonify({"success": False, "message": "Movimiento no encontrado."}), 404

        fields = {}

        # Tipo de movimiento
        if "IdTipoMovimiento" in data and data.get("IdTipoMovimiento") is not None:
            try:
                id_tipo = int(data.get("IdTipoMovimiento"))
            except (TypeError, ValueError):
                return jsonify({"success": False, "message": "IdTipoMovimiento debe ser entero."}), 400

            if not _obtener_tipo_movimiento(id_tipo):
                return jsonify({"success": False, "message": "El tipo de movimiento no existe."}), 400

            fields["IdTipoMovimiento"] = id_tipo
        else:
            id_tipo = None  # puede venir desde BD si hace falta

        # Motivo
        if "Motivo" in data:
            motivo = (data.get("Motivo") or "").strip()
            if not motivo:
                return jsonify({"success": False, "message": "Motivo no puede estar vacío."}), 400
            fields["Motivo"] = motivo

        # Valor
        if "Valor" in data:
            try:
                valor = float(data.get("Valor"))
            except (TypeError, ValueError):
                return jsonify({"success": False, "message": "Valor debe ser numérico."}), 400
            if valor <= 0:
                return jsonify({"success": False, "message": "Valor debe ser mayor a 0."}), 400
            fields["Valor"] = valor

        # Fecha
        if "FechaMovimiento" in data:
            fields["FechaMovimiento"] = data.get("FechaMovimiento") or None

        # Observaciones
        if "Observaciones" in data:
            obs = (data.get("Observaciones") or "").strip() or None
            fields["Observaciones"] = obs

        # Activo
        if "Activo" in data:
            activo = data.get("Activo")
            activo = 1 if str(activo) in ("1", "true", "True") else 0
            fields["Activo"] = activo

        # Concepto
        if "IdConceptoTransaccion" in data:
            id_concepto = data.get("IdConceptoTransaccion")
            if id_concepto in (None, "", []):
                fields["IdConceptoTransaccion"] = None
            else:
                try:
                    id_concepto = int(id_concepto)
                except (TypeError, ValueError):
                    return jsonify({"success": False, "message": "IdConceptoTransaccion debe ser entero."}), 400

                concepto = _obtener_concepto(id_concepto)
                if not concepto:
                    return jsonify({"success": False, "message": "El concepto especificado no existe."}), 400

                concepto_tipo = concepto.get("IdTipoMovimiento")

                # Si se actualiza también el tipo, validar coherencia
                if id_tipo is not None and concepto_tipo and int(concepto_tipo) != id_tipo:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "El concepto pertenece a un tipo de movimiento diferente.",
                            }
                        ),
                        400,
                    )

                fields["IdConceptoTransaccion"] = id_concepto

        if not fields:
            return jsonify({"success": False, "message": "No hay datos para actualizar."}), 400

        set_clauses = []
        params = []
        for col, val in fields.items():
            set_clauses.append(f"{col} = %s")
            params.append(val)

        params.append(id_movimiento)

        update_query = f"""
            UPDATE movimientos_caja
            SET {", ".join(set_clauses)}
            WHERE IdMovimiento = %s
        """

        execute_query(
            update_query,
            tuple(params),
            fetch_one=False,
            fetch_all=False,
        )

        return jsonify({"success": True, "message": "Movimiento actualizado correctamente."}), 200

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Error actualizando movimiento: {str(e)}"},
            ),
            500,
        )

# ============================================================
# DESACTIVAR MOVIMIENTO
# PATCH /api/movimientos/<id>/desactivar/
# ============================================================

@movimientos_bp.route("/<int:id_movimiento>/desactivar/", methods=["PATCH"])
@jwt_required()
@require_rol("Administrador")
def desactivar_movimiento(id_movimiento):
    """
    Marca un movimiento como inactivo (Activo = 0).
    """
    try:
        existe = execute_query(
            "SELECT IdMovimiento FROM movimientos_caja WHERE IdMovimiento = %s",
            (id_movimiento,),
            fetch_one=True,
        )
        if not existe:
            return jsonify({"success": False, "message": "Movimiento no encontrado."}), 404

        update_query = """
            UPDATE movimientos_caja
            SET Activo = 0
            WHERE IdMovimiento = %s
        """
        execute_query(
            update_query,
            (id_movimiento,),
            fetch_one=False,
            fetch_all=False,
        )

        return jsonify({"success": True, "message": "Movimiento desactivado correctamente."}), 200

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Error desactivando movimiento: {str(e)}"},
            ),
            500,
        )

# ============================================================
# CONCEPTOS DE TRANSACCIÓN (CATÁLOGO)
# GET /api/movimientos/conceptos/?tipo=1|2
# POST /api/movimientos/conceptos/
# ============================================================

@movimientos_bp.route("/conceptos/", methods=["GET"])
@jwt_required()
def listar_conceptos():
    """
    Lista conceptos de transacción.
    Filtro opcional:
      - tipo: IdTipoMovimiento (para devolver solo los de ese tipo)
    """
    try:
        tipo = request.args.get("tipo")
        params = []
        where = ""

        if tipo and tipo.isdigit():
            where = "WHERE IdTipoMovimiento = %s"
            params.append(int(tipo))

        query = f"""
            SELECT 
                IdConceptoTransaccion,
                IdTipoMovimiento,
                Descripcion
            FROM conceptotransaccion
            {where}
            ORDER BY Descripcion ASC
        """
        conceptos = execute_query(query, tuple(params) if params else None)

        return jsonify({"success": True, "conceptos": conceptos}), 200

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Error listando conceptos: {str(e)}"},
            ),
            500,
        )

@movimientos_bp.route("/conceptos/", methods=["POST"])
@jwt_required()
@require_rol("Administrador")
def crear_concepto():
    """
    Crea un nuevo concepto de transacción.
    JSON esperado:
      - IdTipoMovimiento (int, requerido)
      - Descripcion (str, requerido)
    """
    try:
        data = request.get_json() or {}

        try:
            id_tipo = int(data.get("IdTipoMovimiento"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "IdTipoMovimiento debe ser entero."}), 400

        if not _obtener_tipo_movimiento(id_tipo):
            return jsonify({"success": False, "message": "El tipo de movimiento no existe."}), 400

        descripcion = (data.get("Descripcion") or "").strip()
        if not descripcion:
            return jsonify({"success": False, "message": "La descripción del concepto es obligatoria."}), 400

        insert_query = """
            INSERT INTO conceptotransaccion (IdTipoMovimiento, Descripcion)
            VALUES (%s, %s)
        """
        new_id = execute_query(
            insert_query,
            (id_tipo, descripcion),
            fetch_one=False,
            fetch_all=False,
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Concepto creado correctamente.",
                    "id": new_id,
                    "concepto": {
                        "IdConceptoTransaccion": new_id,
                        "IdTipoMovimiento": id_tipo,
                        "Descripcion": descripcion,
                    },
                }
            ),
            201,
        )

    except Exception as e:
        return (
            jsonify(
                {"success": False, "message": f"Error creando concepto: {str(e)}"},
            ),
            500,
        )
# ============================================================
# RESUMEN FINANCIERO
# GET /api/movimientos/resumen/?meses=3
# ============================================================

@movimientos_bp.route("/resumen/", methods=["GET"])
@jwt_required()
def resumen_movimientos():
    """
    Devuelve un resumen financiero por período (mes),
    con total de ingresos, egresos y saldo.

    Parámetros opcionales:
      - meses: número de meses hacia atrás a incluir (1–12, por defecto 3)
    """
    try:
        meses_param = request.args.get("meses", "3")
        try:
            meses = int(meses_param)
            if meses < 1:
                meses = 1
            if meses > 12:
                meses = 12
        except ValueError:
            meses = 3

        # Agrupar por año/mes
        query = """
            SELECT 
                YEAR(FechaMovimiento) AS Anio,
                MONTH(FechaMovimiento) AS Mes,
                SUM(CASE WHEN IdTipoMovimiento = 1 THEN Valor ELSE 0 END) AS TotalIngresos,
                SUM(CASE WHEN IdTipoMovimiento = 2 THEN Valor ELSE 0 END) AS TotalEgresos
            FROM movimientos_caja
            WHERE Activo = 1
            GROUP BY Anio, Mes
            ORDER BY Anio DESC, Mes DESC
            LIMIT %s;
        """

        filas = execute_query(query, (meses,))

        meses_es = [
            "", "Enero", "Febrero", "Marzo", "Abril", "Mayo",
            "Junio", "Julio", "Agosto", "Septiembre",
            "Octubre", "Noviembre", "Diciembre"
        ]

        resumen = []
        total_ingresos = 0.0
        total_egresos = 0.0

        for row in filas or []:
            anio = row["Anio"]
            mes = row["Mes"]
            ing = float(row["TotalIngresos"] or 0)
            egr = float(row["TotalEgresos"] or 0)
            saldo = ing - egr

            total_ingresos += ing
            total_egresos += egr

            resumen.append({
                "Periodo": f"{anio}-{mes:02d}",
                "Etiqueta": f"{meses_es[mes]} {anio}",
                "Ingresos": ing,
                "Egresos": egr,
                "Saldo": saldo,
            })

        totales = {
            "Ingresos": total_ingresos,
            "Egresos": total_egresos,
            "Saldo": total_ingresos - total_egresos,
        }

        return jsonify({
            "success": True,
            "resumen": resumen,
            "totales": totales
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error obteniendo resumen financiero: {str(e)}"
        }), 500
