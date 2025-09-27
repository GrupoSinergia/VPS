#!/usr/bin/env python3
import sqlite3
import json
import uuid
import hashlib
import subprocess
import time
from datetime import datetime

# Configuración
DB_PATH = "/home/node/.n8n/database.sqlite"
WORKFLOW_FILE = "/tmp/workflow-final.json"

def create_ollama_credential(cursor):
    """Crear credencial de Ollama directamente en la base de datos"""
    print("🔑 Creating Ollama credential...")

    # Generar ID único para la credencial
    cred_id = str(uuid.uuid4()).replace('-', '')

    # Datos de la credencial (N8N los encripta internamente)
    credential_data = {
        "baseUrl": "http://127.0.0.1:11434",
        "apiKey": ""
    }

    # Obtener timestamp
    timestamp = datetime.utcnow().isoformat() + 'Z'

    # Insertar credencial en la base de datos
    cursor.execute("""
        INSERT INTO credentials_entity (id, name, type, data, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        cred_id,
        "Ollama Local API",
        "ollamaApi",
        json.dumps(credential_data),
        timestamp,
        timestamp
    ))

    print(f"✅ Credential created with ID: {cred_id}")
    return cred_id

def create_workflow_with_credential(cursor, cred_id):
    """Crear workflow con la credencial configurada"""
    print("📋 Creating workflow with Ollama credential...")

    # Cargar el workflow base
    with open('/root/VPS/voip-agent/n8n-complete-workflow.json', 'r') as f:
        workflow_data = json.load(f)

    # Actualizar la credencial en el nodo Ollama
    for node in workflow_data['nodes']:
        if node.get('name') == 'Ollama Chat Model':
            node['credentials'] = {
                "ollamaApi": {
                    "id": cred_id,
                    "name": "Ollama Local API"
                }
            }
            print("🔗 Linked Ollama credential to Chat Model node")

    # Generar ID único para el workflow
    workflow_id = str(uuid.uuid4()).replace('-', '')
    timestamp = datetime.utcnow().isoformat() + 'Z'

    # Insertar workflow activo en la base de datos
    cursor.execute("""
        INSERT INTO workflow_entity (id, name, active, nodes, connections, createdAt, updatedAt, settings, versionId)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        workflow_id,
        workflow_data['name'],
        1,  # active = True
        json.dumps(workflow_data['nodes']),
        json.dumps(workflow_data['connections']),
        timestamp,
        timestamp,
        json.dumps(workflow_data.get('settings', {})),
        workflow_data.get('versionId', 'auto-generated-v1')
    ))

    print(f"✅ Workflow created and activated with ID: {workflow_id}")
    return workflow_id

def setup_n8n_complete():
    """Configuración completa automática de N8N"""
    print("🚀 Starting automatic N8N setup...")

    try:
        # Conectar a la base de datos de N8N
        print("📂 Connecting to N8N database...")
        conn = sqlite3.connect(f'/tmp/n8n_database.sqlite')
        cursor = conn.cursor()

        # Crear credencial de Ollama
        cred_id = create_ollama_credential(cursor)

        # Crear workflow con credencial
        workflow_id = create_workflow_with_credential(cursor, cred_id)

        # Confirmar cambios
        conn.commit()
        conn.close()

        print("\n✅ Setup completed successfully!")
        print(f"🔑 Credential ID: {cred_id}")
        print(f"📋 Workflow ID: {workflow_id}")
        print("🟢 Workflow is ACTIVE and ready for calls")

        return True

    except Exception as e:
        print(f"❌ Error during setup: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    setup_n8n_complete()