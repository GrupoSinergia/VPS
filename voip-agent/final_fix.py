#!/usr/bin/env python3
import sqlite3
import json
import subprocess
import time

def create_fixed_workflow():
    """Crear workflow con configuración corregida para Ollama"""
    print("🔧 Creating corrected workflow...")

    # Workflow corregido con configuración específica de Ollama
    fixed_workflow = {
        "name": "VoIP AI Agent FIXED",
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "voip-agent",
                    "responseMode": "responseNode",
                    "options": {}
                },
                "id": "webhook-node",
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
                    "jsonBody": "={{ {\n  \"model\": \"llama3.2:3b-instruct-q4_k_m\",\n  \"prompt\": \"Eres un asistente de un negocio de automatización. Responde en español de forma breve y profesional. Usuario dice: \" + $json.text,\n  \"stream\": false\n} }}",
                    "options": {
                        "timeout": 60000
                    }
                },
                "id": "http-request-node",
                "name": "Ollama Direct Request",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [300, 0]
            },
            {
                "parameters": {
                    "jsCode": "// Procesar respuesta de Ollama\\nconst input = $input.first()?.json;\\nconst userText = $('Webhook').first()?.json?.text || '';\\nconst ollamaResponse = input?.response || 'Lo siento, no pude procesar tu solicitud.';\\n\\n// Formatear respuesta para VoIP\\nlet finalResponse = ollamaResponse;\\n\\n// Limitar longitud\\nif (finalResponse.length > 200) {\\n  finalResponse = finalResponse.substring(0, 197) + '...';\\n}\\n\\nreturn {\\n  json: {\\n    response: finalResponse,\\n    user_input: userText,\\n    timestamp: new Date().toISOString()\\n  }\\n};"
                },
                "id": "code-node",
                "name": "Process Response",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [600, 0]
            },
            {
                "parameters": {
                    "respondWith": "json",
                    "responseBody": "={{ $json }}",
                    "options": {}
                },
                "id": "respond-node",
                "name": "Respond to Webhook",
                "type": "n8n-nodes-base.respondToWebhook",
                "typeVersion": 1,
                "position": [900, 0]
            }
        ],
        "connections": {
            "Webhook": {
                "main": [[{"node": "Ollama Direct Request", "type": "main", "index": 0}]]
            },
            "Ollama Direct Request": {
                "main": [[{"node": "Process Response", "type": "main", "index": 0}]]
            },
            "Process Response": {
                "main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]
            }
        },
        "active": True,
        "settings": {"executionOrder": "v1"}
    }

    return fixed_workflow

def deploy_fixed_workflow():
    """Desplegar workflow corregido"""
    print("🚀 Deploying fixed workflow...")

    # Copiar base de datos
    subprocess.run([
        "docker", "cp",
        "root_n8n_1:/home/node/.n8n/database.sqlite",
        "/tmp/n8n_database.sqlite"
    ], check=True)

    # Conectar y crear workflow
    conn = sqlite3.connect('/tmp/n8n_database.sqlite')
    cursor = conn.cursor()

    # Eliminar workflow anterior
    cursor.execute("DELETE FROM workflow_entity WHERE name LIKE '%VoIP AI Agent%'")

    # Crear workflow corregido
    workflow_data = create_fixed_workflow()
    workflow_id = "fixed-voip-workflow"

    cursor.execute("""
        INSERT INTO workflow_entity (
            id, name, active, nodes, connections, settings
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        workflow_id,
        workflow_data['name'],
        1,  # active
        json.dumps(workflow_data['nodes']),
        json.dumps(workflow_data['connections']),
        json.dumps(workflow_data['settings'])
    ))

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

    print("✅ Fixed workflow deployed!")

if __name__ == "__main__":
    deploy_fixed_workflow()

    print("\n🧪 Testing fixed integration...")
    time.sleep(5)
    subprocess.run(["python3", "test_webhook.py"])