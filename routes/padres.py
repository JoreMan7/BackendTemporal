"""
Rutas para búsqueda/listado de PADRES (tabla: padre)
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database import execute_query

padres_bp = Blueprint('padres', __name__)

@padres_bp.route('/', methods=['GET'])
@jwt_required()
def listar_padres():
    try:
        query = """
            SELECT 
                IdPadre,
                Nombre,
                Apellido,
                NumeroDocumento,
                Telefono,
                CorreoElectronico,
                Activo
            FROM padre
            WHERE Activo = 1
            ORDER BY Nombre, Apellido
        """
        padres = execute_query(query, fetch_all=True)
        return jsonify({"success": True, "padres": padres}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500