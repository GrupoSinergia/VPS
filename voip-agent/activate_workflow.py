#!/usr/bin/env python3
import requests
import json
import time

# Configuración
N8N_URL = "http://localhost:5678"
WORKFLOW_FILE = "/root/VPS/voip-agent/n8n-complete-workflow.json"

def load_workflow():
    """Cargar el workflow desde el archivo JSON"""
    with open(WORKFLOW_FILE, 'r') as f:
        return json.load(f)

def get_workflows():
    """Obtener lista de workflows existentes"""
    try:
        response = requests.get(f"{N8N_URL}/api/v1/workflows")
        if response.status_code == 200:
            return response.json()['data']
        else:
            print(f"Error getting workflows: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error connecting to N8N: {e}")
        return []

def create_workflow(workflow_data):
    """Crear nuevo workflow"""
    try:
        response = requests.post(f"{N8N_URL}/api/v1/workflows", json=workflow_data)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            print(f"Error creating workflow: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error creating workflow: {e}")
        return None

def activate_workflow(workflow_id):
    """Activar workflow"""
    try:
        response = requests.patch(f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate")
        if response.status_code == 200:
            print(f"✅ Workflow {workflow_id} activated successfully")
            return True
        else:
            print(f"Error activating workflow: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error activating workflow: {e}")
        return False

def main():
    print("🔄 Activating N8N VoIP Workflow...")

    # Cargar workflow
    workflow_data = load_workflow()
    print(f"📁 Loaded workflow: {workflow_data['name']}")

    # Verificar workflows existentes
    existing_workflows = get_workflows()

    # Buscar si ya existe
    existing_workflow = None
    for wf in existing_workflows:
        if wf['name'] == workflow_data['name']:
            existing_workflow = wf
            break

    if existing_workflow:
        print(f"📋 Found existing workflow: {existing_workflow['id']}")
        workflow_id = existing_workflow['id']

        # Verificar si ya está activo
        if existing_workflow.get('active', False):
            print("✅ Workflow is already active!")
        else:
            print("🔧 Activating existing workflow...")
            activate_workflow(workflow_id)
    else:
        print("🆕 Creating new workflow...")
        created_workflow = create_workflow(workflow_data)

        if created_workflow:
            workflow_id = created_workflow['id']
            print(f"✅ Workflow created with ID: {workflow_id}")

            # Activar el workflow
            print("🔧 Activating workflow...")
            time.sleep(2)  # Esperar un poco
            activate_workflow(workflow_id)
        else:
            print("❌ Failed to create workflow")
            return

    # Verificar estado final
    print("\n🔍 Final verification...")
    final_workflows = get_workflows()
    for wf in final_workflows:
        if wf['name'] == workflow_data['name']:
            status = "🟢 ACTIVE" if wf.get('active', False) else "🔴 INACTIVE"
            print(f"Workflow: {wf['name']} - {status}")

            if wf.get('active', False):
                print(f"\n✅ SUCCESS! Webhook URL available at:")
                print(f"📞 http://localhost:5678/webhook/voip-agent")
            break

if __name__ == "__main__":
    main()