from prometheus_client import Gauge

# Métricas de latencia
stt_latency = Gauge('stt_processing_time_seconds', 'Tiempo de procesamiento STT en segundos')
llm_latency = Gauge('llm_processing_time_seconds', 'Tiempo de procesamiento LLM en segundos')
tts_latency = Gauge('tts_processing_time_seconds', 'Tiempo de procesamiento TTS en segundos')

def update_metrics(stt_time, llm_time, tts_time):
    stt_latency.set(stt_time)
    llm_latency.set(llm_time)
    tts_latency.set(tts_time)
