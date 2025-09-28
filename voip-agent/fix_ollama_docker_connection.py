#!/usr/bin/env python3
import sqlite3
import json
import subprocess
import time

def fix_ollama_docker_connection():
    """Configurar la URL de Ollama para el contenedor Docker"""
    print("🔧 Fixing Ollama connection for Docker containers...")

    # Copiar base de datos de n8n
    print("📂 Copying n8n database...")
    subprocess.run([
        "docker", "cp",
        "root_n8n_1:/home/node/.n8n/database.sqlite",
        "/tmp/n8n_database.sqlite"
    ], check=True)

    # Conectar y actualizar
    conn = sqlite3.connect('/tmp/n8n_database.sqlite')
    cursor = conn.cursor()

    # Buscar credenciales de Ollama existentes
    cursor.execute("SELECT id, data FROM credentials_entity WHERE type = 'ollamaApi'")
    credentials = cursor.fetchall()

    if credentials:
        print(f"✅ Found {len(credentials)} existing Ollama credentials")
        for cred_id, data_json in credentials:
            data = json.loads(data_json)
            old_url = data.get('baseUrl', '')

            # Actualizar URL para comunicación entre contenedores Docker
            data['baseUrl'] = 'http://ollama:11434'

            # Guardar cambios
            cursor.execute(
                "UPDATE credentials_entity SET data = ? WHERE id = ?",
                (json.dumps(data), cred_id)
            )

            print(f"🔄 Updated credential {cred_id}")
            print(f"   Old URL: {old_url}")
            print(f"   New URL: {data['baseUrl']}")
    else:
        print("📝 No existing Ollama credentials found. Creating new one...")

        # Crear nueva credencial
        import uuid
        from datetime import datetime

        cred_id = str(uuid.uuid4()).replace('-', '')

        credential_data = {
            "baseUrl": "http://ollama:11434",
            "apiKey": ""
        }

        timestamp = datetime.utcnow().isoformat() + 'Z'

        cursor.execute("""
            INSERT INTO credentials_entity (id, name, type, data, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            cred_id,
            "Ollama Docker API",
            "ollamaApi",
            json.dumps(credential_data),
            timestamp,
            timestamp
        ))

        print(f"✅ Created new credential {cred_id}")
        print(f"   URL: {credential_data['baseUrl']}")

    conn.commit()
    conn.close()

    # Copiar de vuelta al contenedor
    print("📤 Copying database back to n8n container...")
    subprocess.run([
        "docker", "cp",
        "/tmp/n8n_database.sqlite",
        "root_n8n_1:/home/node/.n8n/database.sqlite"
    ], check=True)

    # Reiniciar N8N para aplicar cambios
    print("🔄 Restarting N8N container...")
    subprocess.run(["docker", "restart", "root_n8n_1"], check=True)

    print("⏳ Waiting for n8n to restart...")
    time.sleep(15)

    print("✅ Ollama Docker connection configured!")
    print("\n📋 Next steps:")
    print("1. Access N8N at http://localhost:5678")
    print("2. Username: admin")
    print("3. Password: Sparkurlife5.")
    print("4. The Ollama credential should now work with URL: http://ollama:11434")
    print("5. Test the connection in your workflow")

def test_connection():
    """Probar la conexión entre contenedores"""
    print("\n🧪 Testing inter-container connectivity...")

    try:
        # Probar conectividad desde n8n hacia ollama
        result = subprocess.run([
            "docker", "exec", "root_n8n_1",
            "curl", "-s", "http://ollama:11434/api/tags"
        ], capture_output=True, text=True, check=True)

        models = json.loads(result.stdout)
        print(f"✅ Connection successful! Found {len(models['models'])} models:")
        for model in models['models']:
            print(f"   - {model['name']}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Connection test failed: {e}")
    except json.JSONDecodeError:
        print("❌ Invalid response from Ollama")

if __name__ == "__main__":
    fix_ollama_docker_connection()
    test_connection()