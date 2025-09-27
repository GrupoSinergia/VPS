#!/usr/bin/env python3
import requests
import json
import time

def test_ollama_from_docker():
    """Probar si Ollama es accesible desde la perspectiva de Docker"""
    print("🔍 Testing Ollama from Docker perspective...")

    # Probar desde la IP que usa N8N
    test_urls = [
        "http://172.17.0.1:11434/api/tags",
        "http://host.docker.internal:11434/api/tags",
        "http://127.0.0.1:11434/api/tags"
    ]

    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {url} - WORKING")
                return url.replace("/api/tags", "")
            else:
                print(f"❌ {url} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {url} - Error: {e}")

    return None

def test_ollama_generate():
    """Probar generación de texto con Ollama"""
    print("\n🤖 Testing Ollama text generation...")

    base_url = test_ollama_from_docker()
    if not base_url:
        print("❌ Cannot reach Ollama from any URL")
        return False

    try:
        url = f"{base_url}/api/generate"
        data = {
            "model": "llama3.2:3b-instruct-q4_k_m",
            "prompt": "Responde brevemente: ¿Cómo estás?",
            "stream": False
        }

        print(f"📡 Testing: {url}")
        response = requests.post(url, json=data, timeout=60)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ollama generation working!")
            print(f"🤖 Response: {result.get('response', '')[:100]}...")
            return True
        else:
            print(f"❌ Generation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Generation error: {e}")
        return False

def test_webhook_detailed():
    """Probar webhook con análisis detallado"""
    print("\n🧪 Testing webhook with detailed analysis...")

    url = "http://localhost:5678/webhook/voip-agent"
    data = {"text": "¿Cómo puedo agendar una cita?"}

    try:
        print(f"📡 Sending request to: {url}")
        print(f"📝 Data: {json.dumps(data)}")

        response = requests.post(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 minutos
        )

        print(f"📊 Status: {response.status_code}")
        print(f"📏 Content Length: {len(response.content)}")
        print(f"🏷️ Headers: {dict(response.headers)}")

        if response.content:
            print(f"📄 Raw Content: {response.content}")
            try:
                json_response = response.json()
                print(f"✅ JSON Response: {json.dumps(json_response, indent=2)}")
                return True
            except:
                print(f"📄 Text Response: {response.text}")
        else:
            print("❌ Empty response")

        return False

    except requests.exceptions.Timeout:
        print("⏰ Webhook timeout - N8N/Ollama may be processing")
        return False
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False

def main():
    """Diagnóstico completo"""
    print("🔧 VoIP Integration Debug Tool\n")

    # Test 1: Ollama connectivity
    ollama_working = test_ollama_generate()

    if ollama_working:
        # Test 2: Webhook
        webhook_working = test_webhook_detailed()

        if webhook_working:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Integration is working correctly")
        else:
            print("\n⚠️ Webhook issue detected")
            print("💡 Check N8N workflow configuration")
    else:
        print("\n❌ Ollama connectivity issue")
        print("💡 Check Ollama configuration and firewall")

    print(f"\n📞 VoIP Agent Status: ", end="")
    import subprocess
    result = subprocess.run(["pgrep", "-f", "python3 app.py"], capture_output=True)
    if result.returncode == 0:
        print("🟢 RUNNING")
    else:
        print("🔴 NOT RUNNING")

if __name__ == "__main__":
    main()