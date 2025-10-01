import numpy as np
import silero_vad
from utils import get_env, setup_log

class VadController:
    def __init__(self):
        self.logger = setup_log("vad")
        self.sample_rate = int(get_env("SAMPLE_RATE", 8000))
        # OPTIMIZADO: Umbral más bajo para mayor sensibilidad (0.3 en vez de 0.5)
        self.vad_sensitivity = float(get_env("VAD_SENSITIVITY", 0.3))
        self.frame_ms = int(get_env("FRAME_MS", 20))
        self.model = silero_vad.load_silero_vad()
        self.logger.info(f"✅ VAD inicializado - sensitivity: {self.vad_sensitivity}, sample_rate: {self.sample_rate}Hz")

    def process(self, audio_data):
        """
        Procesa audio para detectar voz usando silero-vad ULTRA-OPTIMIZADO
        """
        try:
            # Validar entrada
            if audio_data is None or len(audio_data) == 0:
                self.logger.warning("⚠️ VAD: Audio vacío")
                return False

            # Convertir a float32 si es necesario
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0

            # Normalizar audio para mejor detección
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val

            # Detectar segmentos de voz con parámetros optimizados
            speech_timestamps = silero_vad.get_speech_timestamps(
                audio_data,
                self.model,
                sampling_rate=self.sample_rate,
                threshold=self.vad_sensitivity,
                min_speech_duration_ms=250,  # Mínimo 250ms de habla
                min_silence_duration_ms=100,  # Máximo 100ms de silencio entre palabras
                speech_pad_ms=30  # Padding de 30ms antes/después
            )

            has_speech = len(speech_timestamps) > 0

            if has_speech:
                total_speech_ms = sum(
                    (seg['end'] - seg['start']) for seg in speech_timestamps
                )
                self.logger.info(f"🎙️ VAD DETECTÓ VOZ: {len(speech_timestamps)} segmentos, {total_speech_ms}ms de habla")
            else:
                self.logger.debug("🔇 VAD: No se detectó voz en el audio")

            return has_speech

        except Exception as e:
            self.logger.error(f"❌ Error en VAD: {e}")
            return False
