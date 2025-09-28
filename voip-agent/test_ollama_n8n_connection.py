#!/usr/bin/env python3
import requests
import json
import time

def test_ollama_connection():
    """Probar la conexión directa a Ollama"""
    print("🧪 Testing Ollama Docker connection...")

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Ollama is running with {len(models['models'])} models")
            for model in models['models']:
                print(f"   - {model['name']}")
            return True
        else:
            print(f"❌ Ollama returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        return False

def test_ollama_generation():
    """Probar generación de texto con Ollama"""
    print("\n🤖 Testing Ollama text generation...")

    payload = {
        "model": "llama3.2:3b-instruct-q4_k_m",
        "prompt": "Hola, ¿cómo estás? Responde brevemente en español.",
        "stream": False
    }

    try:
        response = requests.post("http://localhost:11434/api/generate",
                               json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Generation successful:")
            print(f"   Prompt: {payload['prompt']}")
            print(f"   Response: {result['response']}")
            return True
        else:
            print(f"❌ Generation failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to generate text: {e}")
        return False

def test_n8n_access():
    """Verificar acceso a n8n"""
    print("\n🌐 Testing n8n access...")

    try:
        response = requests.get("http://localhost:5678", timeout=10)
        if response.status_code == 200:
            print("✅ n8n is accessible at http://localhost:5678")
            print("   Username: admin")
            print("   Password: Sparkurlife5.")
            return True
        else:
            print(f"❌ n8n returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to access n8n: {e}")
        return False

def show_docker_status():
    """Mostrar estado de contenedores Docker"""
    print("\n🐳 Docker Container Status:")
    import subprocess
    try:
        result = subprocess.run(["docker", "ps", "--format",
                               "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"],
                               capture_output=True, text=True, check=True)
        print(result.stdout)
    except Exception as e:
        print(f"❌ Failed to get Docker status: {e}")

def main():
    print("=" * 60)
    print("🚀 OLLAMA + N8N DOCKER CONNECTION TEST")
    print("=" * 60)

    show_docker_status()

    # Probar cada componente
    ollama_ok = test_ollama_connection()
    n8n_ok = test_n8n_access()

    if ollama_ok:
        generation_ok = test_ollama_generation()
    else:
        generation_ok = False

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Ollama Docker:     {'✅ OK' if ollama_ok else '❌ FAIL'}")
    print(f"Text Generation:   {'✅ OK' if generation_ok else '❌ FAIL'}")
    print(f"n8n Access:        {'✅ OK' if n8n_ok else '❌ FAIL'}")

    if ollama_ok and n8n_ok:
        print("\n🎉 SUCCESS! Your configuration is working correctly!")
        print("\n📋 Next Steps:")
        print("1. Go to http://localhost:5678")
        print("2. Login with admin / Sparkurlife5.")
        print("3. Your Ollama credentials should now use: http://ollama:11434")
        print("4. Test your workflow - the connection should work!")
        print("\n💡 The containers can communicate using the service name 'ollama'")
    else:
        print("\n❌ Some components are not working properly.")
        print("Please check the Docker containers and network configuration.")

if __name__ == "__main__":
    main()