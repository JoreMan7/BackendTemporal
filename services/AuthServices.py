"""
Servicios de autenticación y autorización
Maneja JWT tokens y validación de roles
"""
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity
from models import UserModel
from utils import Security
from database import execute_query
import logging
from werkzeug.security import check_password_hash

class AuthService:
    """Servicio para manejo de autenticación"""
    
    @staticmethod
    def _create_login_response(user):
        """
        Crea la respuesta de login con tokens
        """
        try:
            # ✅ Asegurar que el identity sea string
            user_id = str(user['IdUsuario'])
            
            # ✅ Crear tokens JWT con identity correcta
            access_token = create_access_token(
                identity=user_id,
                additional_claims={
                    'rol': user.get('rol', 'Usuario'),
                    'nombre': user['Nombre'],
                    'apellido': user['Apellido'],
                    'documento': user['NumeroDocumento'],
                    'tipo_documento': user['IdTipoDocumento']  # 👈 QUITA el .get()
                }
            )
            
            refresh_token = create_refresh_token(identity=user_id)
            
            return {
                'success': True,
                'message': 'Login exitoso',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user_id,
                    'nombre': user['Nombre'],
                    'apellido': user['Apellido'],
                    'email': user.get('CorreoElectronico'),
                    'rol': user.get('rol', 'Usuario'),
                    'telefono': user.get('Telefono'),
                    'documento': user['NumeroDocumento'],
                    'tipo_documento': user['IdTipoDocumento'],  # 👈 QUITA el .get()
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
    def get_user_by_document(document_type, document_number):
        """
        Obtiene el usuario según su documento y tipo de documento.
        Incluye campos de seguridad para bloqueo.
        """
        try:
            query = """
                SELECT 
                    u.IdUsuario AS id,
                    u.login_attempts AS login_attempts,
                    u.locked_until AS locked_until,
                    u.Contraseña AS password_hash,
                    u.IdHabitante AS id_habitante,
                    u.Activo as ActivoUsuario,
                    h.Nombre AS nombre,
                    h.Apellido AS apellido,
                    h.NumeroDocumento AS numero_documento,
                    h.IdTipoDocumento AS tipo_documento,
                    h.Activo as ActivoHabitante
                FROM usuario u
                JOIN habitantes h ON u.IdHabitante = h.IdHabitante
                WHERE h.NumeroDocumento = %s AND h.IdTipoDocumento = %s
                LIMIT 1
            """
            result = execute_query(query, (document_number, document_type), fetch_one=True)

            # Debug: Ver qué datos se están recuperando
            if result:
                logging.info(f"Usuario encontrado: ID={result['id']}, Intentos={result.get('login_attempts', 0)}, Bloqueado hasta={result.get('locked_until')}")
            else:
                logging.warning(f"Usuario NO encontrado: {document_type}-{document_number}")

            return result

        except Exception as e:
            logging.error(f"get_user_by_document error: {e}")
            return None
    @staticmethod
    def update_login_security_state(user_id, login_attempts, locked_until):
        try:
            query = """
                UPDATE usuario
                SET login_attempts = %s,
                    locked_until = %s
                WHERE IdUsuario = %s
            """
            execute_query(query, (login_attempts, locked_until, user_id))
            return True
        except Exception as e:
            logging.error(f"update_login_security_state error: {e}")
            return False

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

            # Limpiar número de documento
            document_number = str(document_number).strip()

            # 🔍 PRIMERO: Buscar usuario y verificar estado de bloqueo
            user = AuthService.get_user_by_document(document_type, document_number)

            if not user:
                logging.warning(f"Usuario no encontrado → {document_type}-{document_number}")
                return {
                    'success': False,
                    'message': 'Tipo de documento, número de documento o contraseña incorrectos'
                }

            # 🔒 VERIFICAR BLOQUEO ACTUAL
            locked_until = user.get('locked_until')
            if locked_until:
                from datetime import datetime
                now = datetime.now()

                # Convertir string a datetime si es necesario
                if isinstance(locked_until, str):
                    try:
                        locked_until = datetime.strptime(locked_until, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        locked_until = datetime.strptime(locked_until, '%Y-%m-%d %H:%M:%S.%f')

                if locked_until > now:
                    remaining_minutes = int((locked_until - now).total_seconds() / 60)
                    remaining_seconds = int((locked_until - now).total_seconds() % 60)

                    logging.warning(f"Usuario bloqueado → {document_type}-{document_number}. Tiempo restante: {remaining_minutes}m {remaining_seconds}s")
                    return {
                        'success': False,
                        'locked': True,
                        'message': f'Usuario bloqueado. Intente nuevamente en {remaining_minutes} minutos',
                        'locked_until': locked_until.strftime('%Y-%m-%d %H:%M:%S')
                    }
                else:
                    # ⏰ Desbloquear usuario si el tiempo expiró
                    logging.info(f"Desbloqueando usuario → {document_type}-{document_number}")
                    AuthService.update_login_security_state(user['id'], 0, None)

            # 🔐 INTENTAR AUTENTICACIÓN
            authenticated_user = UserModel.authenticate_user_by_document(document_type, document_number, password)

            if authenticated_user:
                # ✅ LOGIN EXITOSO - Resetear intentos fallidos
                AuthService.update_login_security_state(authenticated_user['IdUsuario'], 0, None)

                # 🧱 Validar estado activo
                activo_usuario = authenticated_user.get('ActivoUsuario', 1)
                activo_habitante = authenticated_user.get('ActivoHabitante', 1)

                if activo_usuario == 0 or activo_habitante == 0:
                    return {
                        'success': False,
                        'message': 'Usuario inactivo. Contacte al administrador del sistema.'
                    }

                logging.info(f"Login exitoso → {authenticated_user['Nombre']} {authenticated_user['Apellido']}")
                return AuthService._create_login_response(authenticated_user)

            else:
                # ❌ LOGIN FALLIDO - Incrementar intentos
                current_attempts = user.get('login_attempts', 0) + 1
                logging.warning(f"Intento fallido #{current_attempts} → {document_type}-{document_number}")

                # 🚨 VERIFICAR SI SUPERÓ EL LÍMITE
                from config import Config
                from datetime import datetime, timedelta

                locked_until = None
                if current_attempts >= Config.MAX_LOGIN_ATTEMPTS:
                    # Calcular bloqueo progresivo
                    lock_count = current_attempts - Config.MAX_LOGIN_ATTEMPTS
                    lock_duration_minutes = AuthService.calculate_lock_duration(lock_count)
                    locked_until = datetime.now() + timedelta(minutes=lock_duration_minutes)

                    logging.warning(f"Bloqueando usuario → {document_type}-{document_number} por {lock_duration_minutes} minutos")

                # 📝 ACTUALIZAR ESTADO DE SEGURIDAD
                AuthService.update_login_security_state(user['id'], current_attempts, locked_until)

                if locked_until:
                    return {
                        'success': False,
                        'locked': True,
                        'message': f'Demasiados intentos fallidos. Usuario bloqueado por {lock_duration_minutes} minutos',
                        'locked_until': locked_until.strftime('%Y-%m-%d %H:%M:%S'),
                        'attempts': current_attempts
                    }
                else:
                    attempts_remaining = Config.MAX_LOGIN_ATTEMPTS - current_attempts
                    return {
                        'success': False,
                        'message': f'Credenciales incorrectas. Le quedan {attempts_remaining} intento(s)',
                        'attempts': current_attempts,
                        'attempts_remaining': attempts_remaining
                    }

        except Exception as e:
            logging.error(f"Error en login por documento: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': 'Error interno al procesar el inicio de sesión'
            }
    
    @staticmethod
    def calculate_lock_duration(lock_count):
        """
        Calcula la duración del bloqueo usando multiplicador progresivo
        
        Args:
            lock_count (int): Número de bloqueos previos (0 = primer bloqueo)
            
        Returns:
            int: Duración en minutos
        """
        from config import Config
        
        base_minutes = Config.BASE_LOCK_DURATION_MINUTES
        multiplier = Config.LOCK_MULTIPLIER
        max_minutes = Config.MAX_LOCK_DURATION_MINUTES
        
        # Fórmula: base * (multiplicador ^ lock_count)
        duration = base_minutes * (multiplier ** lock_count)
        
        # No exceder el máximo
        return min(int(duration), max_minutes)
    
    @staticmethod
    def handle_failed_login(user_id, current_attempts):
        """
        Maneja el intento fallido de login con bloqueo progresivo
        """
        try:
            from datetime import datetime, timedelta
            from config import Config
            
            new_attempts = current_attempts + 1
            
            # Calcular duración del bloqueo basado en intentos previos
            lock_count = max(0, new_attempts - Config.MAX_LOGIN_ATTEMPTS)
            lock_duration_minutes = AuthService.calculate_lock_duration(lock_count)
            
            locked_until = None
            if new_attempts >= Config.MAX_LOGIN_ATTEMPTS:
                locked_until = datetime.now() + timedelta(minutes=lock_duration_minutes)
                logging.warning(
                    f"Usuario {user_id} bloqueado por {lock_duration_minutes} minutos "
                    f"(intento #{new_attempts}, lock_count: {lock_count})"
                )
            
            # Actualizar estado de seguridad
            AuthService.update_login_security_state(user_id, new_attempts, locked_until)
            
            return {
                'locked': locked_until is not None,
                'attempts_remaining': max(0, Config.MAX_LOGIN_ATTEMPTS - new_attempts),
                'locked_until': locked_until,
                'lock_duration_minutes': lock_duration_minutes
            }
            
        except Exception as e:
            logging.error(f"Error en handle_failed_login: {str(e)}")
            return {'locked': False, 'attempts_remaining': 0}