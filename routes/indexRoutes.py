"""
Rutas principales de la API
============================
Proporciona información general del sistema, estado de salud y listado de endpoints disponibles.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db_mysql import execute_query
from datetime import datetime
import logging

index_bp = Blueprint('index', __name__)

# ======================================
# INFORMACIÓN PRINCIPAL DE LA API
# ======================================
@index_bp.route('/', methods=['GET'])
def index():
    """
    Endpoint raíz (PÚBLICO)
    Muestra información general del proyecto y todas las rutas disponibles.
    """
    return jsonify({
        'proyecto': 'Gestión Eclesial',
        'version': '1.0.0',
        'estado': 'activo',
        'ultima_actualizacion': str(datetime.now()),
        'descripcion': (
            'API modular desarrollada en Flask para la gestión de parroquias, habitantes, grupos, '
            'usuarios, cursos, tareas y configuraciones auxiliares.'
        ),
        'endpoints': {
            'Autenticación': {
                'POST /api/auth/login': 'Iniciar sesión (retorna token JWT)',
                'POST /api/auth/register': 'Registrar nuevo usuario (si está habilitado)',
                'GET /api/auth/profile': 'Consultar perfil autenticado'
            },
            'Sistema': {
                'GET /api/': 'Información general de la API',
                'GET /api/health': 'Verifica conexión con base de datos',
                'GET /api/test-db': 'Prueba de integridad de tablas principales',
                'GET /api/dashboard/stats': 'Estadísticas globales'
            },
            'Opciones / Catálogos': {
                'GET /api/opciones': 'Listar valores de catálogos (documentos, sexos, religiones, etc.)'
            },
            'Habitantes': {
                'GET /api/habitantes/': 'Listar habitantes (requiere token)',
                'GET /api/habitantes/<id>': 'Obtener habitante específico',
                'POST /api/habitantes/': 'Registrar nuevo habitante',
                'PUT /api/habitantes/<id>': 'Actualizar habitante existente',
                'PATCH /api/habitantes/<id>/desactivar': 'Desactivar habitante (soft delete)'
            },
            'Sacramentos': {
                'GET /api/sacramentos/': 'Listar sacramentos disponibles',
                'POST /api/sacramentos/': 'Registrar nuevo sacramento (Administrador)',
                'PUT /api/sacramentos/<id>': 'Actualizar sacramento (Administrador)',
                'PATCH /api/sacramentos/<id>/desactivar': 'Desactivar sacramento'
            },
            'Grupos de Ayudantes': {
                'GET /api/grupos/': 'Listar todos los grupos',
                'GET /api/grupos/<id>': 'Obtener detalles de grupo',
                'POST /api/grupos/': 'Crear grupo (solo Administrador)',
                'PUT /api/grupos/<id>': 'Editar grupo (solo Administrador)',
                'PATCH /api/grupos/<id>/desactivar': 'Desactivar grupo (solo Administrador)'
            },
            'Miembros de Grupo': {
                'GET /api/grupos/<id>/miembros': 'Listar miembros de grupo',
                'POST /api/grupos/<id>/miembros': 'Agregar miembro (Administrador)',
                'PATCH /api/grupos/<id>/miembros/<id_miembro>/desactivar': 'Desactivar miembro'
            },
            'Cursos de Grupo': {
                'GET /api/grupos/<id>/cursos': 'Listar cursos asignados al grupo',
                'POST /api/grupos/<id>/cursos': 'Asignar curso (Administrador)',
                'POST /api/grupos/<id>/cursos/<id_curso>/avanzar': 'Registrar avance del curso'
            },
            'Tareas de Grupo': {
                'GET /api/grupos/<id>/tareas': 'Listar tareas asignadas',
                'POST /api/grupos/<id>/tareas': 'Asignar tarea (Administrador o Líder)',
                'PUT /api/grupos/<id>/tareas/<id_tarea>': 'Actualizar estado de tarea'
            },
            'Usuarios del Sistema': {
                'GET /api/usuarios/': 'Listar todos los usuarios (solo Administrador)',
                'GET /api/usuarios/<id>': 'Ver usuario específico',
                'POST /api/usuarios/': 'Crear usuario (solo Administrador)',
                'PUT /api/usuarios/<id>': 'Editar usuario (solo Administrador)',
                'PATCH /api/usuarios/<id>/desactivar': 'Desactivar usuario (solo Administrador)'
            }
        },
        'autenticacion': {
            'tipo': 'JWT Bearer Token',
            'encabezado': 'Authorization: Bearer <token>',
            'obtener_token': 'POST /api/auth/login con credenciales válidas'
        }
    }), 200


# ======================================
# VERIFICAR ESTADO DE LA BASE DE DATOS
# ======================================
@index_bp.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint público para verificar la conexión a la base de datos.
    """
    try:
        result = execute_query("SELECT 1 AS test", fetch_one=True)
        if result:
            return jsonify({
                'status': 'ok',
                'database': 'connected',
                'timestamp': str(datetime.now())
            }), 200
        else:
            return jsonify({'status': 'error', 'database': 'disconnected'}), 503
    except Exception as e:
        logging.error(f"Error en health_check: {str(e)}")
        return jsonify({
            'status': 'error',
            'database': 'error',
            'message': str(e)
        }), 503


# ======================================
# PRUEBA DE CONEXIÓN GLOBAL
# ======================================
@index_bp.route('/test-db', methods=['GET'])
def test_database():
    """
    Ejecuta pruebas básicas sobre las tablas principales.
    """
    try:
        tests = {
            'usuarios': execute_query("SELECT COUNT(*) AS total FROM usuario", fetch_one=True)['total'],
            'habitantes': execute_query("SELECT COUNT(*) AS total FROM habitantes", fetch_one=True)['total'],
            'tipos_usuario': execute_query("SELECT COUNT(*) AS total FROM tipousuario", fetch_one=True)['total'],
            'grupos_ayudantes': execute_query("SELECT COUNT(*) AS total FROM grupoayudantes", fetch_one=True)['total']
        }

        return jsonify({
            'success': True,
            'message': 'Prueba de base de datos completada exitosamente',
            'tests': tests,
            'timestamp': str(datetime.now())
        }), 200
    except Exception as e:
        logging.error(f"Error en test_database: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error en pruebas de base de datos',
            'error': str(e)
        }), 500


# ======================================
# DASHBOARD DE ESTADÍSTICAS
# ======================================
@index_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """
    Retorna estadísticas generales del sistema (requiere autenticación).
    """
    try:
        current_user_id = get_jwt_identity()
        logging.info(f"Usuario {current_user_id} solicitando estadísticas globales.")

        stats = {
            'total_habitantes': execute_query("SELECT COUNT(*) AS total FROM habitantes", fetch_one=True)['total'],
            'total_usuarios': execute_query("SELECT COUNT(*) AS total FROM usuario", fetch_one=True)['total'],
            'total_parroquias': execute_query("SELECT COUNT(*) AS total FROM parroquia", fetch_one=True)['total'],
            'total_grupos': execute_query("SELECT COUNT(*) AS total FROM grupoayudantes", fetch_one=True)['total']
        }

        return jsonify({'success': True, 'stats': stats}), 200
    except Exception as e:
        logging.error(f"Error obteniendo estadísticas: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
