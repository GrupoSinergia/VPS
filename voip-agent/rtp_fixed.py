import asyncio
import numpy as np
import os
import logging
from utils import setup_log

class RTPProcessor:
    def __init__(self):
        self.logger = setup_log("rtp")
        self.sample_rate = 8000
        self.logger.info(f"RTPProcessor inicializado con sample_rate: {self.sample_rate}")
        # Manejar grabaciones activas para evitar conflictos
        self.active_recordings = {}
        self.recording_lock = asyncio.Lock()

    async def capture_audio(self, channel, duration=5):
        """Capturar audio entrante desde el canal PJSIP con manejo de conflictos."""
        async with self.recording_lock:
            channel_id = channel.id

            # Verificar si ya hay una grabación activa para este canal
            if channel_id in self.active_recordings:
                self.logger.warning(f"Grabación ya activa para canal {channel_id}, esperando...")
                try:
                    await asyncio.wait_for(self.active_recordings[channel_id], timeout=duration + 2)
                except asyncio.TimeoutError:
                    self.logger.warning(f"Timeout esperando grabación anterior para canal {channel_id}")
                except Exception as e:
                    self.logger.error(f"Error esperando grabación anterior: {e}")

            # Crear nueva grabación
            recording_task = asyncio.create_task(self._do_recording(channel, duration))
            self.active_recordings[channel_id] = recording_task

            try:
                result = await recording_task
                return result
            finally:
                # Limpiar grabación completada
                if channel_id in self.active_recordings:
                    del self.active_recordings[channel_id]

    async def _do_recording(self, channel, duration):
        """Realizar la grabación real."""
        try:
            self.logger.info(f"Iniciando captura de audio RTP para canal {channel.id}")
            recording_name = f"recording_{channel.id}_{int(asyncio.get_event_loop().time())}"
            recording_file = f"/var/spool/asterisk/recording/{recording_name}.slin"

            # Crear directorio si no existe
            os.makedirs(os.path.dirname(recording_file), exist_ok=True)

            # Detener cualquier grabación previa
            try:
                await channel.stop_recording(recording_name)
            except:
                pass  # Ignorar si no había grabación previa

            # Iniciar nueva grabación
            await channel.record(
                name=recording_name,
                format="slin",
                maxDurationSeconds=duration,
                maxSilenceSeconds=2,
                ifExists="overwrite"
            )

            self.logger.info(f"Grabación iniciada: {recording_file}")

            # Esperar a que termine la grabación
            await asyncio.sleep(duration + 1)

            # Verificar que el archivo existe
            if not os.path.exists(recording_file):
                self.logger.error(f"Archivo de grabación no encontrado: {recording_file}")
                return None

            # Leer archivo de audio
            try:
                with open(recording_file, 'rb') as f:
                    audio_data = np.frombuffer(f.read(), dtype=np.int16)
                self.logger.info(f"Audio capturado: {len(audio_data)} samples")

                # Limpiar archivo temporal
                try:
                    os.unlink(recording_file)
                except:
                    pass  # No importa si falla la limpieza

                return audio_data

            except Exception as e:
                self.logger.error(f"Error leyendo archivo de audio: {e}")
                return None

        except Exception as e:
            self.logger.error(f"Error capturando audio RTP: {e}")
            return None

    async def cleanup_channel(self, channel_id):
        """Limpiar recursos para un canal específico."""
        if channel_id in self.active_recordings:
            try:
                self.active_recordings[channel_id].cancel()
                del self.active_recordings[channel_id]
                self.logger.info(f"Recursos RTP limpiados para canal {channel_id}")
            except Exception as e:
                self.logger.error(f"Error limpiando recursos RTP: {e}")