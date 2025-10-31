"""
Rutas de autenticación y autorización
Maneja login, registro, refresh de tokens y gestión de usuarios
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services import AuthService
from models.UserModel import UserModel
from utils.Security import Security
import logging

# Crear blueprint para autenticación
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Endpoint para autenticación de usuarios por documento
    
    Body JSON:
    {
        "document_type": "1",
        "document_number": "12345678",
        "password": "contraseña"
    }
    
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
        
        # Obtener datos del formulario
        document_type = data.get('document_type')
        document_number = data.get('document_number')
        password = data.get('password')
        
        #print(document_number, document_type, password)

        # Validaciones básicas
        if not document_type:
            return jsonify({
                'success': False,
                'message': 'Tipo de documento es requerido'
            }), 400
            
        if not document_number:
            return jsonify({
                'success': False,
                'message': 'Número de documento es requerido'
            }), 400
            
        if not password:
            return jsonify({
                'success': False,
                'message': 'Contraseña es requerida'
            }), 400
        
        # Validar formato del número de documento
        document_number = str(document_number).strip()
        if not document_number.isdigit():
            return jsonify({
                'success': False,
                'message': 'El número de documento debe contener solo números'
            }), 400
        
        # Log del intento de login (sin mostrar contraseña)
        logging.info(f"Intento de login - Tipo: {document_type}, Documento: {document_number}")
        
        # Autenticar usuario por documento
        result = AuthService.login_by_document(document_type, document_number, password)
        
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
    
    Body JSON:
    {
        "nombre": "Juan",
        "apellido": "Pérez",
        "id_tipo_documento": "1",
        "numero_documento": "12345678",
        "password": "MiContraseña123!",
        "correo_electronico": "juan@email.com",
        "telefono": "3001234567"
    }
    
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
        
        # Validar email si se proporciona
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
        
        # Validar número de documento
        document_number = str(data.get('numero_documento', '')).strip()
        if document_number and not document_number.isdigit():
            return jsonify({
                'success': False,
                'message': 'El número de documento debe contener solo números'
            }), 400
        
        # Actualizar el número de documento limpio
        data['numero_documento'] = document_number
        
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


@jwt_required()
def get_profile():
    """
    Endpoint para obtener perfil del usuario actual
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        JSON: Datos del perfil del usuario
    """
    try:
        current_user_id = get_jwt_identity()   # 👈 AQUÍ ESTÁ EL PROBLEMA
        user = UserModel.get_user_by_id(current_user_id)  # 👈 SE LLAMA SIN CASTEAR
        
        if user:
            # Remover datos sensibles
            user_data = {
                'id': user['IdUsuario'],
                'nombre': user['Nombre'],
                'apellido': user['Apellido'],
                'email': user.get('CorreoElectronico'),
                'telefono': user.get('Telefono'),
                'documento': user['NumeroDocumento'],
                'tipo_documento': user.get('IdTipoDocumento'),
                'tipo_documento_nombre': user.get('tipo_documento_nombre'),
                'rol': user.get('rol', 'Usuario'),
                'direccion': user.get('Direccion')
            }
            
            return jsonify({
                'success': True,
                'user': user_data
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


@auth_bp.route('/document-types', methods=['GET'])
def get_document_types():
    """
    Endpoint para obtener los tipos de documento disponibles
    
    Returns:
        JSON: Lista de tipos de documento
    """
    try:
        result = AuthService.get_document_types()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logging.error(f"Error en endpoint document-types: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor',
            'document_types': []
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Endpoint para cerrar sesión
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        JSON: Confirmación de logout
    """
    try:
        # En una implementación completa, aquí se podría agregar el token a una blacklist
        # Por ahora, simplemente confirmamos el logout
        
        return jsonify({
            'success': True,
            'message': 'Sesión cerrada exitosamente'
        }), 200
        
    except Exception as e:
        logging.error(f"Error en endpoint logout: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error interno del servidor'
        }), 500
