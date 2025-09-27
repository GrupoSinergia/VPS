#!/usr/bin/env python3
import sqlite3
import json
import subprocess
import time
import uuid

def create_simple_working_workflow():
    """Crear workflow ultra-simple que definitivamente funciona"""
    print("🛠️ Creating ultra-simple working workflow...")

    # Este workflow usa solo HTTP Request (no LangChain)
    workflow_data = {
        "name": "Simple VoIP Webhook",
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "voip-agent",
                    "responseMode": "responseNode"
                },
                "id": str(uuid.uuid4()),
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 0],
                "webhookId": "voip-agent"
            },
            {
                "parameters": {
                    "url": "http://172.17.0.1:11434/api/generate",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={{ {\\n  \\\"model\\\": \\\"llama3.2:3b-instruct-q4_k_m\\\",\\n  \\\"prompt\\\": \\\"Eres un asistente virtual de un negocio de automatización. Responde en español de forma breve y profesional. Usuario dice: \\\" + $json.text,\\n  \\\"stream\\\": false\\n} }}",
                    "options": {
                        "timeout": 30000
                    }
                },
                "id": str(uuid.uuid4()),
                "name": "Call Ollama",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [300, 0]
            },
            {
                "parameters": {
                    "respondWith": "json",
                    "responseBody": "={{ { \\\"response\\\": $json.response, \\\"user_input\\\": $('Webhook').first().json.text } }}",
                    "options": {}
                },
                "id": str(uuid.uuid4()),
                "name": "Respond",
                "type": "n8n-nodes-base.respondToWebhook",
                "typeVersion": 1,
                "position": [600, 0]
            }
        ],
        "connections": {
            "Webhook": {
                "main": [[{"node": "Call Ollama", "type": "main", "index": 0}]]
            },
            "Call Ollama": {
                "main": [[{"node": "Respond", "type": "main", "index": 0}]]
            }
        },
        "active": True,
        "settings": {"executionOrder": "v1"}
    }

    return workflow_data

def deploy_simple_workflow():
    """Desplegar workflow simple"""
    print("🚀 Deploying simple workflow...")

    # Detener N8N temporalmente para evitar conflictos
    subprocess.run(["docker", "stop", "root_n8n_1"], check=True)
    time.sleep(3)

    # Copiar y modificar base de datos
    subprocess.run([
        "docker", "cp",
        "root_n8n_1:/home/node/.n8n/database.sqlite",
        "/tmp/n8n_simple.sqlite"
    ], check=True)

    conn = sqlite3.connect('/tmp/n8n_simple.sqlite')
    cursor = conn.cursor()

    # Limpiar workflows anteriores
    cursor.execute("DELETE FROM workflow_entity WHERE name LIKE '%VoIP%' OR name LIKE '%Simple%'")

    # Crear el workflow simple
    workflow_data = create_simple_working_workflow()
    workflow_id = str(uuid.uuid4())

    cursor.execute("""
        INSERT INTO workflow_entity (
            id, name, active, nodes, connections, settings
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        workflow_id,
        workflow_data['name'],
        1,  # active=True
        json.dumps(workflow_data['nodes']),
        json.dumps(workflow_data['connections']),
        json.dumps(workflow_data['settings'])
    ))

    conn.commit()
    conn.close()

    # Copiar de vuelta
    subprocess.run([
        "docker", "cp",
        "/tmp/n8n_simple.sqlite",
        "root_n8n_1:/home/node/.n8n/database.sqlite"
    ], check=True)

    # Reiniciar N8N
    print("🔄 Starting N8N with simple workflow...")
    subprocess.run(["docker", "start", "root_n8n_1"], check=True)
    time.sleep(20)  # Dar tiempo suficiente

    print(f"✅ Simple workflow deployed with ID: {workflow_id}")

if __name__ == "__main__":
    deploy_simple_workflow()

    print("\n🧪 Testing simple integration...")
    time.sleep(5)

    # Test directo con curl
    print("📞 Testing with curl...")
    result = subprocess.run([
        "curl", "-X", "POST", "http://localhost:5678/webhook/voip-agent",
        "-H", "Content-Type: application/json",
        "-d", '{"text": "hola"}',
        "--max-time", "15", "-s"
    ], capture_output=True, text=True)

    print(f"📊 Curl Response: {result.stdout}")
    if result.stderr:
        print(f"❌ Curl Error: {result.stderr}")

    # Ejecutar test completo
    subprocess.run(["python3", "test_webhook.py"])