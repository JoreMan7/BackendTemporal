"""
Script para inicializar la base de datos con datos básicos
"""
import pymysql
from config import config
import sys

def init_database():
    """Inicializa la base de datos con datos básicos"""
    
    # Configuración de la base de datos
    db_config = config['development']
    
    try:
        # Conectar a MySQL
        connection = pymysql.connect(
            host=db_config.MYSQL_HOST,
            user=db_config.MYSQL_USER,
            password=db_config.MYSQL_PASSWORD,
            database=db_config.MYSQL_DB,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        print("Conectado a la base de datos exitosamente")
        
        # Insertar tipos de documento
        print("Insertando tipos de documento...")
        cursor.execute("""
            INSERT IGNORE INTO tipodocumento (Descripcion) VALUES 
            ('Cédula de Ciudadanía'),
            ('Tarjeta de Identidad'),
            ('Cédula de Extranjería'),
            ('Pasaporte')
        """)
        
        # Insertar tipos de usuario
        print("Insertando tipos de usuario...")
        cursor.execute("""
            INSERT IGNORE INTO tipousuario (Perfil, Descripcion) VALUES 
            ('administrador', 'Acceso completo al sistema'),
            ('secretario', 'Gestión de datos y reportes'),
            ('encuestador', 'Registro y consulta de información')
        """)
        
        # Insertar sectores
        print("Insertando sectores...")
        cursor.execute("""
            INSERT IGNORE INTO sector (Descripcion) VALUES 
            ('Centro'),
            ('Norte'),
            ('Sur'),
            ('Oriente'),
            ('Occidente')
        """)
        
        # Insertar estados de cita
        print("Insertando estados de cita...")
        cursor.execute("""
            INSERT IGNORE INTO estadocita (Descripcion) VALUES 
            ('Programada'),
            ('Confirmada'),
            ('En Proceso'),
            ('Completada'),
            ('Cancelada')
        """)
        
        # Confirmar cambios
        connection.commit()
        print("✅ Base de datos inicializada correctamente")
        
        # Mostrar estadísticas
        cursor.execute("SELECT COUNT(*) FROM tipodocumento")
        print(f"Tipos de documento: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM tipousuario")
        print(f"Tipos de usuario: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM sector")
        print(f"Sectores: {cursor.fetchone()[0]}")
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        sys.exit(1)
    
    finally:
        if 'connection' in locals():
            connection.close()
            print("Conexión cerrada")

if __name__ == '__main__':
    init_database()
