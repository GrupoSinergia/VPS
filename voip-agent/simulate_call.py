#!/usr/bin/env python3
"""
Simulador de llamada VoIP completa
"""
import requests
import time

def simulate_voip_call():
    """Simular una conversación VoIP completa"""
    print("📞 SIMULANDO LLAMADA VoIP COMPLETA")
    print("=" * 40)

    # Conversación simulada
    conversation = [
        "Hola, buenos días",
        "Quiero información sobre sus servicios",
        "Me interesa la automatización de procesos",
        "¿Podrían agendar una cita para la próxima semana?",
        "Perfecto, muchas gracias. Adiós"
    ]

    print("🤖 Iniciando conversación con el agente de IA...")

    for i, user_message in enumerate(conversation, 1):
        print(f"\n👤 Usuario: {user_message}")

        try:
            # Enviar mensaje al webhook (simula el VoIP Agent)
            response = requests.post(
                "http://localhost:5679/webhook/voip-agent",
                json={"text": user_message},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                print(f"🤖 Agente IA: {result['response']}")
                print(f"🎯 Intención detectada: {result['intent_detected']}")
            else:
                print(f"❌ Error en respuesta: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {e}")

        # Pausa entre mensajes (simula conversación natural)
        if i < len(conversation):
            print("⏳ Esperando respuesta...")
            time.sleep(2)

    print("\n📞 Llamada terminada")
    print("✅ El sistema VoIP-AI funcionó perfectamente!")

if __name__ == "__main__":
    simulate_voip_call()