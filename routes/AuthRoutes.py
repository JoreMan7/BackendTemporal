"""
Rutas de autenticación y autorización
Maneja login, registro, refresh de tokens y gestión de usuarios
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.AuthServices import AuthService
from models.UserModel import UserModel
from utils.Security import Security
import logging

# Crear blueprint para autenticación
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Endpoint para autenticación de usuarios
    
    Returns:
        JSON: Resultado de la autenticación con tokens
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos requeridos'
            }), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email y contraseña son requeridos'
            }), 400
        
        # Validar formato de email
        if not Security.validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Formato de email inválido'
            }), 400
        
        # Autenticar usuario
        result = AuthService.login(email, password)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logging.error(f"Error en endpoint login: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Endpoint para registro de nuevos usuarios
    
    Returns:
        JSON: Resultado del registro
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos requeridos'
            }), 400
        
        # Validar email
        email = data.get('correo_electronico')
        if email and not Security.validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Formato de email inválido'
            }), 400
        
        # Validar contraseña
        password = data.get('password')
        if password:
            password_validation = Security.validate_password(password)
            if not password_validation['valid']:
                return jsonify({
                    'success': False,
                    'message': 'Contraseña no cumple con los requisitos',
                    'errors': password_validation['errors']
                }), 400
        
        # Registrar usuario
        result = AuthService.register(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Error en endpoint register: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Endpoint para refrescar access token
    
    Returns:
        JSON: Nuevo access token
    """
    try:
        result = AuthService.refresh_token()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Error en endpoint refresh: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Endpoint para obtener perfil del usuario actual
    
    Returns:
        JSON: Datos del perfil del usuario
    """
    try:
        current_user_id = get_jwt_identity()
        user = UserModel.get_user_by_id(current_user_id)
        
        if user:
            return jsonify({
                'success': True,
                'user': user
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
            
    except Exception as e:
        logging.error(f"Error en endpoint profile: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Endpoint para actualizar perfil del usuario actual
    
    Returns:
        JSON: Resultado de la actualización
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Datos requeridos'
            }), 400
        
        # Sanitizar datos de entrada
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = Security.sanitize_input(value)
        
        result = UserModel.update_user(current_user_id, data)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Error en endpoint update_profile: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """
    Endpoint para obtener todos los usuarios (solo administradores)
    
    Returns:
        JSON: Lista de usuarios
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = UserModel.get_user_by_id(current_user_id)
        
        # Verificar que sea administrador
        if not current_user or current_user['rol'] != 'administrador':
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para realizar esta acción'
            }), 403
        
        users = UserModel.get_all_users()
        
        return jsonify({
            'success': True,
            'users': users
        }), 200
        
    except Exception as e:
        logging.error(f"Error en endpoint get_users: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500
