#!/usr/bin/env python3
import requests
import json
import time

def test_webhook():
    """Probar webhook de N8N"""
    url = "http://localhost:5678/webhook/voip-agent"
    test_data = {"text": "hola, como estas?"}

    print("🧪 Testing N8N VoIP Webhook...")
    print(f"📡 URL: {url}")
    print(f"📝 Test message: {test_data['text']}")

    try:
        response = requests.post(
            url,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! Webhook is working")
            print(f"🤖 AI Response: {result.get('response', 'No response')}")
            print(f"🎯 Intent: {result.get('intent_detected', 'Unknown')}")
            return True
        elif response.status_code == 404:
            print("❌ WORKFLOW NOT ACTIVE")
            print("💡 Please activate the workflow in N8N interface")
            return False
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ TIMEOUT - Webhook took too long to respond")
        print("💡 Check if Ollama is responding correctly")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_ollama():
    """Probar conectividad con Ollama"""
    print("\n🔍 Testing Ollama connectivity...")

    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            print(f"✅ Ollama is working - Models: {models}")
            return True
        else:
            print(f"❌ Ollama error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 VoIP Integration Test\n")

    # Test Ollama first
    ollama_ok = test_ollama()

    if ollama_ok:
        # Test webhook
        webhook_ok = test_webhook()

        if webhook_ok:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Ready for VoIP calls!")
        else:
            print("\n⚠️  NEXT STEPS:")
            print("1. Access N8N at http://localhost:5678")
            print("2. Open 'VoIP AI Agent Completo' workflow")
            print("3. Configure Ollama credential if needed")
            print("4. Activate the workflow")
            print("5. Run this test again")
    else:
        print("\n❌ Fix Ollama connection first")