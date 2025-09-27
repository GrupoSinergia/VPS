import asyncio
import uvloop
import aiohttp
import numpy as np
import logging
import pwd
import os
import wave
import concurrent.futures
from enum import Enum
from aiohttp import web
from prometheus_client import Gauge, generate_latest
from aioari import connect
from utils import get_env, setup_log
from rtp_fixed import RTPProcessor
from vad import VadController
from stt import STTWorker
from tts import TTSWorker
from dtmf import DTMFHandler

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

class ConversationState(Enum):
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"

class VoIPAgent:
    def __init__(self):
        self.logger = setup_log("app")
        self.ari_url = get_env("ARI_URL", "http://127.0.0.1:8088")
        self.ari_user = get_env("ARI_USER", "ari")
        self.ari_pass = get_env("ARI_PASS", "secret")
        self.ari_app = get_env("ARI_APP", "agente-ia")
        self.rtp_in_host = get_env("RTP_IN_HOST", "127.0.0.1")
        self.rtp_in_port = int(get_env("RTP_IN_PORT", 5000))
        self.rtp_out_host = get_env("RTP_OUT_HOST", "127.0.0.1")
        self.rtp_out_port = int(get_env("RTP_OUT_PORT", 5002))
        self.prometheus_port = int(get_env("PROMETHEUS_PORT", 9091))
        self.n8n_webhook = get_env("N8N_WEBHOOK", "http://localhost:5679/webhook/voip-agent")
        self.stt = STTWorker()
        self.tts = TTSWorker()
        self.rtp = RTPProcessor()
        self.vad = VadController()
        self.ari = None
        self.dtmf = None
        self.stt_latency = Gauge("stt_latency_seconds", "Latencia de STT")
        self.tts_latency = Gauge("tts_latency_seconds", "Latencia de TTS")
        self.llm_latency = Gauge("llm_latency_seconds", "Latencia de LLM")
        self.audio_queue = asyncio.Queue()
        # Diccionario para rastrear canales activos y sus tareas
        self.active_channels = {}
        # ThreadPool para operaciones síncronas
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        # Events para playback
        self.playback_events = {}
        # Estados de conversación por canal
        self.conversation_states = {}
        # Eventos de interrupción
        self.interrupt_events = {}
        # Cache de TTS para respuestas comunes
        self.tts_cache = {}
        # Sesión HTTP reutilizable
        self.http_session = None
        # Buffer de audio por canal
        self.audio_buffers = {}
        # Tiempos de última actividad
        self.last_activity = {}

    async def metrics_handler(self, request):
        return web.Response(body=generate_latest(), content_type="text/plain")

    async def process_audio(self, audio_data):
        start_time = asyncio.get_event_loop().time()

        # STT asíncrono usando ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(
            self.executor, self.stt.process_audio, audio_data
        )

        self.stt_latency.set(asyncio.get_event_loop().time() - start_time)
        if not transcription:
            self.logger.error("No se obtuvo transcripción")
            return None
        text = " ".join(transcription) if isinstance(transcription, list) else transcription
        self.logger.info(f"Transcripción: {text}")

        # LLM request
        start_time = asyncio.get_event_loop().time()
        response = await self.send_to_n8n(text)
        self.llm_latency.set(asyncio.get_event_loop().time() - start_time)

        if not response:
            self.logger.error("No se obtuvo respuesta de n8n")
            return None
        self.logger.info(f"Respuesta LLM: {response}")
        return response

    async def send_to_n8n(self, transcription):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.n8n_webhook,
                    json={'text': transcription},
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('response', 'No se recibió respuesta de n8n')
                    else:
                        self.logger.error(f"Error en n8n: {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error enviando a n8n: {e}")
            return None

    async def on_channel(self, *args, **kwargs):
        try:
            if len(args) > 0:
                event = args[0]
                self.logger.info(f"Evento StasisStart recibido para canal: {event.get('channel', {}).get('name', 'unknown')}")
                channel_info = event['channel']
                channel_id = channel_info['id']
                channel_name = channel_info['name']
                caller_number = channel_info.get('caller', {}).get('number', 'unknown')
                self.logger.info(f"Procesando llamada de {caller_number} en canal {channel_name}")
                channel_obj = await self.ari.channels.get(channelId=channel_id)
                await channel_obj.answer()
                self.logger.info(f"Llamada respondida exitosamente")
                
                # Registrar canal como activo
                self.active_channels[channel_id] = {
                    'channel': channel_obj,
                    'processing_task': None
                }

                # Inicializar estado de conversación
                self.conversation_states[channel_id] = ConversationState.LISTENING

                await self.play_welcome_message(channel_obj)
                # Crear tarea de procesamiento de audio y guardar referencia
                processing_task = asyncio.create_task(self.start_audio_processing(channel_obj))
                self.active_channels[channel_id]['processing_task'] = processing_task
                
            else:
                self.logger.error("No se recibieron argumentos en on_channel")
        except Exception as e:
            self.logger.error(f"Error en on_channel: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    async def on_channel_end(self, *args, **kwargs):
        try:
            if len(args) > 0:
                event = args[0]
                channel_info = event.get('channel', {})
                channel_id = channel_info.get('id', 'unknown')
                channel_name = channel_info.get('name', 'unknown')
                self.logger.info(f"Evento StasisEnd recibido para canal: {channel_name} (ID: {channel_id})")
                
                # Limpiar canal activo y cancelar tareas
                if channel_id in self.active_channels:
                    channel_data = self.active_channels[channel_id]
                    
                    # Cancelar tarea de procesamiento de audio si existe
                    if channel_data['processing_task'] and not channel_data['processing_task'].done():
                        channel_data['processing_task'].cancel()
                        self.logger.info(f"Tarea de procesamiento cancelada para canal {channel_id}")
                    
                    # Remover del diccionario de canales activos
                    del self.active_channels[channel_id]
                    self.logger.info(f"Canal {channel_id} limpiado del estado activo")

                # Limpiar estado de conversación
                if channel_id in self.conversation_states:
                    del self.conversation_states[channel_id]
                if channel_id in self.interrupt_events:
                    del self.interrupt_events[channel_id]

                if channel_id not in self.active_channels:
                    self.logger.warning(f"Canal {channel_id} no encontrado en canales activos")
                    
            else:
                self.logger.error("No se recibieron argumentos en on_channel_end")
        except Exception as e:
            self.logger.error(f"Error en on_channel_end: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    async def play_welcome_message(self, channel):
        try:
            self.logger.info("Reproduciendo mensaje de bienvenida")
            welcome_text = "Hola, soy tu asistente virtual. Por favor, mantente en línea y háblame después del tono. Puedes interrumpirme en cualquier momento."
            try:
                start_time = asyncio.get_event_loop().time()
                # TTS asíncrono
                loop = asyncio.get_event_loop()
                rate, audio = await loop.run_in_executor(
                    self.executor, self.tts.synthesize, welcome_text
                )
                self.tts_latency.set(asyncio.get_event_loop().time() - start_time)
                self.logger.info("TTS completado exitosamente")
            except Exception as tts_error:
                self.logger.error(f"Error en TTS: {tts_error}")
                await self.play_simple_tone(channel)
                return

            # NO MUTAR entrada - permitir barge-in
            self.logger.info("Manteniendo audio entrante activo para barge-in")
            tts_filename = f"{channel.id.replace('.', '_')}"
            tts_file = f"/var/lib/asterisk/sounds/tts/{tts_filename}.slin"
            audio_int16 = (audio * 0.7).astype(np.int16)

            # Escritura asíncrona de archivo
            await self.write_audio_file(tts_file, audio_int16.tobytes())

            self.logger.info(f"Archivo TTS SLIN creado: {tts_file}")

            # Reproducir con soporte para barge-in
            await self.play_with_bargein(channel, f"sound:tts/{tts_filename}", tts_file)

        except Exception as e:
            self.logger.error(f"Error reproduciendo mensaje de bienvenida: {e}")

    async def play_simple_tone(self, channel):
        try:
            # NO mutar - permitir barge-in
            await self.play_with_event_wait(channel, "sound:beep")
            self.logger.info("Tono simple reproducido")
        except Exception as e:
            self.logger.error(f"Error reproduciendo tono simple: {e}")

    async def write_audio_file(self, filepath, audio_bytes):
        """Escribe archivo de audio de forma asíncrona"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._write_audio_sync, filepath, audio_bytes)
        except Exception as e:
            self.logger.error(f"Error escribiendo archivo de audio: {e}")
            raise

    def _write_audio_sync(self, filepath, audio_bytes):
        """Escritura síncrona de archivo (ejecuta en thread pool)"""
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)
        os.chmod(filepath, 0o644)
        try:
            asterisk_user = pwd.getpwnam('asterisk')
            os.chown(filepath, asterisk_user.pw_uid, asterisk_user.pw_gid)
        except KeyError:
            self.logger.warning("Usuario asterisk no encontrado")

    async def play_with_event_wait(self, channel, media, cleanup_file=None):
        """Reproduce audio y espera evento de finalización"""
        try:
            playback = await channel.play(media=media)
            playback_id = playback.id
            self.logger.info(f"Playback iniciado: {playback_id}")

            # Crear evento para este playback
            playback_event = asyncio.Event()
            self.playback_events[playback_id] = playback_event

            # Configurar listener para evento de finalización
            def on_playback_finished(playback_obj, event):
                if playback_event:
                    playback_event.set()
                    self.logger.info(f"Playback {playback_id} finalizado por evento")

            playback.on_event('PlaybackFinished', on_playback_finished)

            # Esperar finalización con timeout de seguridad
            try:
                await asyncio.wait_for(playback_event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout esperando playback {playback_id}")

            # Limpiar evento
            if playback_id in self.playback_events:
                del self.playback_events[playback_id]

            # Programar limpieza de archivo
            if cleanup_file:
                asyncio.create_task(self.cleanup_temp_file(cleanup_file, 300))

        except Exception as e:
            self.logger.error(f"Error en playback con eventos: {e}")
            raise

    async def play_with_bargein(self, channel, media, cleanup_file=None):
        """Reproduce audio con soporte para barge-in (interrupción por voz)"""
        try:
            channel_id = channel.id

            # Marcar como hablando
            self.conversation_states[channel_id] = ConversationState.SPEAKING

            # Crear evento de interrupción
            interrupt_event = asyncio.Event()
            self.interrupt_events[channel_id] = interrupt_event

            playback = await channel.play(media=media)
            playback_id = playback.id
            self.logger.info(f"Playback con barge-in iniciado: {playback_id}")

            # Crear evento para finalización normal
            playback_event = asyncio.Event()
            self.playback_events[playback_id] = playback_event

            def on_playback_finished(playback_obj, event):
                if playback_event:
                    playback_event.set()
                    self.logger.info(f"Playback {playback_id} finalizado normalmente")

            playback.on_event('PlaybackFinished', on_playback_finished)

            # Iniciar monitoreo de interrupción
            interrupt_task = asyncio.create_task(self.monitor_interruption(channel))

            # Esperar finalización normal o interrupción
            done, pending = await asyncio.wait(
                [asyncio.create_task(playback_event.wait()), asyncio.create_task(interrupt_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancelar tarea de monitoreo
            interrupt_task.cancel()

            # Verificar si hubo interrupción
            interrupted = interrupt_event.is_set()

            if interrupted:
                self.logger.info(f"Playback {playback_id} interrumpido por usuario")
                try:
                    await playback.stop()
                except:
                    pass  # El playback puede ya haber terminado
                # Cambiar estado a interrumpido
                self.conversation_states[channel_id] = ConversationState.INTERRUPTED
            else:
                self.logger.info(f"Playback {playback_id} completado sin interrupción")
                self.conversation_states[channel_id] = ConversationState.LISTENING

            # Limpiar eventos
            if playback_id in self.playback_events:
                del self.playback_events[playback_id]
            if channel_id in self.interrupt_events:
                del self.interrupt_events[channel_id]

            # Programar limpieza de archivo
            if cleanup_file:
                asyncio.create_task(self.cleanup_temp_file(cleanup_file, 300))

            return interrupted

        except Exception as e:
            self.logger.error(f"Error en playback con barge-in: {e}")
            # Limpiar estado en caso de error
            if channel_id in self.conversation_states:
                self.conversation_states[channel_id] = ConversationState.LISTENING
            raise

    async def monitor_interruption(self, channel):
        """Monitorea audio entrante durante TTS para detectar interrupciones"""
        try:
            channel_id = channel.id
            self.logger.info(f"Iniciando monitoreo de interrupción para canal {channel_id}")

            while (channel_id in self.conversation_states and
                   self.conversation_states[channel_id] == ConversationState.SPEAKING):

                try:
                    # Capturar chunks pequeños de audio (100ms)
                    audio_chunk = await asyncio.wait_for(
                        self.rtp.receive_audio(channel, duration=0.1),
                        timeout=0.2
                    )

                    if audio_chunk is not None:
                        # Verificar si hay voz usando VAD
                        loop = asyncio.get_event_loop()
                        is_speech = await loop.run_in_executor(
                            self.executor, self.vad.is_speech, audio_chunk
                        )

                        if is_speech:
                            self.logger.info(f"Voz detectada durante TTS en canal {channel_id} - Interrumpiendo")
                            if channel_id in self.interrupt_events:
                                self.interrupt_events[channel_id].set()
                            break

                    await asyncio.sleep(0.05)  # 50ms entre checks

                except asyncio.TimeoutError:
                    # No hay audio, continuar monitoreando
                    await asyncio.sleep(0.05)
                    continue
                except Exception as e:
                    self.logger.error(f"Error en monitoreo de interrupción: {e}")
                    break

        except asyncio.CancelledError:
            self.logger.info(f"Monitoreo de interrupción cancelado para canal {channel_id}")
        except Exception as e:
            self.logger.error(f"Error fatal en monitoreo de interrupción: {e}")

    async def get_cached_tts(self, text):
        """Obtiene TTS con cache para respuestas comunes"""
        # Crear hash del texto para cache
        import hashlib
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:12]

        if text_hash in self.tts_cache:
            self.logger.info(f"Cache HIT para TTS: {text[:30]}...")
            return self.tts_cache[text_hash]

        # TTS asíncrono
        loop = asyncio.get_event_loop()
        rate, audio = await loop.run_in_executor(
            self.executor, self.tts.synthesize, text
        )

        # Cachear solo respuestas cortas (<100 chars) para evitar uso excesivo de memoria
        if len(text) < 100 and len(self.tts_cache) < 50:  # Limitar cache a 50 entradas
            self.tts_cache[text_hash] = (rate, audio)
            self.logger.info(f"Cache MISS - Guardado: {text[:30]}...")

        return rate, audio

    async def init_common_tts_cache(self):
        """Pre-genera cache para respuestas comunes"""
        common_responses = [
            "Hola, soy tu asistente virtual. Por favor, mantente en línea y dime tu nombre después del tono. Bip.",
            "Te escucho, por favor continúa.",
            "Disculpa, no pude entender. ¿Puedes repetir?",
            "Lo siento, estoy teniendo problemas de conexión. ¿Puedes repetir?",
            "Disculpa, no pude procesar tu mensaje. ¿Puedes intentar de nuevo?",
            "Un momento por favor...",
            "Perfecto, entiendo.",
            "Muy bien, gracias."
        ]

        self.logger.info("Pre-generando cache de TTS para respuestas comunes...")
        for response in common_responses:
            try:
                await self.get_cached_tts(response)
            except Exception as e:
                self.logger.error(f"Error pre-generando TTS para '{response[:30]}': {e}")

        self.logger.info(f"Cache TTS inicializado con {len(self.tts_cache)} entradas")

    async def cleanup_temp_file(self, filepath, delay_seconds):
        try:
            await asyncio.sleep(delay_seconds)
            if os.path.exists(filepath):
                os.unlink(filepath)
                self.logger.info(f"Archivo temporal limpiado: {filepath}")
        except Exception as e:
            self.logger.error(f"Error limpiando archivo temporal: {e}")

    async def start_audio_processing(self, channel):
        try:
            self.logger.info(f"Iniciando procesamiento de audio para canal {channel.id}")
            bridge_id = f"bridge-{channel.id}"
            bridge = await self.ari.bridges.create(type='mixing', bridgeId=bridge_id)
            await bridge.addChannel(channel=channel.id)
            self.logger.info(f"Bridge {bridge_id} creado para hold")
            def on_dtmf(channel_obj, event):
                digit = event.get('digit', '?')
                self.logger.info(f"DTMF recibido: {digit}")
                asyncio.create_task(self.respond_to_dtmf(channel, digit))
            channel.on_event('ChannelDtmfReceived', on_dtmf)
            # Procesar audio entrante con VAD continuo
            await self.continuous_audio_processing(channel)

            # Limpiar bridge al finalizar
            try:
                await bridge.destroy()
                self.logger.info(f"Bridge {bridge_id} destruido")
            except Exception as e:
                self.logger.error(f"Error destruyendo bridge: {e}")

            await self.audio_queue.put(channel)
            self.logger.info("Procesamiento de audio finalizado")
        except Exception as e:
            self.logger.error(f"Error iniciando procesamiento de audio: {e}")

    async def continuous_audio_processing(self, channel):
        """Procesamiento continuo de audio con VAD y chunks pequeños para tiempo real"""
        channel_id = channel.id
        self.logger.info(f"Iniciando procesamiento continuo para canal {channel_id}")

        audio_buffer = []
        silence_duration = 0
        speech_detected = False

        while channel_id in self.active_channels:
            try:
                # Capturar chunks pequeños (100ms) para tiempo real
                audio_chunk = await asyncio.wait_for(
                    self.rtp.receive_audio(channel, duration=0.1),
                    timeout=0.2
                )

                if audio_chunk is None:
                    silence_duration += 0.1
                    # Si hay silencio prolongado y ya había voz, procesar buffer
                    if speech_detected and silence_duration > 1.0:  # 1 segundo de silencio
                        if audio_buffer:
                            await self.process_audio_buffer(channel, audio_buffer)
                            audio_buffer = []
                            speech_detected = False
                            silence_duration = 0
                    continue

                # VAD asíncrono en chunk para detectar voz
                loop = asyncio.get_event_loop()
                is_speech = await loop.run_in_executor(
                    self.executor, self.vad.is_speech, audio_chunk
                )

                if is_speech:
                    if not speech_detected:
                        self.logger.info("🎙️ Inicio de voz detectado - Iniciando captura")
                        speech_detected = True
                        audio_buffer = []

                    audio_buffer.append(audio_chunk)
                    silence_duration = 0

                    # Procesar si buffer es muy largo (evitar memoria excesiva)
                    if len(audio_buffer) > 50:  # 5 segundos max
                        await self.process_audio_buffer(channel, audio_buffer)
                        audio_buffer = []
                        speech_detected = False

                else:
                    if speech_detected:
                        silence_duration += 0.1
                        # Pequeña pausa en el habla, seguir acumulando
                        if silence_duration < 0.5:  # 500ms de tolerancia
                            audio_buffer.append(audio_chunk)
                        # Pausa más larga, procesar lo acumulado
                        elif silence_duration > 1.0:  # 1 segundo de silencio
                            if audio_buffer:
                                await self.process_audio_buffer(channel, audio_buffer)
                                audio_buffer = []
                                speech_detected = False
                                silence_duration = 0

            except asyncio.TimeoutError:
                # No hay audio, continuar monitoreando
                silence_duration += 0.2
                if speech_detected and silence_duration > 1.5:  # 1.5s timeout
                    if audio_buffer:
                        await self.process_audio_buffer(channel, audio_buffer)
                        audio_buffer = []
                        speech_detected = False
                        silence_duration = 0
                continue

            except asyncio.CancelledError:
                self.logger.info(f"Procesamiento continuo cancelado para canal {channel_id}")
                break

            except Exception as e:
                self.logger.error(f"Error en procesamiento continuo: {e}")
                await asyncio.sleep(0.1)  # Pequeña pausa antes de continuar

    async def process_audio_buffer(self, channel, audio_buffer):
        """Procesa buffer de audio acumulado"""
        try:
            if not audio_buffer:
                return

            # Concatenar chunks de audio
            import numpy as np
            full_audio = np.concatenate(audio_buffer)

            self.logger.info(f"Procesando buffer de audio ({len(audio_buffer)} chunks)")

            # Procesar con pipeline optimizado
            response = await self.process_audio(full_audio)

            if response:
                # TTS con cache
                start_time = asyncio.get_event_loop().time()
                rate, audio = await self.get_cached_tts(response)
                self.tts_latency.set(asyncio.get_event_loop().time() - start_time)

                tts_filename = f"{channel.id.replace('.', '_')}_response_{int(asyncio.get_event_loop().time())}"
                tts_file = f"/var/lib/asterisk/sounds/tts/{tts_filename}.slin"
                audio_int16 = (audio * 0.7).astype(np.int16)

                # Escritura asíncrona
                await self.write_audio_file(tts_file, audio_int16.tobytes())

                self.logger.info(f"Archivo TTS SLIN creado: {tts_file}")

                # Reproducir con soporte para barge-in
                interrupted = await self.play_with_bargein(channel, f"sound:tts/{tts_filename}", tts_file)

                if interrupted:
                    self.logger.info("TTS interrumpido, continuando captura")

        except Exception as e:
            self.logger.error(f"Error procesando buffer de audio: {e}")

    async def respond_to_dtmf(self, channel, digit):
        try:
            self.logger.info(f"DTMF recibido: {digit}")
            await self.play_with_event_wait(channel, f"sound:digits/{digit}")
            self.logger.info(f"DTMF {digit} respondido exitosamente")
        except Exception as e:
            self.logger.error(f"Error respondiendo a DTMF {digit}: {e}")
            try:
                await self.play_with_event_wait(channel, "sound:beep")
                self.logger.info("Tono beep reproducido como fallback")
            except Exception as beep_error:
                self.logger.error(f"Error con beep: {beep_error}")

    async def connect_ari(self):
        max_retries = 3
        retry_delay = 5
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Intentando conectar a ARI (intento {attempt + 1}/{max_retries})")
                self.ari = await connect(
                    base_url=self.ari_url,
                    username=self.ari_user,
                    password=self.ari_pass
                )
                asterisk_info = await self.ari.asterisk.getInfo()
                self.logger.info(f"Conectado a Asterisk: {asterisk_info['build']['date']}")
                self.ari.on_event('StasisStart', self.on_channel)
                self.ari.on_event("StasisEnd", self.on_channel_end)
                self.logger.info(f"Preparado para recibir eventos de: {self.ari_app}")
                self.logger.info("Iniciando procesamiento WebSocket...")
                self.dtmf = DTMFHandler(self.ari)
                self.logger.info("Conexión ARI exitosa")
                return True
            except Exception as e:
                self.logger.error(f"Error en intento {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Reintentando en {retry_delay} segundos...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error("No se pudo conectar a ARI después de todos los intentos")
                    return False

    async def run(self):
        self.logger.info("Iniciando VoIP Agent")
        app = web.Application()
        app.add_routes([web.get("/metrics", self.metrics_handler)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.prometheus_port)
        await site.start()
        self.logger.info(f"Servidor de métricas iniciado en puerto {self.prometheus_port}")
        # Inicializar cache de TTS
        await self.init_common_tts_cache()

        try:
            if not await self.connect_ari():
                raise Exception("No se pudo conectar a ARI")
        except Exception as e:
            self.logger.error(f"Error conectando a ARI: {e}")
            raise
        try:
            self.logger.info("Iniciando procesamiento de audio y WebSocket...")
            websocket_task = asyncio.create_task(self.ari.run(apps=[self.ari_app]))
            audio_task = asyncio.create_task(self.process_audio_loop())
            await asyncio.gather(websocket_task, audio_task)
        except KeyboardInterrupt:
            self.logger.info("Deteniendo VoIP Agent...")
        except Exception as e:
            self.logger.error(f"Error fatal: {e}")
            raise
        finally:
            if self.ari:
                try:
                    await self.ari.close()
                except:
                    pass
            # Cerrar sesión HTTP
            if self.http_session:
                try:
                    await self.http_session.close()
                except:
                    pass
            # Cerrar ThreadPool
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)

    async def process_audio_loop(self):
        while True:
            try:
                channel = await asyncio.wait_for(self.audio_queue.get(), timeout=1.0)
                self.logger.info(f"Canal activo en cola: {channel.id}")
                while True:
                    await asyncio.sleep(15)
                    try:
                        await channel.play(media="sound:silence/1")
                        self.logger.info(f"Keep-alive audio enviado para canal {channel.id}")
                    except Exception as e:
                        self.logger.error(f"Error en keep-alive para canal {channel.id}: {e}")
                        break
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error en process_audio_loop: {e}")

async def main():
    agent = VoIPAgent()
    try:
        await agent.run()
    except Exception as e:
        logging.getLogger("app").error(f"Error fatal: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nVoIP Agent detenido por el usuario")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
