#!/usr/bin/env python3
"""
Servidor webhook directo para VoIP Agent
Reemplaza temporalmente a N8N para que tengas la funcionalidad completa
"""
from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "llama3.2:3b-instruct-q4_k_m"

SYSTEM_PROMPT = """Eres un asistente virtual especializado para un negocio de automatización y tecnología.
Tu personalidad es profesional pero amigable, conciso y siempre dispuesto a ayudar.

INFORMACIÓN DEL NEGOCIO:
- Nombre: Negocio de Automatización y Tecnología
- Horarios: Lunes a viernes 9:00 AM - 6:00 PM
- Servicios: Automatización de procesos, desarrollo de software, consultoría IT
- Teléfono: +526147420077
- Email: contacto@negocio.com

INSTRUCCIONES:
- Responde SOLO en español
- Mantén respuestas cortas (máximo 2 oraciones para VoIP)
- Si necesitas información específica, pregunta directamente
- Para citas, solicita: fecha, hora preferida, y motivo
- Si no puedes ayudar, ofrece transferir "con un especialista"

CONTEXTO: El usuario está llamando por teléfono. Responde de manera natural y útil."""

@app.route('/webhook/voip-agent', methods=['POST'])
def voip_webhook():
    """Webhook principal para VoIP Agent"""
    try:
        # Obtener datos del request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' in request"}), 400

        user_text = data['text']
        logger.info(f"📞 VoIP Request: {user_text}")

        # Llamar a Ollama
        ollama_response = call_ollama(user_text)

        if ollama_response:
            # Procesar respuesta
            response_data = process_response(user_text, ollama_response)
            logger.info(f"🤖 AI Response: {response_data['response']}")
            return jsonify(response_data)
        else:
            # Respuesta de fallback
            fallback_response = {
                "response": "Lo siento, estoy experimentando problemas técnicos. ¿Podrías llamar en unos minutos?",
                "user_input": user_text,
                "intent_detected": "technical_error",
                "timestamp": datetime.now().isoformat(),
                "status": "fallback"
            }
            return jsonify(fallback_response)

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({
            "response": "Disculpa, tengo un problema técnico. Intenta de nuevo por favor.",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }), 500

def call_ollama(user_text):
    """Llamar a Ollama para generar respuesta"""
    try:
        # Construir prompt completo
        full_prompt = f"{SYSTEM_PROMPT}\\n\\nUsuario dice: {user_text}\\n\\nRespuesta:"

        # Payload para Ollama
        payload = {
            "model": MODEL_NAME,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "max_tokens": 200,
                "top_p": 0.9
            }
        }

        logger.info(f"🔄 Calling Ollama...")
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            logger.error(f"❌ Ollama error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"❌ Ollama call failed: {e}")
        return None

def process_response(user_input, ai_response):
    """Procesar y formatear respuesta"""
    # Detectar intención básica
    intent = detect_intent(user_input)

    # Limitar longitud para VoIP
    if len(ai_response) > 200:
        ai_response = ai_response[:197] + "..."

    return {
        "response": ai_response,
        "user_input": user_input,
        "intent_detected": intent,
        "timestamp": datetime.now().isoformat(),
        "conversation_context": "voip_call",
        "status": "success"
    }

def detect_intent(text):
    """Detectar intención básica del usuario"""
    text_lower = text.lower()

    if any(word in text_lower for word in ['cita', 'agendar', 'reunión', 'agenda']):
        return 'schedule'
    elif any(word in text_lower for word in ['cancelar', 'cambiar']):
        return 'cancel'
    elif any(word in text_lower for word in ['horario', 'cuándo', 'hora']):
        return 'hours'
    elif any(word in text_lower for word in ['servicio', 'precio', 'costo']):
        return 'services'
    elif any(word in text_lower for word in ['adiós', 'gracias', 'bye']):
        return 'goodbye'
    elif any(word in text_lower for word in ['hola', 'buenos', 'buenas']):
        return 'greeting'
    else:
        return 'general'

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "VoIP Webhook Server",
        "timestamp": datetime.now().isoformat(),
        "ollama_status": check_ollama_health()
    })

def check_ollama_health():
    """Verificar si Ollama está disponible"""
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        return "online" if response.status_code == 200 else "offline"
    except:
        return "offline"

@app.route('/', methods=['GET'])
def root():
    """Endpoint raíz"""
    return jsonify({
        "message": "VoIP Webhook Server is running",
        "endpoints": {
            "webhook": "/webhook/voip-agent",
            "health": "/health"
        },
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting VoIP Webhook Server...")
    print("📞 Webhook URL: http://localhost:5679/webhook/voip-agent")
    print("🏥 Health Check: http://localhost:5679/health")
    print("⚡ Ready to receive VoIP calls!")

    app.run(host='0.0.0.0', port=5679, debug=False)