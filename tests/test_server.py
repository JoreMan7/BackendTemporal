"""
Script simple para probar el servidor
"""
import requests
import json

def test_server():
    """Prueba básica del servidor"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Probando servidor...")
    
    # Probar ruta raíz
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Ruta raíz: {response.status_code}")
        print(f"   Respuesta: {response.json()}")
    except Exception as e:
        print(f"❌ Error en ruta raíz: {e}")
    
    # Probar health check
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"   Respuesta: {response.json()}")
    except Exception as e:
        print(f"❌ Error en health check: {e}")
    
    # Probar API principal
    try:
        response = requests.get(f"{base_url}/api/")
        print(f"✅ API principal: {response.status_code}")
        print(f"   Respuesta: {response.json()}")
    except Exception as e:
        print(f"❌ Error en API principal: {e}")
    
    # Probar API health
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"✅ API health: {response.status_code}")
        print(f"   Respuesta: {response.json()}")
    except Exception as e:
        print(f"❌ Error en API health: {e}")

if __name__ == '__main__':
    test_server()
