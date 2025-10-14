"""
Rutas para gestión de sacramentos de los habitantes
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database.db_mysql import execute_query
from datetime import datetime
from utils import require_rol

sacramentos_bp = Blueprint('sacramentos', __name__)

# ✅ LISTAR TODOS LOS TIPOS DE SACRAMENTO
@sacramentos_bp.route('/api/sacramentos/tipos', methods=['GET'])
@jwt_required()
def listar_tipos_sacramento():
    try:
        query = "SELECT IdSacramento AS id, Descripcion AS descripcion, Costo FROM tiposacramentos"
        tipos = execute_query(query)
        return jsonify({'success': True, 'tipos': tipos}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al obtener tipos de sacramentos: {str(e)}"}), 500


# ✅ OBTENER SACRAMENTOS DE UN HABITANTE
@sacramentos_bp.route('/api/habitantes/<int:id>/sacramentos', methods=['GET'])
@jwt_required()
def obtener_sacramentos(id):
    try:
        query = """
            SELECT 
                s.IdSacramento AS id_sacramento,
                s.Descripcion AS sacramento,
                hs.FechaSacramento AS fecha
            FROM habitante_sacramento hs
            INNER JOIN tiposacramentos s ON hs.IdSacramento = s.IdSacramento
            WHERE hs.IdHabitante = %s
        """
        sacramentos = execute_query(query, (id,))
        return jsonify({'success': True, 'sacramentos': sacramentos}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al obtener sacramentos: {str(e)}"}), 500


# ✅ REGISTRAR SACRAMENTO A UN HABITANTE
@sacramentos_bp.route('/api/habitantes/<int:id>/sacramentos', methods=['POST'])
@jwt_required()
@require_rol('Administrador')
def registrar_sacramento(id):
    try:
        data = request.get_json()
        fecha = data.get('fecha_sacramento') or datetime.now().strftime('%Y-%m-%d')

        query = """
            INSERT INTO habitante_sacramento (IdHabitante, IdSacramento, FechaSacramento)
            VALUES (%s, %s, %s)
        """
        params = (id, data.get('id_sacramento'), fecha)
        execute_query(query, params)

        return jsonify({'success': True, 'message': 'Sacramento registrado exitosamente'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al registrar sacramento: {str(e)}"}), 500


# ✅ ELIMINAR SACRAMENTO DE UN HABITANTE
@sacramentos_bp.route('/api/habitantes/<int:id>/sacramentos/<int:id_sacramento>', methods=['DELETE'])
@jwt_required()
@require_rol('Administrador')
def eliminar_sacramento(id, id_sacramento):
    try:
        query = "DELETE FROM habitante_sacramento WHERE IdHabitante=%s AND IdSacramento=%s"
        deleted = execute_query(query, (id, id_sacramento))
        if deleted:
            return jsonify({'success': True, 'message': 'Sacramento eliminado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Sacramento no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al eliminar sacramento: {str(e)}"}), 500
