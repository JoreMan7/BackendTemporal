from flask import Blueprint, jsonify
from database import get_db_connection

opciones_bp = Blueprint("opciones", __name__)

@opciones_bp.route("/", methods=["GET"])
def get_opciones():
    conn = get_db_connection()
    cursor = conn.cursor()

    # tipodocumento: IdTipoDocumento, Descripcion
    cursor.execute("SELECT IdTipoDocumento AS id, Descripcion FROM tipodocumento")
    tipos_documento = cursor.fetchall()

    # sexos: IdSexo, Nombre
    cursor.execute("SELECT IdSexo AS id, Nombre FROM sexos")
    sexos = cursor.fetchall()

    # estados_civiles: IdEstadoCivil, Nombre
    cursor.execute("SELECT IdEstadoCivil AS id, Nombre FROM estados_civiles")
    estados_civiles = cursor.fetchall()

    # religiones: IdReligion, Nombre
    cursor.execute("SELECT IdReligion AS id, Nombre FROM religiones")
    religiones = cursor.fetchall()

    # tiposacramentos: IdSacramento, Costo, Descripcion
    cursor.execute("SELECT IdSacramento AS id, Costo, Descripcion FROM tiposacramentos")
    sacramentos = cursor.fetchall()

    # sector: IdSector, Nombre
    cursor.execute("SELECT IdSector AS id, Descripcion FROM sector")
    sectores = cursor.fetchall()

    # tipopoblacion: IdTipoPoblacion, Nombre, Descripcion
    cursor.execute("SELECT IdTipoPoblacion AS id, Nombre, Descripcion FROM tipopoblacion")
    poblaciones = cursor.fetchall()

    conn.close()

    return jsonify({
        "tiposDocumento": tipos_documento,
        "sexos": sexos,
        "estadosCiviles": estados_civiles,
        "religiones": religiones,
        "sacramentos": sacramentos,
        "sectores": sectores,
        "poblaciones": poblaciones
    })
