"""
Rutas para gestión de sacramentos de los habitantes
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from database.db_mysql import execute_query
from datetime import datetime
from utils import require_rol

sacramentos_bp = Blueprint('sacramentos', __name__)

# OBTENER SACRAMENTOS DE UN HABITANTE
sacramentos_bp.route('/habitante/<int:id>', methods=['GET'])
@jwt_required()
def obtener_sacramentos_habitante(id):
    try:
        query = """
            SELECT 
                hs.IdHabitante,
                hs.IdSacramento,
                ts.Descripcion AS Sacramento,
                ts.Costo,
                hs.FechaSacramento
            FROM habitante_sacramento hs
            JOIN tiposacramentos ts ON hs.IdSacramento = ts.IdSacramento
            WHERE hs.IdHabitante = %s
            ORDER BY hs.FechaSacramento
        """
        sacramentos = execute_query(query, (id,))
        return jsonify({'success': True, 'sacramentos': sacramentos}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# AGREGAR SACRAMENTO A HABITANTE
@sacramentos_bp.route('/habitante/<int:id>', methods=['POST'])
@jwt_required()
def agregar_sacramento_habitante(id):
    try:
        data = request.get_json()
        
        # Verificar que el habitante existe
        habitante_query = "SELECT IdHabitante FROM habitantes WHERE IdHabitante = %s AND Activo = 1"
        habitante = execute_query(habitante_query, (id,), fetch_one=True)
        if not habitante:
            return jsonify({'success': False, 'message': 'Habitante no encontrado'}), 404
        
        # Verificar que el sacramento existe
        sacramento_query = "SELECT IdSacramento FROM tiposacramentos WHERE IdSacramento = %s"
        sacramento = execute_query(sacramento_query, (data.get('id_sacramento'),), fetch_one=True)
        if not sacramento:
            return jsonify({'success': False, 'message': 'Sacramento no válido'}), 400
        
        # Verificar que no existe ya esta combinación
        existe_query = "SELECT 1 FROM habitante_sacramento WHERE IdHabitante = %s AND IdSacramento = %s"
        existe = execute_query(existe_query, (id, data.get('id_sacramento')), fetch_one=True)
        if existe:
            return jsonify({'success': False, 'message': 'El habitante ya tiene este sacramento'}), 400
        
        # Insertar nuevo sacramento
        insert_query = """
            INSERT INTO habitante_sacramento (IdHabitante, IdSacramento, FechaSacramento)
            VALUES (%s, %s, %s)
        """
        execute_query(insert_query, (
            id, 
            data.get('id_sacramento'), 
            data.get('fecha_sacramento')
        ))
        
        return jsonify({'success': True, 'message': 'Sacramento agregado exitosamente'}), 201
        
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al agregar sacramento: {str(e)}"}), 500

# ACTUALIZAR FECHA DE SACRAMENTO
@sacramentos_bp.route('/habitante/<int:id_habitante>/sacramento/<int:id_sacramento>', methods=['PUT'])
@jwt_required()
def actualizar_sacramento_habitante(id_habitante, id_sacramento):
    try:
        data = request.get_json()
        
        query = """
            UPDATE habitante_sacramento 
            SET FechaSacramento = %s 
            WHERE IdHabitante = %s AND IdSacramento = %s
        """
        updated = execute_query(query, (
            data.get('fecha_sacramento'),
            id_habitante,
            id_sacramento
        ))
        
        if updated:
            return jsonify({'success': True, 'message': 'Sacramento actualizado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Sacramento no encontrado'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al actualizar sacramento: {str(e)}"}), 500

# ELIMINAR SACRAMENTO DE HABITANTE
@sacramentos_bp.route('/habitante/<int:id_habitante>/sacramento/<int:id_sacramento>', methods=['DELETE'])
@jwt_required()
def eliminar_sacramento_habitante(id_habitante, id_sacramento):
    try:
        query = "DELETE FROM habitante_sacramento WHERE IdHabitante = %s AND IdSacramento = %s"
        deleted = execute_query(query, (id_habitante, id_sacramento))
        
        if deleted:
            return jsonify({'success': True, 'message': 'Sacramento eliminado exitosamente'}), 200
        return jsonify({'success': False, 'message': 'Sacramento no encontrado'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error al eliminar sacramento: {str(e)}"}), 500

# OBTENER CATÁLOGO DE SACRAMENTOS DISPONIBLES
@sacramentos_bp.route('/catalogo', methods=['GET'])
@jwt_required()
def obtener_catalogo_sacramentos():
    try:
        query = "SELECT IdSacramento, Descripcion, Costo FROM tiposacramentos ORDER BY IdSacramento"
        sacramentos = execute_query(query)
        return jsonify({'success': True, 'sacramentos': sacramentos}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500