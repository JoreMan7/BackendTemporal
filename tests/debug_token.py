"""
Script para debuggear problemas de token
"""
import requests
import json

def test_complete_flow():
    """Prueba completa del flujo de autenticación"""
    
    base_url = "http://localhost:5000"
    
    print("🔍 DIAGNÓSTICO COMPLETO DE TOKEN")
    print("=" * 50)
    
    # Paso 1: Verificar servidor
    print("\n1. 🏥 Verificando servidor...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Servidor funcionando")
        else:
            print("   ❌ Servidor con problemas")
            return
    except Exception as e:
        print(f"   ❌ Error conectando al servidor: {e}")
        return
    
    # Paso 2: Registrar usuario
    print("\n2. 📝 Registrando usuario de prueba...")
    user_data = {
        "nombre": "Debug",
        "apellido": "User",
        "correo_electronico": "debug@test.com",
        "password": "Debug123!",
        "numero_documento": "99999999",
        "id_tipo_documento": 1,
        "id_tipo_usuario": 1
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/register",
            json=user_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code in [201, 400]:  # 400 si ya existe
            print("   ✅ Usuario registrado/existe")
        else:
            print(f"   ❌ Error registrando: {response.text}")
    except Exception as e:
        print(f"   ❌ Error en registro: {e}")
    
    # Paso 3: Login
    print("\n3. 🔑 Haciendo login...")
    login_data = {
        "email": "debug@test.com",
        "password": "Debug123!"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print("   ✅ Login exitoso")
            print(f"   Token (primeros 50 chars): {token[:50]}...")
            print(f"   Token (últimos 20 chars): ...{token[-20:]}")
            print(f"   Longitud del token: {len(token)} caracteres")
            
            # Paso 4: Usar token
            print("\n4. 🔒 Probando endpoint protegido...")
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            print(f"   Header Authorization: Bearer {token[:30]}...")
            
            try:
                response = requests.get(
                    f"{base_url}/api/auth/profile",
                    headers=headers
                )
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("   ✅ Token funciona correctamente!")
                    profile = response.json()
                    print(f"   Usuario: {profile.get('user', {}).get('Nombre', 'N/A')}")
                else:
                    print(f"   ❌ Error con token: {response.text}")
                    
                    # Información adicional de debug
                    print(f"\n   🔍 Headers enviados:")
                    for key, value in headers.items():
                        if key == 'Authorization':
                            print(f"      {key}: Bearer {value[7:37]}...")
                        else:
                            print(f"      {key}: {value}")
                            
            except Exception as e:
                print(f"   ❌ Error usando token: {e}")
                
        else:
            print(f"   ❌ Error en login: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error en login: {e}")
    
    # Paso 5: Información adicional
    print("\n5. 📊 Información del sistema...")
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            health = response.json()
            print(f"   Base de datos: {health.get('database', 'unknown')}")
        
        response = requests.get(f"{base_url}/api/test-db")
        if response.status_code == 200:
            db_test = response.json()
            tests = db_test.get('tests', {})
            print(f"   Usuarios en BD: {tests.get('usuarios_count', 0)}")
            print(f"   Habitantes en BD: {tests.get('habitantes_count', 0)}")
            
    except Exception as e:
        print(f"   ❌ Error obteniendo info: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 INSTRUCCIONES PARA THUNDER CLIENT:")
    print("=" * 50)
    print("1. Method: GET")
    print("2. URL: http://localhost:5000/api/auth/profile")
    print("3. Headers:")
    print("   Name: Authorization")
    print(f"   Value: Bearer {token if 'token' in locals() else 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1MTU5MzEzNywianRpIjoiZDJjZDFiZjEtNDZiNC00ODYzLWI4YzktMTQyOTI3MGI0MWQzIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6NywibmJmIjoxNzUxNTkzMTM3LCJleHAiOjE3NTE1OTY3MzcsInJvbCI6ImFkbWluaXN0cmFkb3IiLCJub21icmUiOiJBZG1pbiIsImFwZWxsaWRvIjoiVGVzdCJ9.FkCZDm8Mf02GGycDvP4JnleJOBspJEUmkXwHA19iP14'}")
    print("\n¡Copia exactamente el token que aparece arriba!")

if __name__ == '__main__':
    test_complete_flow()
