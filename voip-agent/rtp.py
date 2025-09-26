import asyncio
import numpy as np
import struct
import socket
import opus
import os
from utils import setup_log

class RTPProcessor:
    def __init__(self):
        self.logger = setup_log("rtp")
        self.sample_rate = 8000
        self.channels = 1
        self.frame_duration_ms = 20
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        self.logger.info(f"RTPProcessor inicializado con sample_rate: {self.sample_rate}")

    def decode_opus(self, opus_data, frame_size):
        """Decodificar datos de audio OPUS."""
        try:
            decoder = opus.Decoder(self.sample_rate, self.channels)
            return decoder.decode(opus_data, frame_size)
        except Exception as e:
            self.logger.error(f"Error decodificando audio: {e}")
            return None

    async def receive_audio(self, channel, duration=5):
        """Capturar audio entrante usando MixMonitor."""
        try:
            self.logger.info(f"Iniciando captura de audio con MixMonitor para canal {channel.id}")
            recording_name = f"recording_{channel.id}"
            recording_file = f"/var/spool/asterisk/recording/{recording_name}.slin"
            
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(recording_file), exist_ok=True)
            
            # Usar MixMonitor en lugar de channel.record
            # El formato 'r' captura solo el audio recibido (del usuario)
            await channel.startMixMonitor(f"recording/{recording_name}.slin,r")
            self.logger.info(f"MixMonitor iniciado: {recording_file}")
            
            # Esperar la duración especificada
            await asyncio.sleep(duration)
            
            # Parar MixMonitor
            try:
                await channel.stopMixMonitor()
                self.logger.info("MixMonitor detenido")
            except Exception as e:
                self.logger.warning(f"Error parando MixMonitor: {e}")
            
            # Pequeña pausa para que termine de escribir el archivo
            await asyncio.sleep(0.5)
            
            # Verificar si el archivo existe
            if not os.path.exists(recording_file):
                self.logger.error(f"Archivo de grabación no encontrado: {recording_file}")
                return None
            
            # Verificar que el archivo no esté vacío
            file_size = os.path.getsize(recording_file)
            if file_size == 0:
                self.logger.error(f"Archivo de grabación vacío: {recording_file}")
                os.unlink(recording_file)
                return None
            
            # Leer el archivo de audio
            with open(recording_file, 'rb') as f:
                audio_data = np.frombuffer(f.read(), dtype=np.int16)
            
            self.logger.info(f"Audio capturado: {len(audio_data)} samples ({file_size} bytes)")
            
            # Limpiar archivo temporal
            try:
                os.unlink(recording_file)
            except Exception as e:
                self.logger.warning(f"Error eliminando archivo temporal: {e}")
            
            # Validar que tenemos datos de audio útiles
            if len(audio_data) < 1000:  # Menos de 1000 samples probablemente es solo silencio
                self.logger.warning("Audio capturado muy corto, probablemente silencio")
                return None
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Error capturando audio: {e}")
            return None

    async def send_audio(self, channel, audio_data, sample_rate=8000):
        """Enviar audio saliente al canal PJSIP."""
        try:
            self.logger.info(f"Enviando audio a canal {channel.id}")
            
            if audio_data is None or len(audio_data) == 0:
                self.logger.error("No hay datos de audio para enviar")
                return False
            
            # Convertir audio_data a formato apropiado si es necesario
            if audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)
            
            # Aquí se implementaría el envío de audio RTP
            # Por ahora, esto se maneja via TTS y playback en app.py
            self.logger.info(f"Audio preparado para envío: {len(audio_data)} samples")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enviando audio: {e}")
            return False

    def validate_audio(self, audio_data):
        """Validar que los datos de audio son útiles."""
        if audio_data is None or len(audio_data) == 0:
            return False
        
        # Verificar que no sea solo silencio
        audio_abs = np.abs(audio_data)
        max_amplitude = np.max(audio_abs)
        rms = np.sqrt(np.mean(audio_abs ** 2))
        
        # Si la amplitud máxima es muy baja, probablemente es silencio
        if max_amplitude < 100 or rms < 50:
            self.logger.debug(f"Audio rechazado: amplitud muy baja (max: {max_amplitude}, rms: {rms:.2f})")
            return False
        
        return True

    def cleanup(self):
        """Limpiar recursos del procesador RTP."""
        try:
            # Limpiar archivos temporales de grabación
            recording_dir = "/var/spool/asterisk/recording"
            if os.path.exists(recording_dir):
                for filename in os.listdir(recording_dir):
                    if filename.startswith("recording_") and filename.endswith(".slin"):
                        filepath = os.path.join(recording_dir, filename)
                        try:
                            os.unlink(filepath)
                            self.logger.debug(f"Archivo temporal limpiado: {filename}")
                        except Exception as e:
                            self.logger.warning(f"Error limpiando {filename}: {e}")
            
            self.logger.info("Limpieza de RTPProcessor completada")
        except Exception as e:
            self.logger.error(f"Error en limpieza de RTPProcessor: {e}")
