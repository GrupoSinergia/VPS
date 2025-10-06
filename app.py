import asyncio
import uvloop
import aiohttp
import numpy as np
import logging
import pwd
import os
import wave
from aiohttp import web
from prometheus_client import Gauge, generate_latest
from aioari import connect
from utils import get_env, setup_log
from rtp_realtime import RealtimeRTPProcessor
from rtp_streaming import StreamingRTPProcessor
from vad import VadController
from stt import STTWorker
from tts import TTSWorker
from dtmf import DTMFHandler

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

class VoIPAgent:
    def __init__(self):
        self.logger = setup_log("app")
        self.ari_url = get_env("ARI_URL", "http://127.0.0.1:8088")
        self.ari_user = get_env("ARI_USER", "ari")
        self.ari_pass = get_env("ARI_PASS", "secret")
        self.ari_app = get_env("ARI_APP", "agente-ia")
        self.rtp_in_host = get_env("RTP_IN_HOST", "127.0.0.1")
        self.rtp_in_port = int(get_env("RTP_IN_PORT", 4000))
        self.rtp_out_host = get_env("RTP_OUT_HOST", "127.0.0.1")
        self.rtp_out_port = int(get_env("RTP_OUT_PORT", 4002))
        self.prometheus_port = int(get_env("PROMETHEUS_PORT", 9091))
        self.n8n_webhook = get_env("N8N_WEBHOOK", "http://0.0.0.0:5678/webhook/my-workflow")
        self.stt = STTWorker()
        self.tts = TTSWorker()
        self.vad = VadController()
        self.rtp = RealtimeRTPProcessor()
        self.rtp_streaming = StreamingRTPProcessor(self.vad)
        self.ari = None
        self.dtmf = None
        self.stt_latency = Gauge("stt_latency_seconds", "Latencia de STT")
        self.tts_latency = Gauge("tts_latency_seconds", "Latencia de TTS")
        self.llm_latency = Gauge("llm_latency_seconds", "Latencia de LLM")
        self.audio_queue = asyncio.Queue()
        # Diccionario para rastrear canales activos y sus tareas
        self.active_channels = {}

    async def metrics_handler(self, request):
        return web.Response(body=generate_latest(), content_type="text/plain")

    async def process_audio(self, audio_data):
        start_time = asyncio.get_event_loop().time()
        transcription = await self.stt.process_audio(audio_data)
        self.stt_latency.set(asyncio.get_event_loop().time() - start_time)
        if not transcription:
            self.logger.error("No se obtuvo transcripción")
            return None
        text = " ".join(transcription) if isinstance(transcription, list) else transcription
        self.logger.info(f"Transcripción: {text}")
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
                        # Intentar leer como texto plano primero
                        text_response = await response.text()
                        if text_response:
                            return text_response
                        # Si está vacío, intentar JSON
                        try:
                            data = await response.json()
                            return data.get('response', 'No se recibió respuesta de n8n')
                        except:
                            return 'No se recibió respuesta de n8n'
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
                else:
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
            welcome_text = "Hola, soy tu asistente virtual. Por favor, mantente en línea y dime tu nombre después del tono. Bip."
            try:
                start_time = asyncio.get_event_loop().time()
                rate, audio = self.tts.synthesize(welcome_text)
                self.tts_latency.set(asyncio.get_event_loop().time() - start_time)
                self.logger.info("TTS completado exitosamente")
            except Exception as tts_error:
                self.logger.error(f"Error en TTS: {tts_error}")
                await self.play_simple_tone(channel)
                return
            await channel.mute(direction='in')
            self.logger.info("Audio entrante mutado durante TTS")
            tts_filename = f"{channel.id.replace('.', '_')}"
            tts_file = f"/var/lib/asterisk/sounds/tts/{tts_filename}.slin"
            audio_int16 = (audio * 0.7).astype(np.int16)
            with open(tts_file, 'wb') as f:
                f.write(audio_int16.tobytes())
            os.chmod(tts_file, 0o644)
            try:
                asterisk_user = pwd.getpwnam('asterisk')
                os.chown(tts_file, asterisk_user.pw_uid, asterisk_user.pw_gid)
            except KeyError:
                self.logger.warning("Usuario asterisk no encontrado")
            self.logger.info(f"Archivo TTS SLIN creado: {tts_file}")
            playback = await channel.play(media=f"sound:tts/{tts_filename}")
            self.logger.info(f"TTS iniciado para playback {playback.id}")
            await asyncio.sleep(15)
            self.logger.info(f"Playback TTS completado para {channel.id} (sleep estimado)")
            await channel.unmute(direction='in')
            self.logger.info("Audio desmutado")
            asyncio.create_task(self.cleanup_temp_file(tts_file, 300))
        except Exception as e:
            self.logger.error(f"Error reproduciendo mensaje de bienvenida: {e}")
            await channel.unmute(direction='in')

    async def play_simple_tone(self, channel):
        try:
            await channel.mute(direction='in')
            playback = await channel.play(media="sound:beep")
            self.logger.info("Tono simple reproducido")
            await asyncio.sleep(2)
            self.logger.info(f"Playback tono completado para {channel.id} (sleep estimado)")
            await channel.unmute(direction='in')
        except Exception as e:
            self.logger.error(f"Error reproduciendo tono simple: {e}")
            await channel.unmute(direction='in')

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
            # Procesar audio entrante en bucle con captura batch optimizada
            while channel.id in self.active_channels:  # Solo continuar si el canal está activo
                try:
                    self.logger.info("🎙️ Iniciando captura de audio (batch optimizado 2s)")
                    # CRÍTICO: Pasar el BRIDGE no el channel, porque el canal está dentro del bridge
                    # Asterisk ARI no permite grabar un canal que está en un bridge
                    audio_data = await self.rtp.capture_audio_realtime(bridge=bridge, duration=2)

                    if audio_data is not None and len(audio_data) > 0:
                        self.logger.info(f"✅ Audio recibido: {len(audio_data)} samples")

                        # Validar con VAD antes de procesar
                        audio_float = audio_data.astype(np.float32) / 32768.0
                        if self.vad.process(audio_float):
                            self.logger.info("🎙️ VOZ DETECTADA - Procesando con STT")
                            response = await self.process_audio(audio_data)
                        else:
                            self.logger.warning("⚠️ No se detectó voz en el audio capturado")
                            response = None
                        if response:
                            start_time = asyncio.get_event_loop().time()
                            rate, audio = self.tts.synthesize(response)
                            self.tts_latency.set(asyncio.get_event_loop().time() - start_time)
                            tts_filename = f"{channel.id.replace('.', '_')}_response"
                            tts_file = f"/var/lib/asterisk/sounds/tts/{tts_filename}.slin"
                            audio_int16 = (audio * 0.7).astype(np.int16)
                            with open(tts_file, 'wb') as f:
                                f.write(audio_int16.tobytes())
                            os.chmod(tts_file, 0o644)
                            try:
                                asterisk_user = pwd.getpwnam('asterisk')
                                os.chown(tts_file, asterisk_user.pw_uid, asterisk_user.pw_gid)
                            except KeyError:
                                self.logger.warning("Usuario asterisk no encontrado")
                            self.logger.info(f"Archivo TTS SLIN creado: {tts_file}")
                            await channel.mute(direction='in')
                            playback = await channel.play(media=f"sound:tts/{tts_filename}")
                            self.logger.info(f"TTS respuesta iniciado para playback {playback.id}")
                            await asyncio.sleep(15)
                            await channel.unmute(direction='in')
                            asyncio.create_task(self.cleanup_temp_file(tts_file, 300))
                    else:
                        self.logger.warning("⚠️ No se capturó audio válido o no contiene voz")

                except asyncio.CancelledError:
                    self.logger.info(f"Procesamiento de audio cancelado para canal {channel.id}")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Error procesando audio entrante: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    # No romper el loop, continuar intentando
                    await asyncio.sleep(1)
            
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

    async def respond_to_dtmf(self, channel, digit):
        try:
            self.logger.info(f"Respondiendo a DTMF: {digit}")
            await channel.mute(direction='in')
            playback = await channel.play(media=f"sound:digits/{digit}")
            self.logger.info(f"Playback DTMF {digit} iniciado para {channel.id}")
            await asyncio.sleep(2)
            self.logger.info(f"Playback DTMF {digit} completado para {channel.id} (sleep estimado)")
            await channel.unmute(direction='in')
            self.logger.info(f"DTMF {digit} respondido exitosamente")
        except Exception as e:
            self.logger.error(f"Error respondiendo a DTMF {digit}: {e}")
            try:
                await channel.mute(direction='in')
                playback = await channel.play(media="sound:beep")
                self.logger.info(f"Playback beep iniciado para {channel.id}")
                await asyncio.sleep(2)
                self.logger.info(f"Playback beep completado para {channel.id} (sleep estimado)")
                await channel.unmute(direction='in')
                self.logger.info("Tono beep reproducido como fallback")
            except Exception as beep_error:
                self.logger.error(f"Error con beep: {beep_error}")
            finally:
                await channel.unmute(direction='in')

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
