"""
Script completo para probar la API paso a paso
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_public_endpoints():
    """Prueba endpoints públicos (no requieren token)"""
    print("🔓 Probando endpoints públicos...")
    
    # Test 1: Página principal
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ GET / : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Mensaje: {data.get('message')}")
    except Exception as e:
        print(f"❌ Error en /: {e}")
    
    # Test 2: Health check
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ GET /health : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Estado: {data.get('status')}")
    except Exception as e:
        print(f"❌ Error en /health: {e}")
    
    # Test 3: API info
    try:
        response = requests.get(f"{BASE_URL}/api/")
        print(f"✅ GET /api/ : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   API: {data.get('message')}")
    except Exception as e:
        print(f"❌ Error en /api/: {e}")
    
    # Test 4: API health
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"✅ GET /api/health : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Base de datos: {data.get('database')}")
    except Exception as e:
        print(f"❌ Error en /api/health: {e}")
    
    # Test 5: Test de base de datos
    try:
        response = requests.get(f"{BASE_URL}/api/test-db")
        print(f"✅ GET /api/test-db : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Tests BD: {data.get('tests')}")
    except Exception as e:
        print(f"❌ Error en /api/test-db: {e}")

def test_registration_and_login():
    """Prueba registro y login"""
    print("\n🔐 Probando registro y autenticación...")
    
    # Datos de usuario de prueba
    user_data = {
        "nombre": "Usuario",
        "apellido": "Prueba",
        "correo_electronico": "test@example.com",
        "password": "Test123!",
        "numero_documento": "12345678",
        "id_tipo_documento": 1,
        "id_tipo_usuario": 1
    }
    
    # Test 1: Registro
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json=user_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"✅ POST /api/auth/register : {response.status_code}")
        if response.status_code in [201, 400]:  # 400 si ya existe
            data = response.json()
            print(f"   Resultado: {data.get('message')}")
    except Exception as e:
        print(f"❌ Error en registro: {e}")
    
    # Test 2: Login
    login_data = {
        "email": user_data["correo_electronico"],
        "password": user_data["password"]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"✅ POST /api/auth/login : {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            user_info = data.get('user')
            print(f"   Usuario: {user_info.get('nombre')} {user_info.get('apellido')}")
            print(f"   Token obtenido: {token[:20]}...")
            return token
        else:
            data = response.json()
            print(f"   Error: {data.get('message')}")
            return None
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return None

def test_protected_endpoints(token):
    """Prueba endpoints que requieren token"""
    print("\n🔒 Probando endpoints protegidos...")
    
    if not token:
        print("❌ No hay token disponible. Saltando pruebas protegidas.")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test 1: Perfil
    try:
        response = requests.get(f"{BASE_URL}/api/auth/profile", headers=headers)
        print(f"✅ GET /api/auth/profile : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            user = data.get('user')
            print(f"   Usuario: {user.get('Nombre')} {user.get('Apellido')}")
    except Exception as e:
        print(f"❌ Error en perfil: {e}")
    
    # Test 2: Habitantes
    try:
        response = requests.get(f"{BASE_URL}/api/habitantes", headers=headers)
        print(f"✅ GET /api/habitantes : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total habitantes: {data.get('total')}")
    except Exception as e:
        print(f"❌ Error en habitantes: {e}")
    
    # Test 3: Parroquias
    try:
        response = requests.get(f"{BASE_URL}/api/parroquias", headers=headers)
        print(f"✅ GET /api/parroquias : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total parroquias: {data.get('total')}")
    except Exception as e:
        print(f"❌ Error en parroquias: {e}")
    
    # Test 4: Estadísticas
    try:
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        print(f"✅ GET /api/dashboard/stats : {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats')
            print(f"   Estadísticas: {stats}")
    except Exception as e:
        print(f"❌ Error en estadísticas: {e}")

def test_without_token():
    """Prueba qué pasa cuando accedes a endpoints protegidos sin token"""
    print("\n⚠️  Probando acceso sin token (debería fallar)...")
    
    protected_endpoints = [
        "/api/auth/profile",
        "/api/habitantes", 
        "/api/parroquias",
        "/api/dashboard/stats"
    ]
    
    for endpoint in protected_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"❌ GET {endpoint} : {response.status_code}")
            if response.status_code == 401:
                data = response.json()
                print(f"   Error esperado: {data.get('message')}")
        except Exception as e:
            print(f"❌ Error en {endpoint}: {e}")

def main():
    """Función principal"""
    print("🧪 Prueba completa de la API de Gestión Eclesial")
    print("=" * 50)
    
    # Paso 1: Endpoints públicos
    test_public_endpoints()
    
    # Paso 2: Mostrar qué pasa sin token
    test_without_token()
    
    # Paso 3: Registro y login
    token = test_registration_and_login()
    
    # Paso 4: Endpoints protegidos con token
    test_protected_endpoints(token)
    
    print("\n" + "=" * 50)
    print("🎉 Pruebas completadas!")
    
    if token:
        print(f"\n💡 Para usar la API desde tu frontend, usa este token:")
        print(f"Authorization: Bearer {token}")
        print(f"\n📝 Ejemplo con curl:")
        print(f"curl -H 'Authorization: Bearer {token}' {BASE_URL}/api/habitantes")

if __name__ == '__main__':
    main()
