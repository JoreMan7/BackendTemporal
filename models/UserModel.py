from database.db_mysql import execute_query
from utils import Security
from datetime import datetime
import logging

class UserModel:
    @staticmethod
    def create_user(user_data):
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Inserta habitante con IdSexo (FK), no 'Sexo'
            habitante_query = """
                INSERT INTO habitantes (
                    Nombre, Apellido, IdTipoDocumento, NumeroDocumento,
                    FechaNacimiento, Hijos, IdSexo, Telefono,
                    CorreoElectronico, Direccion, DiscapacidadParaAsistir,
                    Activo, FechaRegistro
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            """
            habitante_params = (
                user_data.get('nombre'),
                user_data.get('apellido'),
                user_data.get('id_tipo_documento'),
                user_data.get('numero_documento'),
                user_data.get('fecha_nacimiento'),
                user_data.get('hijos', 0),
                user_data.get('id_sexo'),              # 👈 AQUÍ el FK correcto
                user_data.get('telefono'),
                user_data.get('correo_electronico'),
                user_data.get('direccion'),
                user_data.get('discapacidad_para_asistir', 'Ninguna'),
                now
            )

            habitante_id = execute_query(habitante_query, habitante_params)

            if habitante_id:
                password_hash = Security.generate_password_hash(user_data.get('password'))

                user_query = """
                    INSERT INTO usuario (IdTipoUsuario, Contraseña, IdHabitante, Activo, FechaRegistro)
                    VALUES (%s, %s, %s, 1, %s)
                """
                user_params = (
                    user_data.get('id_tipo_usuario'),
                    password_hash,
                    habitante_id,
                    now
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
    def authenticate_user_by_document(document_type, document_number, password):
        try:
            query = """
                SELECT 
                    u.IdUsuario,
                    u.IdTipoUsuario,
                    u.Activo AS ActivoUsuario,
                    h.IdHabitante,
                    h.Activo AS ActivoHabitante,
                    h.Nombre,
                    h.Apellido,
                    h.CorreoElectronico,
                    h.NumeroDocumento,
                    h.Telefono,
                    h.IdTipoDocumento,
                    td.Descripcion AS tipo_documento_nombre,
                    tu.Perfil AS rol,
                    u.Contraseña AS password_hash
                FROM usuario u
                INNER JOIN habitantes h ON u.IdHabitante = h.IdHabitante
                LEFT JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
                LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
                WHERE h.IdTipoDocumento = %s
                  AND h.NumeroDocumento = %s
                  AND u.Activo = 1
                  AND h.Activo = 1
                LIMIT 1
            """
            user = execute_query(query, (document_type, document_number), fetch_one=True)
            if not user:
                return None

            if not Security.check_password_hash(user['password_hash'], password):
                return None

            user.pop('password_hash', None)
            return user

        except Exception as e:
            logging.error(f"Error autenticando usuario por documento: {str(e)}")
            return None

    @staticmethod
    def get_user_by_id(user_id):
        try:
            query = """
                SELECT 
                    u.IdUsuario,
                    u.IdTipoUsuario,
                    u.Activo AS ActivoUsuario,
                    h.IdHabitante,
                    h.Activo AS ActivoHabitante,
                    h.Nombre,
                    h.Apellido,
                    h.CorreoElectronico,
                    h.NumeroDocumento,
                    h.Telefono,
                    h.Direccion,
                    h.IdTipoDocumento,
                    td.Descripcion AS tipo_documento_nombre,
                    tu.Perfil AS rol,
                    u.FechaRegistro
                FROM usuario u
                INNER JOIN habitantes h ON u.IdHabitante = h.IdHabitante
                LEFT JOIN tipousuario tu ON u.IdTipoUsuario = tu.IdTipoUsuario
                LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
                WHERE u.IdUsuario = %s
                LIMIT 1
            """
            return execute_query(query, (user_id,), fetch_one=True)

        except Exception as e:
            logging.error(f"Error obteniendo usuario: {str(e)}")
            return None

    @staticmethod
    def check_document_exists(document_type, document_number):
        """
        Verifica si ya existe un usuario con el documento especificado
        
        Args:
            document_type (str): Tipo de documento
            document_number (str): Número de documento
            
        Returns:
            bool: True si existe, False si no existe
        """
        try:
            query = """
                SELECT COUNT(*) as count
                FROM habitantes h
                WHERE h.IdTipoDocumento = %s AND h.NumeroDocumento = %s
            """
            
            result = execute_query(query, (document_type, document_number), fetch_one=True)
            return result['count'] > 0
            
        except Exception as e:
            logging.error(f"Error verificando documento: {str(e)}")
            return False
