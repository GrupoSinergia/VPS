#!/usr/bin/env python3
"""
Dashboard simple para visualizar métricas de tiempo del VoIP Agent
"""
import requests
import time
import json
from datetime import datetime

def get_metric(metric_name):
    """Obtener métrica de Prometheus"""
    try:
        response = requests.get(f"http://localhost:9090/api/v1/query?query={metric_name}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                return float(data['data']['result'][0]['value'][1])
        return 0.0
    except:
        return 0.0

def get_direct_metrics():
    """Obtener métricas directamente del VoIP Agent"""
    try:
        response = requests.get("http://localhost:9091/metrics", timeout=5)
        if response.status_code == 200:
            content = response.text
            metrics = {}
            for line in content.split('\n'):
                if 'stt_latency_seconds' in line and not line.startswith('#'):
                    metrics['stt'] = float(line.split()[-1])
                elif 'tts_latency_seconds' in line and not line.startswith('#'):
                    metrics['tts'] = float(line.split()[-1])
                elif 'llm_latency_seconds' in line and not line.startswith('#'):
                    metrics['llm'] = float(line.split()[-1])
            return metrics
        return {}
    except:
        return {}

def get_webhook_logs():
    """Obtener estadísticas del webhook server"""
    try:
        response = requests.get("http://localhost:5679/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def show_dashboard():
    """Mostrar dashboard de métricas"""
    print("\033[2J\033[H")  # Clear screen
    print("=" * 80)
    print("🎯 DASHBOARD DE TIMING - VoIP Agent")
    print("=" * 80)
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Métricas directas del VoIP Agent
    print("📊 MÉTRICAS DIRECTAS DEL VoIP AGENT:")
    print("-" * 40)
    direct_metrics = get_direct_metrics()

    if direct_metrics:
        stt_time = direct_metrics.get('stt', 0.0)
        tts_time = direct_metrics.get('tts', 0.0)
        llm_time = direct_metrics.get('llm', 0.0)
        total_time = stt_time + tts_time + llm_time

        print(f"🎤 STT Latency:  {stt_time:.3f}s")
        print(f"🧠 LLM Latency:  {llm_time:.3f}s")
        print(f"🔊 TTS Latency:  {tts_time:.3f}s")
        print(f"⚡ TOTAL:        {total_time:.3f}s")

        if total_time > 0:
            print()
            print("📈 DISTRIBUCIÓN DE TIEMPO:")
            if stt_time > 0:
                stt_pct = (stt_time / total_time) * 100
                print(f"   STT: {stt_pct:.1f}% {'█' * int(stt_pct/5)}")
            if llm_time > 0:
                llm_pct = (llm_time / total_time) * 100
                print(f"   LLM: {llm_pct:.1f}% {'█' * int(llm_pct/5)}")
            if tts_time > 0:
                tts_pct = (tts_time / total_time) * 100
                print(f"   TTS: {tts_pct:.1f}% {'█' * int(tts_pct/5)}")
    else:
        print("❌ No hay métricas disponibles (no se han procesado llamadas)")

    print()
    print("🌐 ESTADO DEL WEBHOOK SERVER:")
    print("-" * 40)
    webhook_status = get_webhook_logs()
    if webhook_status:
        print(f"🟢 Status: {webhook_status.get('status', 'unknown')}")
        print(f"🤖 Ollama: {webhook_status.get('ollama_status', 'unknown')}")
        print(f"📡 Service: {webhook_status.get('service', 'unknown')}")
    else:
        print("❌ Webhook server no responde")

    print()
    print("💡 ANÁLISIS DE RENDIMIENTO:")
    print("-" * 40)
    if direct_metrics and any(direct_metrics.values()):
        total = sum(direct_metrics.values())
        if total < 3:
            print("🚀 EXCELENTE: Latencia muy baja para VoIP")
        elif total < 5:
            print("⚡ BUENO: Latencia aceptable para VoIP")
        elif total < 10:
            print("⚠️  REGULAR: Latencia alta, considerar optimización")
        else:
            print("🐌 LENTO: Latencia muy alta, requiere optimización")

        print(f"   Tiempo total de respuesta: {total:.3f}s")
        print(f"   Objetivo para VoIP: < 3.0s")
    else:
        print("📊 Esperando datos de llamadas VoIP...")

    print()
    print("🔄 Actualizando cada 3 segundos... (Ctrl+C para salir)")
    print("=" * 80)

def main():
    """Main dashboard loop"""
    try:
        while True:
            show_dashboard()
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard terminado")

if __name__ == "__main__":
    main()