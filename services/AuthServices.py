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
    def login_by_document(document_type, document_number, password):
        """
        Autentica un usuario por tipo y número de documento.
        Retorna tokens JWT si las credenciales son válidas.
        """
        try:
            # 🧩 Validar campos obligatorios
            if not document_type or not document_number or not password:
                return {
                    'success': False,
                    'message': 'Todos los campos son requeridos'
                }
    
            # Limpiar número de documento (por si hay espacios)
            document_number = str(document_number).strip()
    
            # 🧠 Intentar autenticar usuario
            user = UserModel.authenticate_user_by_document(document_type, document_number, password)
    
            # ✅ Caso: usuario no encontrado o contraseña incorrecta
            if not user:
                logging.warning(f"Intento de login fallido → {document_type}-{document_number}")
                return {
                    'success': False,
                    'message': 'Tipo de documento, número de documento o contraseña incorrectos'
                }
    
            # 🧱 Validar estado activo del usuario y habitante
            activo_usuario = user.get('ActivoUsuario', 1)
            activo_habitante = user.get('ActivoHabitante', 1)
    
            if activo_usuario == 0 or activo_habitante == 0:
                logging.warning(f"Intento de login con usuario inactivo → {document_type}-{document_number}")
                return {
                    'success': False,
                    'message': 'Usuario inactivo. Contacte al administrador del sistema.'
                }
    
            # ✅ Si todo está bien → crear tokens JWT
            logging.info(
                f"Login exitoso → {user['Nombre']} {user['Apellido']} "
                f"(Doc: {document_type}-{document_number}, Rol: {user.get('rol', 'Usuario')})"
            )
    
            return AuthService._create_login_response(user)
    
        except Exception as e:
            logging.error(f"Error en login por documento: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': 'Error interno al procesar el inicio de sesión'
            }
    @staticmethod
    def _create_login_response(user):
        """
        Crea la respuesta de login con tokens
        
        Args:
            user (dict): Datos del usuario autenticado
            
        Returns:
            dict: Respuesta con tokens y datos del usuario
        """
        try:
            # Crear tokens JWT
            access_token = create_access_token(
            identity=str(user['IdUsuario']),
            additional_claims={
                'rol': user.get('rol', 'Usuario'),
                'nombre': user['Nombre'],
                'apellido': user['Apellido'],
                'documento': user['NumeroDocumento'],
                'tipo_documento': user.get('IdTipoDocumento')
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
                    'email': user.get('CorreoElectronico'),
                    'rol': user.get('rol', 'Usuario'),
                    'telefono': user.get('Telefono'),
                    'documento': user['NumeroDocumento'],
                    'tipo_documento': user.get('IdTipoDocumento'),
                    'tipo_documento_nombre': user.get('tipo_documento_nombre')
                }
            }
            
        except Exception as e:
            logging.error(f"Error creando respuesta de login: {str(e)}")
            return {
                'success': False,
                'message': 'Error generando tokens de acceso'
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
            required_fields = [
                'nombre', 'apellido', 'id_tipo_documento', 
                'numero_documento', 'password'
            ]
            
            for field in required_fields:
                if not user_data.get(field):
                    return {
                        'success': False,
                        'message': f'El campo {field} es requerido'
                    }
            
            # Verificar si el documento ya existe
            if UserModel.check_document_exists(
                user_data.get('id_tipo_documento'), 
                user_data.get('numero_documento')
            ):
                return {
                    'success': False,
                    'message': 'Ya existe un usuario con este documento'
                }
            
            # Validar email si se proporciona
            email = user_data.get('correo_electronico')
            if email and not Security.validate_email(email):
                return {
                    'success': False,
                    'message': 'Formato de email inválido'
                }
            
            # Validar contraseña
            password = user_data.get('password')
            password_validation = Security.validate_password(password)
            if not password_validation['valid']:
                return {
                    'success': False,
                    'message': 'Contraseña no cumple con los requisitos',
                    'errors': password_validation['errors']
                }
            
            # Crear usuario
            result = UserModel.create_user(user_data)
            
            if result['success']:
                logging.info(f"Usuario registrado exitosamente: {user_data.get('nombre')} {user_data.get('apellido')}")
            
            return result
            
        except Exception as e:
            logging.error(f"Error en registro: {str(e)}")
            return {
                'success': False,
                'message': 'Error interno del servidor'
            }
    
    @staticmethod
    def get_document_types():
        """
        Obtiene los tipos de documento disponibles
        
        Returns:
            dict: Lista de tipos de documento
        """
        try:
            from database.db_mysql import execute_query
            
            query = """
                SELECT IdTipoDocumento, TipoDocumento
                FROM tipodocumento
                ORDER BY IdTipoDocumento
            """
            
            document_types = execute_query(query, fetch_all=True)
            
            return {
                'success': True,
                'document_types': document_types or []
            }
            
        except Exception as e:
            logging.error(f"Error obteniendo tipos de documento: {str(e)}")
            return {
                'success': False,
                'message': 'Error obteniendo tipos de documento',
                'document_types': []
            }
