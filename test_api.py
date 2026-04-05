"""Script para probar la API JWT"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("🔐 Probando sistema JWT...\n")

# 1. Login
print("1️⃣ Login con usuario admin...")
login_data = {
    "username": "admin",
    "password": "Admin123"
}

response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
print(f"   Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    user = data["user"]
    
    print(f"   ✅ Login exitoso!")
    print(f"   Usuario: {user['username']}")
    print(f"   Email: {user['email']}")
    print(f"   Roles: {user['roles']}")
    print(f"   Access Token: {access_token[:50]}...")
    
    # 2. Obtener lista de usuarios
    print("\n2️⃣ Obteniendo lista de usuarios (requiere rol ADMIN)...")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(f"{BASE_URL}/users", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Usuarios obtenidos: {data['total']} total")
        for user in data['users']:
            print(f"      - {user['username']} ({user['email']}) - Roles: {user['roles']}")
    else:
        print(f"   ❌ Error: {response.json()}")
    
    # 3. Obtener perfil propio
    print("\n3️⃣ Obteniendo perfil propio...")
    response = requests.get(f"{BASE_URL}/users/{user['id']}", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Perfil obtenido:")
        print(f"      Username: {data['username']}")
        print(f"      Email: {data['email']}")
        print(f"      Roles: {data['roles']}")
    else:
        print(f"   ❌ Error: {response.json()}")
    
    # 4. Refresh token
    print("\n4️⃣ Refrescando token...")
    refresh_data = {
        "refresh_token": refresh_token
    }
    
    response = requests.post(f"{BASE_URL}/auth/refresh", json=refresh_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        new_access_token = data["access_token"]
        print(f"   ✅ Token refrescado exitosamente!")
        print(f"   Nuevo Access Token: {new_access_token[:50]}...")
    else:
        print(f"   ❌ Error: {response.json()}")
    
    # 5. Logout
    print("\n5️⃣ Cerrando sesión...")
    response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✅ Sesión cerrada exitosamente!")
    else:
        print(f"   ❌ Error: {response.json()}")
    
    # 6. Intentar usar token después de logout
    print("\n6️⃣ Intentando usar token después de logout (debe fallar)...")
    response = requests.get(f"{BASE_URL}/users", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 401:
        print(f"   ✅ Token correctamente revocado!")
        print(f"   Error: {response.json()['detail']}")
    else:
        print(f"   ❌ Token no fue revocado correctamente")

else:
    print(f"   ❌ Login fallido: {response.json()}")

print("\n✅ Pruebas completadas!")
