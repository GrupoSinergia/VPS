#!/usr/bin/env python3
import sqlite3
import json
import subprocess
import time

def fix_ollama_connection():
    """Corregir la URL de Ollama para Docker"""
    print("🔧 Fixing Ollama connection for Docker...")

    # Copiar base de datos
    subprocess.run([
        "docker", "cp",
        "root_n8n_1:/home/node/.n8n/database.sqlite",
        "/tmp/n8n_database.sqlite"
    ], check=True)

    # Conectar y actualizar
    conn = sqlite3.connect('/tmp/n8n_database.sqlite')
    cursor = conn.cursor()

    # Buscar credenciales de Ollama
    cursor.execute("SELECT id, data FROM credentials_entity WHERE type = 'ollamaApi'")
    credentials = cursor.fetchall()

    for cred_id, data_json in credentials:
        data = json.loads(data_json)
        old_url = data.get('baseUrl', '')

        # Actualizar URL para Docker
        data['baseUrl'] = 'http://172.17.0.1:11434'

        # Guardar cambios
        cursor.execute(
            "UPDATE credentials_entity SET data = ? WHERE id = ?",
            (json.dumps(data), cred_id)
        )

        print(f"✅ Updated credential {cred_id}")
        print(f"   Old URL: {old_url}")
        print(f"   New URL: {data['baseUrl']}")

    conn.commit()
    conn.close()

    # Copiar de vuelta
    subprocess.run([
        "docker", "cp",
        "/tmp/n8n_database.sqlite",
        "root_n8n_1:/home/node/.n8n/database.sqlite"
    ], check=True)

    # Reiniciar N8N
    print("🔄 Restarting N8N...")
    subprocess.run(["docker", "restart", "root_n8n_1"], check=True)
    time.sleep(15)

    print("✅ Ollama connection fixed!")

if __name__ == "__main__":
    fix_ollama_connection()

    print("\n🧪 Testing connection...")
    time.sleep(5)
    subprocess.run(["python3", "test_webhook.py"])