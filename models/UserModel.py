"""
Modelo para el manejo de usuarios del sistema
Incluye autenticación y gestión de roles
"""
from database.db_mysql import execute_query
from utils.Security import Security
import logging

class UserModel:
    """Modelo para gestión de usuarios"""
    
    @staticmethod
    def create_user(user_data):
        """
        Crea un nuevo usuario en el sistema
        
        Args:
            user_data (dict): Datos del usuario a crear
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            # Primero crear el habitante
            habitante_query = """
                INSERT INTO habitantes (
                    Nombre, Apellido, IdTipoDocumento, NumeroDocumento,
                    FechaNacimiento, Sexo, Telefono, CorreoElectronico, Direccion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            habitante_params = (
                user_data.get('nombre'),
                user_data.get('apellido'),
                user_data.get('id_tipo_documento'),
                user_data.get('numero_documento'),
                user_data.get('fecha_nacimiento'),
                user_data.get('sexo'),
                user_data.get('telefono'),
                user_data.get('correo_electronico'),
                user_data.get('direccion')
            )
            
            habitante_id = execute_query(habitante_query, habitante_params)
            
            if habitante_id:
                # Crear usuario
                password_hash = Security.generate_password_hash(user_data.get('password'))
                
                user_query = """
                    INSERT INTO usuario (IdTipoUsuario, Contraseña, IdHabitante)
                    VALUES (%s, %s, %s)
                """
                
                user_params = (
                    user_data.get('id_tipo_usuario'),
                    password_hash,
                    habitante_id
                )
                
                user_id = execute_query(user_query, user_params)
                
                if user_id:
                    return {
                        'success': True,
                        'message': 'Usuario creado exitosamente',
                        'user_id': user_id
                    }
            
            return {'success': False, 'message': 'Error al crear usuario'}
            
        except Exception as e:
            logging.error(f"Error creando usuario: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    @staticmethod
    def authenticate_user(email, password):
        """
        Autentica un usuario por email y contraseña
        
        Args:
            email (str): Email del usuario
            password (str): Contraseña del usuario
            
        Returns:
            dict: Datos del usuario autenticado o None
        """
        try:
            query = """
                SELECT 
                    u.IdUsuario,
                    u.IdTipoUsuario,
                    h.Nombre,
                    h.Apellido,
                    h.CorreoElectronico,
                    h.NumeroDocumento,
                    h.Telefono,
                    tu.Perfil as rol,
                    u.Contraseña
                FROM usuario u
                INNER JOIN habitantes h ON u.IdHabitante = h.IdHabitante
                LEFT JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
                WHERE h.CorreoElectronico = %s
            """
            
            user = execute_query(query, (email,), fetch_one=True)
            
            if user and Security.check_password_hash(user['Contraseña'], password):
                # Remover contraseña del resultado
                user.pop('Contraseña', None)
                return user
            
            return None
            
        except Exception as e:
            logging.error(f"Error autenticando usuario: {str(e)}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id):
        """
        Obtiene un usuario por su ID
        
        Args:
            user_id (int): ID del usuario
            
        Returns:
            dict: Datos del usuario
        """
        try:
            query = """
                SELECT 
                    u.IdUsuario,
                    u.IdTipoUsuario,
                    h.Nombre,
                    h.Apellido,
                    h.CorreoElectronico,
                    h.NumeroDocumento,
                    h.Telefono,
                    h.Direccion,
                    tu.Perfil as rol
                FROM usuario u
                INNER JOIN habitantes h ON u.IdHabitante = h.IdHabitante
                LEFT JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
                WHERE u.IdUsuario = %s
            """
            
            return execute_query(query, (user_id,), fetch_one=True)
            
        except Exception as e:
            logging.error(f"Error obteniendo usuario: {str(e)}")
            return None
    
    @staticmethod
    def get_all_users():
        """
        Obtiene todos los usuarios del sistema
        
        Returns:
            list: Lista de usuarios
        """
        try:
            query = """
                SELECT 
                    u.IdUsuario,
                    u.IdTipoUsuario,
                    h.Nombre,
                    h.Apellido,
                    h.CorreoElectronico,
                    h.NumeroDocumento,
                    h.Telefono,
                    tu.Perfil as rol
                FROM usuario u
                INNER JOIN habitantes h ON u.IdHabitante = h.IdHabitante
                LEFT JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
                ORDER BY h.Nombre, h.Apellido
            """
            
            return execute_query(query, fetch_all=True)
            
        except Exception as e:
            logging.error(f"Error obteniendo usuarios: {str(e)}")
            return []
    
    @staticmethod
    def update_user(user_id, user_data):
        """
        Actualiza los datos de un usuario
        
        Args:
            user_id (int): ID del usuario
            user_data (dict): Nuevos datos del usuario
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            # Actualizar datos del habitante
            habitante_query = """
                UPDATE habitantes h
                INNER JOIN usuario u ON h.IdHabitante = u.IdHabitante
                SET h.Nombre = %s, h.Apellido = %s, h.Telefono = %s, h.Direccion = %s
                WHERE u.IdUsuario = %s
            """
            
            habitante_params = (
                user_data.get('nombre'),
                user_data.get('apellido'),
                user_data.get('telefono'),
                user_data.get('direccion'),
                user_id
            )
            
            rows_affected = execute_query(habitante_query, habitante_params)
            
            if rows_affected > 0:
                return {'success': True, 'message': 'Usuario actualizado exitosamente'}
            else:
                return {'success': False, 'message': 'No se pudo actualizar el usuario'}
                
        except Exception as e:
            logging.error(f"Error actualizando usuario: {str(e)}")
            return {'success': False, 'message': f'Error: {str(e)}'}
