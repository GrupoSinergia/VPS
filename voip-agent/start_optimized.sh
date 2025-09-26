#!/bin/bash

# Script optimizado para VoIP Agent con baja latencia
# Configurado para rendimiento máximo en tiempo real

echo "=== Iniciando VoIP Agent Optimizado para Baja Latencia ==="

# Configurar variables de entorno para rendimiento
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Configuraciones de sistema para baja latencia (opcional, requiere permisos)
# echo "Configurando sistema para baja latencia..."
# sudo sysctl -w net.core.rmem_max=134217728
# sudo sysctl -w net.core.wmem_max=134217728
# sudo sysctl -w net.ipv4.tcp_rmem="4096 16384 134217728"
# sudo sysctl -w net.ipv4.tcp_wmem="4096 16384 134217728"

# Verificar que /var/lib/asterisk/sounds/tts existe
if [ ! -d "/var/lib/asterisk/sounds/tts" ]; then
    echo "Creando directorio para TTS..."
    sudo mkdir -p /var/lib/asterisk/sounds/tts
    sudo chown asterisk:asterisk /var/lib/asterisk/sounds/tts
    sudo chmod 755 /var/lib/asterisk/sounds/tts
fi

# Configuración de entorno por defecto (ajustar según necesidad)
export ARI_URL="${ARI_URL:-http://127.0.0.1:8088}"
export ARI_USER="${ARI_USER:-ari}"
export ARI_PASS="${ARI_PASS:-secret}"
export ARI_APP="${ARI_APP:-agente-ia}"
export RTP_IN_HOST="${RTP_IN_HOST:-127.0.0.1}"
export RTP_IN_PORT="${RTP_IN_PORT:-4000}"
export RTP_OUT_HOST="${RTP_OUT_HOST:-127.0.0.1}"
export RTP_OUT_PORT="${RTP_OUT_PORT:-4002}"
export PROMETHEUS_PORT="${PROMETHEUS_PORT:-9091}"

# IMPORTANTE: Configurar tu webhook de n8n aquí
export N8N_WEBHOOK="${N8N_WEBHOOK:-http://localhost:5678/webhook/voip}"

echo "=== Configuración ==="
echo "ARI URL: $ARI_URL"
echo "ARI APP: $ARI_APP"
echo "RTP IN: $RTP_IN_HOST:$RTP_IN_PORT"
echo "RTP OUT: $RTP_OUT_HOST:$RTP_OUT_PORT"
echo "Prometheus: $PROMETHEUS_PORT"
echo "N8N Webhook: $N8N_WEBHOOK"
echo ""

echo "=== Iniciando agente con optimizaciones de tiempo real ==="
echo "✅ Sleep fijos eliminados - Eventos ARI"
echo "✅ Barge-in implementado - Interrupciones de voz"
echo "✅ STT asíncrono - ThreadPoolExecutor"
echo "✅ VAD continuo - Chunks de 100ms"
echo "✅ Cache TTS - Respuestas pre-generadas"
echo "✅ HTTP session reutilizable - Latencia reducida"
echo ""

# Ejecutar con prioridad alta (requiere permisos)
if command -v nice &> /dev/null; then
    echo "Ejecutando con prioridad alta..."
    exec nice -n -10 python3 app.py
else
    echo "Ejecutando con prioridad normal..."
    exec python3 app.py
fi