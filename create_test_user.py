#!/usr/bin/env python3
"""
Script para crear usuarios de prueba en el sistema
Crea usuarios con diferentes tipos de documento para testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pymysql
from werkzeug.security import generate_password_hash
from config import config

def check_table_structure(cursor):
    """Verificar la estructura de la tabla habitantes"""
    try:
        cursor.execute("DESCRIBE habitantes")
        columns = cursor.fetchall()
        print("📋 Estructura de la tabla habitantes:")
        for col in columns:
            print(f"   - {col['Field']}: {col['Type']} {'NOT NULL' if col['Null'] == 'NO' else 'NULL'}")
        return [col['Field'] for col in columns]
    except Exception as e:
        print(f"⚠️  Error verificando estructura: {e}")
        return []

def create_test_users():
    """Crear usuarios de prueba para testing"""
    
    print("🔧 Creando usuarios de prueba...")
    
    # Configuración de la base de datos
    db_config = config['development']
    
    # Usuarios de prueba con SOLO los campos que existen
    test_users = [
        {
            'nombre': 'Admin00',
            'apellido': 'Sistema',
            'id_tipo_documento': 1,  # Cédula
            'numero_documento': '12345008',
            'fecha_nacimiento': '1990-01-01',
            'hijos': 0,
            'sexo': 'Masculino',  # ENUM: 'Masculino','Femenino','Otros'
            'tipo_religion': 'Católica',  # ENUM: 'Católica','Evangélica','Judía','Musulmana','Otras'
            'id_tipo_sacramento': 1,  # Bautismo
            'discapacidad_para_asistir': 'Ninguna',  # Campo obligatorio
            'id_tipo_poblacion': 3,  # Adultos
            'direccion': 'Calle 123 #45-67',
            'telefono': '3001234567',
            'correo_electronico': 'admin00@sistema.com',
            'id_grupo_familiar': None,
            'tiene_impedimento_salud': 0,  # 0 = False, 1 = True
            'motivo_impedimento_salud': None,
            'password': 'Admin123!',
            'id_tipo_usuario': 1  # Administrador
        },
        {
            'nombre': 'Juan0',
            'apellido': 'Pérez',
            'id_tipo_documento': 1,  # Cédula
            'numero_documento': '87654320',
            'fecha_nacimiento': '1985-05-15',
            'hijos': 2,
            'sexo': 'Masculino',
            'tipo_religion': 'Católica',
            'id_tipo_sacramento': 1,
            'discapacidad_para_asistir': 'Ninguna',
            'id_tipo_poblacion': 3,  # Adultos
            'direccion': 'Carrera 45 #12-34',
            'telefono': '3009876543',
            'correo_electronico': 'juan.perez0@email.com',
            'id_grupo_familiar': 1,
            'tiene_impedimento_salud': 0,
            'motivo_impedimento_salud': None,
            'password': 'Usuario123!',
            'id_tipo_usuario': 2  # Usuario normal
        },
        {
            'nombre': 'María',
            'apellido': 'González',
            'id_tipo_documento': 2,  # Tarjeta de Identidad
            'numero_documento': '1122330055',
            'fecha_nacimiento': '1992-08-20',
            'hijos': 1,
            'sexo': 'Femenino',
            'tipo_religion': 'Católica',
            'id_tipo_sacramento': 2,  # Comunión
            'discapacidad_para_asistir': 'Ninguna',
            'id_tipo_poblacion': 3,  # Adultos
            'direccion': 'Avenida 80 #25-30',
            'telefono': '3005551234',
            'correo_electronico': 'maria.gonzalez0@email.com',
            'id_grupo_familiar': 2,
            'tiene_impedimento_salud': 0,
            'motivo_impedimento_salud': None,
            'password': 'Maria123!',
            'id_tipo_usuario': 2  # Usuario normal
        }
    ]
    
    created_users = []
    
    try:
        # Conectar a MySQL directamente
        connection = pymysql.connect(
            host=db_config.MYSQL_HOST,
            user=db_config.MYSQL_USER,
            password=db_config.MYSQL_PASSWORD,
            database=db_config.MYSQL_DB,
            port=db_config.MYSQL_PORT,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        cursor = connection.cursor()
        print("✅ Conexión a base de datos establecida")
        
        # Verificar estructura de la tabla
        available_columns = check_table_structure(cursor)
        
        for user_data in test_users:
            try:
                # Verificar si el usuario ya existe
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM habitantes h 
                    WHERE h.IdTipoDocumento = %s AND h.NumeroDocumento = %s
                """, (user_data['id_tipo_documento'], user_data['numero_documento']))
                
                existing = cursor.fetchone()
                
                if existing and existing['count'] > 0:
                    print(f"⚠️  Usuario {user_data['nombre']} {user_data['apellido']} ya existe")
                    
                    # Agregar a la lista aunque ya exista para mostrar credenciales
                    created_users.append({
                        'nombre': user_data['nombre'],
                        'apellido': user_data['apellido'],
                        'documento': user_data['numero_documento'],
                        'tipo_documento': user_data['id_tipo_documento'],
                        'password': user_data['password'],
                        'user_id': 'existente'
                    })
                    continue
                
                # Crear habitante SIN IdEstadoCivil (no existe en la tabla)
                print(f"🔄 Creando habitante: {user_data['nombre']} {user_data['apellido']}")
                cursor.execute("""
                    INSERT INTO habitantes (
                        Nombre, Apellido, IdTipoDocumento, NumeroDocumento,
                        FechaNacimiento, Hijos, Sexo, TipoReligion, IdTipoSacramento,
                        DiscapacidadParaAsistir, IdTipoPoblacion, Direccion, Telefono,
                        CorreoElectronico, IdGrupoFamiliar, TieneImpedimentoSalud,
                        MotivoImpedimentoSalud
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_data['nombre'],
                    user_data['apellido'],
                    user_data['id_tipo_documento'],
                    user_data['numero_documento'],
                    user_data['fecha_nacimiento'],
                    user_data['hijos'],
                    user_data['sexo'],
                    user_data['tipo_religion'],
                    user_data['id_tipo_sacramento'],
                    user_data['discapacidad_para_asistir'],
                    user_data['id_tipo_poblacion'],
                    user_data['direccion'],
                    user_data['telefono'],
                    user_data['correo_electronico'],
                    user_data['id_grupo_familiar'],
                    user_data['tiene_impedimento_salud'],
                    user_data['motivo_impedimento_salud']
                ))
                
                habitante_id = cursor.lastrowid
                print(f"✅ Habitante creado con ID: {habitante_id}")
                
                # Crear usuario
                password_hash = generate_password_hash(user_data['password'], method='pbkdf2:sha256')
                
                cursor.execute("""
                    INSERT INTO usuario (IdTipoUsuario, Contraseña, IdHabitante)
                    VALUES (%s, %s, %s)
                """, (
                    user_data['id_tipo_usuario'],
                    password_hash,
                    habitante_id
                ))
                
                user_id = cursor.lastrowid
                
                created_users.append({
                    'nombre': user_data['nombre'],
                    'apellido': user_data['apellido'],
                    'documento': user_data['numero_documento'],
                    'tipo_documento': user_data['id_tipo_documento'],
                    'password': user_data['password'],
                    'user_id': user_id
                })
                
                print(f"✅ Usuario creado: {user_data['nombre']} {user_data['apellido']} (ID: {user_id})")
                
            except Exception as e:
                print(f"❌ Error creando usuario {user_data['nombre']}: {str(e)}")
                connection.rollback()
        
        # Confirmar todos los cambios
        connection.commit()
        print("✅ Todos los cambios confirmados en la base de datos")
        
    except Exception as e:
        print(f"❌ Error de conexión a base de datos: {str(e)}")
        return []
    
    finally:
        if 'connection' in locals():
            connection.close()
            print("🔌 Conexión cerrada")
    
    return created_users

def show_test_credentials(users):
    """Mostrar credenciales de prueba"""
    
    print("\n" + "="*70)
    print("🔑 CREDENCIALES DE PRUEBA PARA THUNDER CLIENT")
    print("="*70)
    
    for i, user in enumerate(users, 1):
        print(f"\n👤 USUARIO {i}: {user['nombre']} {user['apellido']}")
        print(f"   📋 Tipo de Documento: {user['tipo_documento']}")
        print(f"   🆔 Número de Documento: {user['documento']}")
        print(f"   🔐 Contraseña: {user['password']}")
        print(f"   🏷️  ID Usuario: {user['user_id']}")

def show_thunder_client_examples():
    """Mostrar ejemplos para Thunder Client"""
    
    print("\n" + "="*70)
    print("📡 PASOS PARA THUNDER CLIENT")
    print("="*70)
    
    print("\n🔧 CONFIGURACIÓN:")
    print("   1. Método: POST")
    print("   2. URL: http://localhost:5000/api/auth/login")
    print("   3. Headers:")
    print("      Content-Type: application/json")
    
    print("\n📋 EJEMPLO 1 - Admin (RECOMENDADO):")
    print("""   Body (JSON):
   {
     "document_type": "1",
     "document_number": "12345678",
     "password": "Admin123!"
   }""")
    
    print("\n📋 EJEMPLO 2 - Usuario Normal:")
    print("""   Body (JSON):
   {
     "document_type": "1",
     "document_number": "87654321",
     "password": "Usuario123!"
   }""")
    
    print("\n📋 EJEMPLO 3 - Tarjeta de Identidad:")
    print("""   Body (JSON):
   {
     "document_type": "2",
     "document_number": "1122334455",
     "password": "Maria123!"
   }""")

def main():
    """Función principal"""
    
    print("🚀 Iniciando creación de usuarios de prueba...")
    
    try:
        # Crear usuarios de prueba
        created_users = create_test_users()
        
        if created_users:
            show_test_credentials(created_users)
            show_thunder_client_examples()
            
            print(f"\n✅ Proceso completado - {len(created_users)} usuarios disponibles")
            print("\n🚀 PRÓXIMOS PASOS:")
            print("   1. Ejecutar: python app.py")
            print("   2. Abrir Thunder Client")
            print("   3. Usar las credenciales mostradas arriba")
            print("   4. ¡Hacer login! 🎉")
        else:
            print("⚠️  No se pudieron crear/encontrar usuarios")
            
    except Exception as e:
        print(f"❌ Error general: {str(e)}")

if __name__ == "__main__":
    main()

