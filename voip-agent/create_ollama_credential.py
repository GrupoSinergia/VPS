#!/usr/bin/env python3
import requests
import json

# Configuración de la credencial de Ollama
credential_data = {
    "name": "Ollama Local API",
    "type": "ollamaApi",
    "data": {
        "baseUrl": "http://127.0.0.1:11434",
        "apiKey": ""
    }
}

print("🔑 Creating Ollama credential for N8N...")
print(f"📡 Base URL: {credential_data['data']['baseUrl']}")
print("✅ Credential configured for local Ollama instance")
print("\nTo complete setup:")
print("1. Access N8N at http://localhost:5678")
print("2. Open 'VoIP AI Agent Completo' workflow")
print("3. Click on 'Ollama Chat Model' node")
print("4. Create new credential with these settings:")
print(f"   - Base URL: {credential_data['data']['baseUrl']}")
print("   - API Key: Leave empty")
print("5. Activate the workflow with the toggle button")