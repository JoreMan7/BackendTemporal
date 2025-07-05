"""
Servicios de autenticación y autorización
Maneja JWT tokens y validación de roles
"""
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity
from models.UserModel import UserModel
from utils.Security import Security
import logging

class AuthService:
    """Servicio para manejo de autenticación"""
    
    @staticmethod
    def login(email, password):
        """
        Autentica un usuario y genera tokens JWT
        
        Args:
            email (str): Email del usuario
            password (str): Contraseña del usuario
            
        Returns:
            dict: Resultado de la autenticación con tokens
        """
        try:
            # Autenticar usuario
            user = UserModel.authenticate_user(email, password)
            
            if not user:
                return {
                    'success': False,
                    'message': 'Credenciales inválidas'
                }
            
            # Crear tokens JWT
            access_token = create_access_token(
                identity=user['IdUsuario'],
                additional_claims={
                    'rol': user['rol'],
                    'nombre': user['Nombre'],
                    'apellido': user['Apellido']
                }
            )
            
            refresh_token = create_refresh_token(identity=user['IdUsuario'])
            
            return {
                'success': True,
                'message': 'Login exitoso',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user['IdUsuario'],
                    'nombre': user['Nombre'],
                    'apellido': user['Apellido'],
                    'email': user['CorreoElectronico'],
                    'rol': user['rol'],
                    'telefono': user['Telefono']
                }
            }
            
        except Exception as e:
            logging.error(f"Error en login: {str(e)}")
            return {
                'success': False,
                'message': 'Error interno del servidor'
            }
    
    @staticmethod
    def refresh_token():
        """
        Genera un nuevo access token usando el refresh token
        
        Returns:
            dict: Nuevo access token
        """
        try:
            current_user_id = get_jwt_identity()
            user = UserModel.get_user_by_id(current_user_id)
            
            if not user:
                return {
                    'success': False,
                    'message': 'Usuario no encontrado'
                }
            
            new_token = create_access_token(
                identity=current_user_id,
                additional_claims={
                    'rol': user['rol'],
                    'nombre': user['Nombre'],
                    'apellido': user['Apellido']
                }
            )
            
            return {
                'success': True,
                'access_token': new_token
            }
            
        except Exception as e:
            logging.error(f"Error refrescando token: {str(e)}")
            return {
                'success': False,
                'message': 'Error interno del servidor'
            }
    
    @staticmethod
    def register(user_data):
        """
        Registra un nuevo usuario en el sistema
        
        Args:
            user_data (dict): Datos del usuario a registrar
            
        Returns:
            dict: Resultado del registro
        """
        try:
            # Validar datos requeridos
            required_fields = ['nombre', 'apellido', 'correo_electronico', 'password', 'numero_documento']
            
            for field in required_fields:
                if not user_data.get(field):
                    return {
                        'success': False,
                        'message': f'El campo {field} es requerido'
                    }
            
            # Crear usuario
            result = UserModel.create_user(user_data)
            
            return result
            
        except Exception as e:
            logging.error(f"Error en registro: {str(e)}")
            return {
                'success': False,
                'message': 'Error interno del servidor'
            }
    
    @staticmethod
    def validate_role(required_roles):
        """
        Decorador para validar roles de usuario
        
        Args:
            required_roles (list): Lista de roles permitidos
            
        Returns:
            function: Decorador
        """
        def decorator(f):
            def decorated_function(*args, **kwargs):
                try:
                    current_user_id = get_jwt_identity()
                    user = UserModel.get_user_by_id(current_user_id)
                    
                    if not user or user['rol'] not in required_roles:
                        return {
                            'success': False,
                            'message': 'No tienes permisos para realizar esta acción'
                        }, 403
                    
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    logging.error(f"Error validando rol: {str(e)}")
                    return {
                        'success': False,
                        'message': 'Error de autorización'
                    }, 500
            
            decorated_function.__name__ = f.__name__
            return decorated_function
        return decorator
