"""
Rutas principales de la aplicación
Incluye endpoints generales y de información
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from database.db_mysql import execute_query
import logging
from datetime import datetime

# Crear blueprint principal
index_bp = Blueprint('index', __name__)

@index_bp.route('/', methods=['GET'])
def index():
    """
    Endpoint principal de la API (PÚBLICO)
    
    Returns:
        JSON: Información básica de la API
    """
    return jsonify({
        'message': 'API de Gestión Eclesial',
        'version': '1.0.0',
        'status': 'active',
        'endpoints': {
            'public': {
                'info': 'GET /api/',
                'health': 'GET /api/health',
                'login': 'POST /api/auth/login',
                'register': 'POST /api/auth/register'
            },
            'protected': {
                'profile': 'GET /api/auth/profile (requiere token)',
                'habitantes': 'GET /api/habitantes (requiere token)',
                'parroquias': 'GET /api/parroquias (requiere token)',
                'stats': 'GET /api/dashboard/stats (requiere token)'
            }
        },
        'authentication': {
            'type': 'JWT Bearer Token',
            'header': 'Authorization: Bearer <token>',
            'how_to_get_token': 'POST /api/auth/login con email y password'
        }
    }), 200

@index_bp.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint para verificar el estado de la API y base de datos (PÚBLICO)
    
    Returns:
        JSON: Estado de salud del sistema
    """
    try:
        # Verificar conexión a base de datos
        result = execute_query("SELECT 1 as test", fetch_one=True)
        
        if result:
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': str(datetime.now()),
                'message': 'Sistema funcionando correctamente'
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'timestamp': str(datetime.now())
            }), 503
            
    except Exception as e:
        logging.error(f"Error en health check: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'error',
            'error': str(e),
            'timestamp': str(datetime.now())
        }), 503

@index_bp.route('/test-db', methods=['GET'])
def test_database():
    """
    Endpoint para probar la base de datos (PÚBLICO)
    
    Returns:
        JSON: Resultado de la prueba de base de datos
    """
    try:
        # Probar consultas básicas
        tests = {}
        
        # Test 1: Contar usuarios
        result = execute_query("SELECT COUNT(*) as total FROM usuario", fetch_one=True)
        tests['usuarios_count'] = result['total'] if result else 0
        
        # Test 2: Contar habitantes
        result = execute_query("SELECT COUNT(*) as total FROM habitantes", fetch_one=True)
        tests['habitantes_count'] = result['total'] if result else 0
        
        # Test 3: Verificar tipos de usuario
        result = execute_query("SELECT COUNT(*) as total FROM tipousuario", fetch_one=True)
        tests['tipos_usuario_count'] = result['total'] if result else 0
        
        return jsonify({
            'success': True,
            'message': 'Pruebas de base de datos completadas',
            'tests': tests,
            'timestamp': str(datetime.now())
        }), 200
        
    except Exception as e:
        logging.error(f"Error en test de base de datos: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error en pruebas de base de datos',
            'error': str(e),
            'timestamp': str(datetime.now())
        }), 500

@index_bp.route('/habitantes', methods=['GET'])
@jwt_required()
def get_habitantes():
    """
    Endpoint para obtener lista de habitantes (REQUIERE TOKEN)
    
    Returns:
        JSON: Lista de habitantes
    """
    try:
        current_user_id = get_jwt_identity()
        logging.info(f"Usuario {current_user_id} solicitando lista de habitantes")
        
        query = """
            SELECT 
                IdHabitante,
                Nombre,
                Apellido,
                NumeroDocumento,
                Telefono,
                CorreoElectronico,
                Direccion
            FROM habitantes
            ORDER BY Nombre, Apellido
            LIMIT 100
        """
        
        habitantes = execute_query(query, fetch_all=True)
        
        return jsonify({
            'success': True,
            'habitantes': habitantes,
            'total': len(habitantes)
        }), 200
        
    except Exception as e:
        logging.error(f"Error obteniendo habitantes: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@index_bp.route('/parroquias', methods=['GET'])
@jwt_required()
def get_parroquias():
    """
    Endpoint para obtener lista de parroquias (REQUIERE TOKEN)
    
    Returns:
        JSON: Lista de parroquias
    """
    try:
        current_user_id = get_jwt_identity()
        logging.info(f"Usuario {current_user_id} solicitando lista de parroquias")
        
        query = """
            SELECT 
                p.IdParroquia,
                p.Nombre,
                p.Direccion,
                p.Telefono,
                p.Nit,
                s.Descripcion as Sector
            FROM parroquia p
            LEFT JOIN sector s ON p.IdSector = s.IdSector
            ORDER BY p.Nombre
        """
        
        parroquias = execute_query(query, fetch_all=True)
        
        return jsonify({
            'success': True,
            'parroquias': parroquias,
            'total': len(parroquias)
        }), 200
        
    except Exception as e:
        logging.error(f"Error obteniendo parroquias: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@index_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """
    Endpoint para obtener estadísticas del dashboard (REQUIERE TOKEN)
    
    Returns:
        JSON: Estadísticas generales
    """
    try:
        current_user_id = get_jwt_identity()
        logging.info(f"Usuario {current_user_id} solicitando estadísticas del dashboard")
        
        stats = {}
        
        # Total de habitantes
        habitantes_query = "SELECT COUNT(*) as total FROM habitantes"
        habitantes_result = execute_query(habitantes_query, fetch_one=True)
        stats['total_habitantes'] = habitantes_result['total'] if habitantes_result else 0
        
        # Total de usuarios
        usuarios_query = "SELECT COUNT(*) as total FROM usuario"
        usuarios_result = execute_query(usuarios_query, fetch_one=True)
        stats['total_usuarios'] = usuarios_result['total'] if usuarios_result else 0
        
        # Total de parroquias
        parroquias_query = "SELECT COUNT(*) as total FROM parroquia"
        parroquias_result = execute_query(parroquias_query, fetch_one=True)
        stats['total_parroquias'] = parroquias_result['total'] if parroquias_result else 0
        
        # Citas pendientes
        citas_query = """
            SELECT COUNT(*) as total 
            FROM asignacioncita 
            WHERE IdEstadoCita = 1
        """
        citas_result = execute_query(citas_query, fetch_one=True)
        stats['citas_pendientes'] = citas_result['total'] if citas_result else 0
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logging.error(f"Error obteniendo estadísticas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500
