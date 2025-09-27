#!/usr/bin/env python3
import sqlite3
import json
import uuid
import subprocess
import time
from datetime import datetime

def delete_existing_workflows(cursor):
    """Eliminar workflows existentes con el mismo nombre"""
    cursor.execute("SELECT id FROM workflow_entity WHERE name = ?", ("VoIP AI Agent Completo",))
    existing = cursor.fetchall()

    for (workflow_id,) in existing:
        print(f"🗑️ Removing existing workflow: {workflow_id}")
        cursor.execute("DELETE FROM workflow_entity WHERE id = ?", (workflow_id,))

def delete_existing_credentials(cursor):
    """Eliminar credenciales Ollama existentes"""
    cursor.execute("SELECT id FROM credentials_entity WHERE type = ? AND name LIKE ?", ("ollamaApi", "%Ollama%"))
    existing = cursor.fetchall()

    for (cred_id,) in existing:
        print(f"🗑️ Removing existing credential: {cred_id}")
        cursor.execute("DELETE FROM credentials_entity WHERE id = ?", (cred_id,))

def create_ollama_credential(cursor):
    """Crear credencial de Ollama"""
    print("🔑 Creating Ollama credential...")

    # Generar ID único
    cred_id = str(uuid.uuid4())

    # Los datos se almacenan como JSON plano en N8N
    credential_data = {
        "baseUrl": "http://127.0.0.1:11434",
        "apiKey": ""
    }

    # Insertar credencial
    cursor.execute("""
        INSERT INTO credentials_entity (id, name, type, data, isManaged)
        VALUES (?, ?, ?, ?, ?)
    """, (
        cred_id,
        "Ollama Local API",
        "ollamaApi",
        json.dumps(credential_data),
        0
    ))

    print(f"✅ Credential created: {cred_id}")
    return cred_id

def create_workflow(cursor, cred_id):
    """Crear workflow activo con credencial"""
    print("📋 Creating active workflow...")

    # Cargar workflow
    with open('/root/VPS/voip-agent/n8n-complete-workflow.json', 'r') as f:
        workflow_data = json.load(f)

    # Actualizar credencial en el nodo Ollama
    for node in workflow_data['nodes']:
        if node.get('name') == 'Ollama Chat Model':
            node['credentials'] = {
                "ollamaApi": {
                    "id": cred_id,
                    "name": "Ollama Local API"
                }
            }
            print("🔗 Linked credential to Ollama node")

    # Generar ID para workflow
    workflow_id = str(uuid.uuid4())

    # Insertar workflow ACTIVO
    cursor.execute("""
        INSERT INTO workflow_entity (
            id, name, active, nodes, connections, settings, versionId, triggerCount
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        workflow_id,
        workflow_data['name'],
        1,  # active = TRUE
        json.dumps(workflow_data['nodes']),
        json.dumps(workflow_data['connections']),
        json.dumps(workflow_data.get('settings', {})),
        workflow_data.get('versionId', 'auto-v1'),
        0
    ))

    print(f"✅ Active workflow created: {workflow_id}")
    return workflow_id

def restart_n8n():
    """Reiniciar N8N para cargar los cambios"""
    print("🔄 Restarting N8N to load changes...")
    subprocess.run(["docker", "restart", "root_n8n_1"], check=True)
    time.sleep(10)  # Esperar que arranque
    print("✅ N8N restarted")

def setup_complete():
    """Configuración completa automatizada"""
    print("🚀 Starting complete N8N setup...\n")

    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('/tmp/n8n_database.sqlite')
        cursor = conn.cursor()

        # Limpiar configuraciones existentes
        print("🧹 Cleaning existing configurations...")
        delete_existing_workflows(cursor)
        delete_existing_credentials(cursor)

        # Crear nueva credencial
        cred_id = create_ollama_credential(cursor)

        # Crear workflow activo
        workflow_id = create_workflow(cursor, cred_id)

        # Guardar cambios
        conn.commit()
        conn.close()

        # Copiar base de datos modificada de vuelta al contenedor
        print("📂 Updating N8N database...")
        subprocess.run([
            "docker", "cp",
            "/tmp/n8n_database.sqlite",
            "root_n8n_1:/home/node/.n8n/database.sqlite"
        ], check=True)

        # Reiniciar N8N
        restart_n8n()

        print(f"\n🎉 SETUP COMPLETED SUCCESSFULLY!")
        print(f"🔑 Credential ID: {cred_id}")
        print(f"📋 Workflow ID: {workflow_id}")
        print(f"🟢 Workflow Status: ACTIVE")
        print(f"📞 Webhook URL: http://localhost:5678/webhook/voip-agent")

        return True

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_complete()
    if success:
        print("\n🧪 Running integration test...")
        time.sleep(3)
        subprocess.run(["python3", "test_webhook.py"])
    else:
        print("\n❌ Setup failed - please check errors above")