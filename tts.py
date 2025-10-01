import os
import numpy as np
from piper import PiperVoice
from utils import get_env, setup_log

class TTSWorker:
    def __init__(self):
        self.logger = setup_log(__name__)
        self.voice = '/root/.cache/piper/es_MX-claude-high.onnx'
        self.rate = float(get_env('PIPER_RATE', '1.0'))
        try:
            self.model = PiperVoice.load(self.voice)
            self.logger.info(f"Loaded Piper voice: {self.voice}")
        except Exception as e:
            self.logger.error(f"Failed to load Piper voice {self.voice}: {e}")
            raise

    def synthesize(self, text):
        """Synthesize text to audio using Piper TTS optimizado para Asterisk 8kHz."""
        try:
            self.logger.info(f"Iniciando síntesis TTS para: {text[:50]}...")

            # Piper devuelve un generador de AudioChunk objects
            audio_generator = self.model.synthesize(text)

            # Recolectar chunks válidos y extraer audio
            audio_chunks = []
            total_samples = 0

            for i, chunk in enumerate(audio_generator):
                self.logger.info(f"Procesando chunk {i}: {type(chunk)}")

                try:
                    # Extraer audio con ganancia optimizada para telefonía
                    if hasattr(chunk, 'audio_int16_array'):
                        audio_data = chunk.audio_int16_array
                        # Ganancia optimizada: 80% para evitar saturación manteniendo claridad
                        audio_data = (audio_data * 0.8).astype(np.int16)
                        self.logger.info(f"ÉXITO: Extraído {len(audio_data)} samples con ganancia optimizada")
                    elif hasattr(chunk, 'audio_float_array'):
                        # Alternativa: usar audio_float_array y convertir
                        float_audio = chunk.audio_float_array
                        float_audio = np.clip(float_audio, -1.0, 1.0)
                        audio_data = (float_audio * 32767 * 0.8).astype(np.int16)
                        self.logger.info(f"ÉXITO: Convertido {len(audio_data)} samples de audio_float_array optimizado")
                    else:
                        self.logger.error(f"Chunk {i} no tiene audio_int16_array ni audio_float_array")
                        continue

                    # Verificar calidad del audio
                    if isinstance(audio_data, np.ndarray) and audio_data.size > 0:
                        min_val, max_val = audio_data.min(), audio_data.max()
                        
                        # Detectar posible saturación
                        if min_val < -32000 or max_val > 32000:
                            self.logger.warning(f"Chunk {i} cerca de saturación: min={min_val}, max={max_val}")
                        
                        audio_chunks.append(audio_data)
                        total_samples += len(audio_data)
                        self.logger.info(f"Chunk {i} agregado: {len(audio_data)} samples (rango: {audio_data.min()} a {audio_data.max()})")
                    else:
                        self.logger.error(f"Chunk {i} audio inválido: {type(audio_data)}")

                except Exception as chunk_error:
                    self.logger.error(f"Error extrayendo chunk {i}: {chunk_error}")

            self.logger.info(f"=== RESUMEN EXTRACCIÓN ===")
            self.logger.info(f"Chunks procesados: {len(audio_chunks)}")
            self.logger.info(f"Total samples: {total_samples}")

            if not audio_chunks:
                self.logger.error("No se extrajo audio válido")
                return self._generate_fallback_tone()

            # Concatenar chunks con verificación de tipos
            if len(audio_chunks) == 1:
                audio = audio_chunks[0]
            else:
                try:
                    # Asegurar que todos los chunks tengan el mismo dtype
                    audio_chunks = [chunk.astype(np.int16) for chunk in audio_chunks]
                    audio = np.concatenate(audio_chunks)
                    self.logger.info(f"Audio concatenado: {len(audio)} samples")
                except ValueError as concat_error:
                    self.logger.error(f"Error concatenando: {concat_error}")
                    audio = audio_chunks[0]

            # Verificar resultado final
            self.logger.info(f"Audio final a 22kHz: {len(audio)} samples, dtype: {audio.dtype}")

            if len(audio) == 0:
                return self._generate_fallback_tone()

            # Procesamiento final del audio
            if audio.dtype == np.int16:
                audio_final = audio
            else:
                # Convertir a int16 si es necesario
                if audio.dtype in [np.float32, np.float64]:
                    audio = np.clip(audio, -1.0, 1.0)
                    audio_final = (audio * 32767 * 0.8).astype(np.int16)
                else:
                    audio_final = audio.astype(np.int16)

            # CORRECCIÓN CRÍTICA: Resamplear de 22kHz a 8kHz para Asterisk
            try:
                import scipy.signal
                # Calcular nueva longitud para 8kHz
                resample_ratio = 8000 / 22050
                new_length = int(len(audio_final) * resample_ratio)
                
                # Resamplear usando scipy con filtro anti-aliasing
                audio_8k = scipy.signal.resample(audio_final, new_length)
                audio_8k_int16 = audio_8k.astype(np.int16)
                
                self.logger.info(f"Audio resampleado: {len(audio_final)} samples (22kHz) -> {len(audio_8k_int16)} samples (8kHz)")
                
                # Aplicar fade-in y fade-out suaves para evitar clicks
                fade_samples = min(80, len(audio_8k_int16) // 10)  # 10ms fade a 8kHz
                if len(audio_8k_int16) > fade_samples * 2:
                    # Fade-in
                    fade_in = np.linspace(0, 1, fade_samples)
                    audio_8k_int16[:fade_samples] = (audio_8k_int16[:fade_samples] * fade_in).astype(np.int16)
                    
                    # Fade-out
                    fade_out = np.linspace(1, 0, fade_samples)
                    audio_8k_int16[-fade_samples:] = (audio_8k_int16[-fade_samples:] * fade_out).astype(np.int16)

                # Estadísticas finales para monitoreo
                audio_stats = {
                    'samples_22k': len(audio_final),
                    'samples_8k': len(audio_8k_int16),
                    'min': int(audio_8k_int16.min()),
                    'max': int(audio_8k_int16.max()),
                    'saturated': int(np.sum(np.abs(audio_8k_int16) >= 32700))
                }
                
                self.logger.info(f"Audio stats final (8kHz): {audio_stats}")
                
                if audio_stats['saturated'] == 0:
                    self.logger.info("✅ Audio 8kHz optimizado sin saturación")
                else:
                    self.logger.warning(f"⚠️ Audio 8kHz con {audio_stats['saturated']} samples saturados")

                # Retornar audio a 8kHz para compatibilidad con Asterisk
                self.logger.info(f"✅ TTS completado: {len(audio_8k_int16)} samples a 8000Hz para Asterisk")
                return 8000, audio_8k_int16
                
            except ImportError:
                self.logger.error("scipy no disponible para resample, usando audio original")
                return 22050, audio_final
            except Exception as resample_error:
                self.logger.error(f"Error en resample: {resample_error}, usando audio original")
                return 22050, audio_final

        except Exception as e:
            self.logger.error(f"TTS synthesis failed: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return self._generate_fallback_tone()

    def _generate_fallback_tone(self):
        """Generar un tono simple como fallback cuando TTS falla."""
        try:
            # Crear un tono simple de 1 segundo a 8kHz para Asterisk
            duration = 1.0
            sample_rate = 8000
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # Crear un tono agradable con múltiples frecuencias
            frequency1 = 440  # La nota A
            frequency2 = 523  # Do
            audio_fallback = (np.sin(2 * np.pi * frequency1 * t) * 0.15 + 
                            np.sin(2 * np.pi * frequency2 * t) * 0.10)
            
            # Aplicar fade-in y fade-out suave
            fade_samples = int(sample_rate * 0.05)  # 50ms fade
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)
            
            audio_fallback[:fade_samples] *= fade_in
            audio_fallback[-fade_samples:] *= fade_out
            
            audio_fallback_int16 = (audio_fallback * 32767).astype(np.int16)

            self.logger.info("Generado audio fallback: tono armónico a 8kHz para Asterisk")
            return sample_rate, audio_fallback_int16

        except Exception as fallback_error:
            self.logger.error(f"Error generando fallback: {fallback_error}")
            return 8000, np.array([], dtype=np.int16)
