import asyncio
import numpy as np
import os
from typing import Optional
from utils import setup_log

class StreamingRTPProcessor:
    """
    PROCESADOR DE AUDIO STREAMING CON VAD AUTOMÁTICO
    Captura audio continuamente y detecta fin de frase con pausas
    """

    def __init__(self, vad_controller):
        self.logger = setup_log("rtp_streaming")
        self.sample_rate = 8000  # Asterisk telephony standard
        self.channels = 1
        self.frame_duration_ms = 20
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        self.bytes_per_sample = 2  # 16-bit audio
        self.vad = vad_controller

        # Parámetros de detección de fin de frase
        self.min_speech_duration_ms = 300  # Mínimo 300ms de habla
        self.max_silence_duration_ms = 400  # Pausa de 400ms = fin de frase

        self.logger.info(f"✅ StreamingRTPProcessor inicializado: {self.sample_rate}Hz, pausa={self.max_silence_duration_ms}ms")

    async def capture_audio_streaming(self, channel=None, bridge=None, max_duration=10.0):
        """
        Captura audio en streaming hasta detectar pausa (fin de frase)

        Args:
            channel: Canal ARI de Asterisk (solo si NO está en bridge)
            bridge: Bridge ARI de Asterisk (si el canal está en bridge)
            max_duration: Duración máxima de captura en segundos (timeout)

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
                self.logger.info(f"🎙️ Iniciando captura STREAMING para BRIDGE {obj_id}")
            else:
                record_obj = channel
                obj_id = channel.id
                obj_type = "channel"
                self.logger.info(f"🎙️ Iniciando captura STREAMING para CANAL {obj_id}")

            # Configurar archivo de grabación
            recording_name = f"streaming_{obj_id.replace('.', '_').replace('-', '_')}"
            recording_file = f"/var/spool/asterisk/recording/{recording_name}.slin"

            # Crear directorio si no existe
            os.makedirs(os.path.dirname(recording_file), exist_ok=True)

            try:
                # Iniciar grabación con duración máxima
                recording = await record_obj.record(
                    name=recording_name,
                    format="slin",
                    maxDurationSeconds=int(max_duration) + 1,
                    ifExists="overwrite",
                    terminateOn="none"
                )

                self.logger.info(f"📝 Grabación streaming iniciada: {recording_file}")

            except Exception as e:
                self.logger.error(f"❌ Error iniciando grabación en {obj_type}: {e}")
                return None

            # Variables para detección de fin de frase
            audio_buffer = []
            silence_duration_ms = 0
            speech_detected = False
            total_duration_ms = 0
            chunk_size_ms = 500  # Analizar en chunks de 500ms

            # Loop de captura streaming
            start_time = asyncio.get_event_loop().time()

            while total_duration_ms < (max_duration * 1000):
                # Esperar chunk de audio
                await asyncio.sleep(chunk_size_ms / 1000.0)
                total_duration_ms += chunk_size_ms

                # Verificar si el archivo existe y tiene contenido
                if not os.path.exists(recording_file):
                    continue

                file_size = os.path.getsize(recording_file)
                if file_size == 0:
                    continue

                # Leer chunk de audio actual
                try:
                    with open(recording_file, 'rb') as f:
                        audio_bytes = f.read()

                    if len(audio_bytes) == 0:
                        continue

                    # Convertir a numpy array
                    chunk_data = np.frombuffer(audio_bytes, dtype=np.int16)

                    # Si es el mismo tamaño que antes, no hay audio nuevo
                    if len(chunk_data) <= len(audio_buffer):
                        # Incrementar contador de silencio
                        silence_duration_ms += chunk_size_ms
                    else:
                        # Hay audio nuevo - extraer solo la parte nueva
                        new_audio = chunk_data[len(audio_buffer):]
                        audio_buffer = chunk_data.copy()

                        # Convertir a float32 para VAD
                        new_audio_float = new_audio.astype(np.float32) / 32768.0

                        # Detectar voz en el nuevo audio
                        has_speech = self.vad.process(new_audio_float)

                        if has_speech:
                            speech_detected = True
                            silence_duration_ms = 0  # Reset contador de silencio
                            self.logger.debug(f"🎙️ Voz detectada - buffer: {len(audio_buffer)} samples")
                        else:
                            silence_duration_ms += chunk_size_ms

                except Exception as e:
                    self.logger.warning(f"⚠️ Error leyendo chunk: {e}")
                    continue

                # Verificar fin de frase: hubo voz Y ahora hay pausa larga
                if speech_detected and silence_duration_ms >= self.max_silence_duration_ms:
                    duration_sec = len(audio_buffer) / self.sample_rate

                    # Validar duración mínima de habla
                    if duration_sec >= (self.min_speech_duration_ms / 1000.0):
                        self.logger.info(f"✅ FIN DE FRASE detectado: {duration_sec:.2f}s de audio, pausa={silence_duration_ms}ms")
                        break
                    else:
                        self.logger.debug(f"⚠️ Audio muy corto: {duration_sec:.2f}s < {self.min_speech_duration_ms/1000.0}s")
                        speech_detected = False
                        silence_duration_ms = 0

            # Detener grabación
            try:
                await recording.stop()
                self.logger.info("⏹️ Grabación streaming detenida")
            except Exception as e:
                self.logger.warning(f"⚠️ Error deteniendo grabación: {e}")

            # Pausa para asegurar que el archivo esté completo
            await asyncio.sleep(0.2)

            # Verificar resultado final
            if len(audio_buffer) == 0:
                self.logger.error(f"❌ No se capturó audio")
                try:
                    os.unlink(recording_file)
                except:
                    pass
                return None

            final_duration = len(audio_buffer) / self.sample_rate
            self.logger.info(f"✅ Audio capturado: {len(audio_buffer)} samples ({final_duration:.2f}s)")

            # Limpiar archivo temporal
            try:
                os.unlink(recording_file)
                self.logger.debug(f"🧹 Archivo temporal eliminado: {recording_file}")
            except Exception as e:
                self.logger.warning(f"⚠️ Error limpiando archivo: {e}")

            return audio_buffer

        except Exception as e:
            self.logger.error(f"❌ Error crítico en captura streaming: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def cleanup(self):
        """Limpiar recursos"""
        try:
            recording_dir = "/var/spool/asterisk/recording"
            if os.path.exists(recording_dir):
                for filename in os.listdir(recording_dir):
                    if filename.startswith("streaming_"):
                        filepath = os.path.join(recording_dir, filename)
                        try:
                            os.unlink(filepath)
                            self.logger.debug(f"🧹 Limpiado: {filename}")
                        except Exception as e:
                            self.logger.warning(f"⚠️ Error limpiando {filename}: {e}")

            self.logger.info("✅ Limpieza completada")
        except Exception as e:
            self.logger.error(f"❌ Error en limpieza: {e}")
