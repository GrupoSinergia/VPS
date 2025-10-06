import asyncio
import numpy as np
import logging
import os
from typing import Optional
from utils import setup_log

class RealtimeRTPProcessor:
    """
    PROCESADOR DE AUDIO EN TIEMPO REAL ULTRA-OPTIMIZADO
    Usa channel.record() con lectura progresiva para captura en tiempo real
    """

    def __init__(self):
        self.logger = setup_log("rtp_realtime")
        self.sample_rate = 8000  # Asterisk telephony standard
        self.channels = 1
        self.frame_duration_ms = 20
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        self.bytes_per_sample = 2  # 16-bit audio
        self.logger.info(f"✅ RealtimeRTPProcessor inicializado: {self.sample_rate}Hz, {self.frame_duration_ms}ms frames")

    async def capture_audio_realtime(self, channel=None, bridge=None, duration=5.0):
        """
        Captura audio en tiempo real usando bridge.record() o channel.record()

        IMPORTANTE: Si el canal está en un bridge, DEBE pasarse el bridge, no el channel.
        Asterisk ARI no permite grabar un canal que está dentro de un bridge.

        Args:
            channel: Canal ARI de Asterisk (solo si NO está en bridge)
            bridge: Bridge ARI de Asterisk (si el canal está en bridge)
            duration: Duración de captura en segundos

        Returns:
            numpy array con audio capturado o None si falla
        """
        try:
            # Validar que se pasó channel o bridge
            if channel is None and bridge is None:
                self.logger.error("❌ Debe proporcionar channel o bridge")
                return None

            # Determinar qué objeto usar y su ID
            if bridge is not None:
                record_obj = bridge
                obj_id = bridge.id
                obj_type = "bridge"
                self.logger.info(f"🎙️ Iniciando captura de audio EN TIEMPO REAL para BRIDGE {obj_id}")
            else:
                record_obj = channel
                obj_id = channel.id
                obj_type = "channel"
                self.logger.info(f"🎙️ Iniciando captura de audio EN TIEMPO REAL para CANAL {obj_id}")

            # Configurar archivo de grabación
            recording_name = f"realtime_{obj_id.replace('.', '_').replace('-', '_')}"
            recording_file = f"/var/spool/asterisk/recording/{recording_name}.slin"

            # Crear directorio si no existe
            os.makedirs(os.path.dirname(recording_file), exist_ok=True)

            try:
                # Iniciar grabación usando bridge.record() o channel.record()
                # CRÍTICO: El parámetro 'name' NO debe incluir subdirectorio
                # Asterisk ARI ya escribe en /var/spool/asterisk/recording/
                # Solo se pasa el nombre del archivo sin path
                recording = await record_obj.record(
                    name=recording_name,  # SIN prefijo "recording/"
                    format="slin",
                    maxDurationSeconds=int(duration) + 1,
                    ifExists="overwrite",
                    terminateOn="none"
                )

                self.logger.info(f"📝 Grabación iniciada para {obj_type}: {recording_file}")

            except Exception as e:
                self.logger.error(f"❌ Error iniciando grabación en {obj_type}: {e}")
                return None

            # Esperar la duración especificada para que se grabe audio
            await asyncio.sleep(duration)

            # Detener grabación
            try:
                await recording.stop()
                self.logger.info("⏹️ Grabación detenida")
            except Exception as e:
                self.logger.warning(f"⚠️ Error deteniendo grabación: {e}")

            # Pequeña pausa para asegurar que el archivo esté completo
            await asyncio.sleep(0.3)

            # Verificar si el archivo existe
            if not os.path.exists(recording_file):
                self.logger.error(f"❌ Archivo de grabación no existe: {recording_file}")
                return None

            # Verificar tamaño del archivo
            file_size = os.path.getsize(recording_file)
            if file_size == 0:
                self.logger.error(f"❌ Archivo de grabación VACÍO: {recording_file}")
                try:
                    os.unlink(recording_file)
                except:
                    pass
                return None

            # Leer audio capturado
            with open(recording_file, 'rb') as f:
                audio_bytes = f.read()

            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

            self.logger.info(f"✅ Audio capturado: {len(audio_data)} samples ({file_size} bytes) = {len(audio_data)/self.sample_rate:.2f}s")

            # Limpiar archivo temporal
            try:
                os.unlink(recording_file)
                self.logger.debug(f"🧹 Archivo temporal eliminado: {recording_file}")
            except Exception as e:
                self.logger.warning(f"⚠️ Error limpiando archivo: {e}")

            # Validar audio
            if not self.validate_audio(audio_data):
                self.logger.warning("⚠️ Audio capturado no pasa validación de calidad")
                return None

            return audio_data

        except Exception as e:
            self.logger.error(f"❌ Error crítico en captura de audio: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def validate_audio(self, audio_data):
        """
        Validación ULTRA precisa de audio
        """
        if audio_data is None or len(audio_data) == 0:
            self.logger.debug("❌ Audio vacío")
            return False

        # Mínimo de samples para considerar válido
        min_samples = int(self.sample_rate * 0.5)  # Al menos 0.5 segundos
        if len(audio_data) < min_samples:
            self.logger.debug(f"❌ Audio muy corto: {len(audio_data)} samples < {min_samples}")
            return False

        # Convertir a absolutos
        audio_abs = np.abs(audio_data)

        # Métricas de calidad
        max_amplitude = np.max(audio_abs)
        rms = np.sqrt(np.mean(audio_abs.astype(np.float64) ** 2))
        mean_amplitude = np.mean(audio_abs)

        # Umbrales OPTIMIZADOS para telefonía VoIP real (codecs G.711, Opus)
        MIN_MAX_AMPLITUDE = 250   # Ajustado para voz comprimida VoIP (era 500)
        MIN_RMS = 80              # RMS mínimo para voz inteligible
        MIN_MEAN = 25             # Media ajustada para telefonía

        self.logger.debug(f"📊 Audio stats: max={max_amplitude}, rms={rms:.2f}, mean={mean_amplitude:.2f}")

        if max_amplitude < MIN_MAX_AMPLITUDE:
            self.logger.debug(f"❌ Amplitud máxima muy baja: {max_amplitude} < {MIN_MAX_AMPLITUDE}")
            return False

        if rms < MIN_RMS:
            self.logger.debug(f"❌ RMS muy bajo: {rms:.2f} < {MIN_RMS}")
            return False

        if mean_amplitude < MIN_MEAN:
            self.logger.debug(f"❌ Amplitud media muy baja: {mean_amplitude:.2f} < {MIN_MEAN}")
            return False

        self.logger.info(f"✅ Audio VÁLIDO - max:{max_amplitude} rms:{rms:.2f} mean:{mean_amplitude:.2f}")
        return True

    def cleanup(self):
        """Limpiar recursos"""
        try:
            recording_dir = "/var/spool/asterisk/recording"
            if os.path.exists(recording_dir):
                for filename in os.listdir(recording_dir):
                    if filename.startswith("realtime_"):
                        filepath = os.path.join(recording_dir, filename)
                        try:
                            os.unlink(filepath)
                            self.logger.debug(f"🧹 Limpiado: {filename}")
                        except Exception as e:
                            self.logger.warning(f"⚠️ Error limpiando {filename}: {e}")

            self.logger.info("✅ Limpieza completada")
        except Exception as e:
            self.logger.error(f"❌ Error en limpieza: {e}")
