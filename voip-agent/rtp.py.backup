import asyncio
import numpy as np
import opuslib
import silero_vad
from utils import setup_log
import os

class RTPProcessor:
    def __init__(self, sample_rate=8000):
        self.logger = setup_log(__name__)
        self.sample_rate = sample_rate
        self.encoder = opuslib.Encoder(fs=sample_rate, channels=1, application=opuslib.APPLICATION_VOIP)
        self.encoder.bitrate = 20000
        self.vad_model = silero_vad.load_silero_vad()
        self.logger.info(f"RTPProcessor inicializado con sample_rate: {sample_rate}")

    def encode(self, pcm):
        """Codificar audio PCM a Opus."""
        self.logger.info("Codificando audio para RTP")
        try:
            return self.encoder.encode(pcm.astype(np.int16).tobytes(), frame_size=len(pcm))
        except Exception as e:
            self.logger.error(f"Error codificando audio: {e}")
            return None

    def vad_process(self, pcm):
        """Procesar audio con VAD para detectar voz."""
        try:
            if pcm.dtype != np.float32:
                audio = pcm.astype(np.float32) / 32768.0
            else:
                audio = pcm
            speech_timestamps = silero_vad.get_speech_timestamps(audio, self.vad_model, sampling_rate=self.sample_rate)
            self.logger.debug(f"VAD detectó {len(speech_timestamps)} segmentos de voz")
            return len(speech_timestamps) > 0
        except Exception as e:
            self.logger.error(f"Error en VAD: {e}")
            return False

    def decode(self, opus_data, frame_size=160):
        """Decodificar audio Opus a PCM."""
        try:
            decoder = opuslib.Decoder(fs=self.sample_rate, channels=1)
            return decoder.decode(opus_data, frame_size)
        except Exception as e:
            self.logger.error(f"Error decodificando audio: {e}")
            return None

    async def receive_audio(self, channel, duration=5):
        """Capturar audio entrante desde el canal PJSIP."""
        try:
            self.logger.info(f"Iniciando captura de audio RTP para canal {channel.id}")
            recording_name = f"recording_{channel.id}"
            recording_file = f"/var/spool/asterisk/recording/{recording_name}.slin"
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(recording_file), exist_ok=True)
            await channel.record(
                name=recording_name,
                format="slin",
                maxDurationSeconds=duration,
                maxSilenceSeconds=2,
                ifExists="overwrite"
            )
            self.logger.info(f"Grabación iniciada: {recording_file}")
            await asyncio.sleep(duration + 1)
            if not os.path.exists(recording_file):
                self.logger.error(f"Archivo de grabación no encontrado: {recording_file}")
                return None
            with open(recording_file, 'rb') as f:
                audio_data = np.frombuffer(f.read(), dtype=np.int16)
            self.logger.info(f"Audio capturado: {len(audio_data)} samples")
            os.unlink(recording_file)
            return audio_data
        except Exception as e:
            self.logger.error(f"Error capturando audio RTP: {e}")
            return None
