import asyncio
import numpy as np
import faster_whisper
from utils import get_env, setup_log
from vad import VadController
import tempfile
import wave
import os

class STTWorker:
    def __init__(self):
        self.logger = setup_log("stt")
        self.model_name = get_env("WHISPER_MODEL", "base")  # Optimizado para VoIP tiempo real
        self.vad = VadController()
        self.sample_rate = 8000  # Ajustado a 8kHz para compatibilidad con Asterisk
        try:
            self.model = faster_whisper.WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8"
            )
            self.logger.info(f"STT inicializado con modelo: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Error inicializando Whisper: {e}")
            raise
        self.window_ms = 300

    async def process_audio(self, audio):
        """Procesa audio en streaming con ventanas de 300 ms."""
        try:
            if audio is None or len(audio) == 0:
                self.logger.error("No se recibió audio para transcripción")
                return []

            # Convertir a float32 para VAD
            if audio.dtype != np.float32:
                audio_float = audio.astype(np.float32) / 32768.0
            else:
                audio_float = audio

            # Usar VAD para filtrar audio sin voz
            if not self.vad.process(audio_float):
                self.logger.debug("No se detectó voz")
                return []

            # Guardar audio temporalmente como WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                with wave.open(tmp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio.tobytes())

            self.logger.info(f"Archivo WAV temporal creado: {tmp_path}")

            # Transcribir con faster-whisper OPTIMIZADO para baja latencia
            segments, info = self.model.transcribe(
                tmp_path,
                language="es",
                task="transcribe",
                beam_size=1,  # Greedy decoding (5x más rápido que default beam_size=5)
                temperature=0.0,  # Decisiones determinísticas sin sampling
                vad_filter=False,  # VAD ya se hace externamente con Silero
                condition_on_previous_text=False,  # Sin contexto entre segmentos
                without_timestamps=True,  # Más rápido sin timestamps
                word_timestamps=False
            )

            result = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    result.append(text)
                    self.logger.info(f"Transcripción: {text}")

            os.unlink(tmp_path)
            return result if result else []

        except Exception as e:
            self.logger.error(f"Error en transcripción: {e}")
            return []

    def cleanup(self):
        """Limpia recursos del modelo."""
        if hasattr(self, 'model'):
            del self.model
            self.logger.info("Modelo STT limpiado")
