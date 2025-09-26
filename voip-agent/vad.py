import numpy as np
import silero_vad
from utils import get_env, setup_log

class VadController:
    def __init__(self):
        self.logger = setup_log("vad")
        self.sample_rate = int(get_env("SAMPLE_RATE", 8000))
        self.vad_sensitivity = float(get_env("VAD_SENSITIVITY", 0.5))
        self.frame_ms = int(get_env("FRAME_MS", 20))
        self.model = silero_vad.load_silero_vad()

    def process(self, audio_data):
        """Procesa audio para detectar voz usando silero-vad."""
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32) / 32768.0
        speech_timestamps = silero_vad.get_speech_timestamps(
            audio_data,
            self.model,
            sampling_rate=self.sample_rate,
            threshold=self.vad_sensitivity
        )
        self.logger.info(f"VAD detectó {len(speech_timestamps)} segmentos de voz")
        return len(speech_timestamps) > 0
