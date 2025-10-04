# 📋 FASE 1 - SISTEMA VOIP IA FUNCIONAL - RESUMEN COMPLETO

**Fecha:** 1 de Octubre 2025
**Estado:** ✅ COMPLETADO - Sistema funcional end-to-end
**Objetivo:** Crear el MEJOR agente de IA VoIP de LATAM

---

## 🎯 OBJETIVO DEL PROYECTO

Construir un agente de IA conversacional por teléfono que:
- Reciba llamadas VoIP
- Entienda voz en español
- Responda de forma inteligente usando IA
- Converse de manera natural y fluida

**META:** Ser el mejor agente de IA de llamadas en tiempo real de todo LATAM.

---

## ✅ ESTADO ACTUAL - QUÉ FUNCIONA

### Sistema End-to-End Funcional:
1. ✅ **Audio Capture** - Captura audio del usuario desde bridge
2. ✅ **VAD** - Detecta cuándo el usuario habla (Silero)
3. ✅ **STT** - Transcribe voz a texto (Whisper)
4. ✅ **IA Processing** - Procesa con LLM (n8n + Ollama)
5. ✅ **TTS** - Convierte respuesta a voz (Piper)
6. ✅ **Playback** - Reproduce respuesta al usuario

**El agente RESPONDE correctamente** ✅

---

## 🐌 PROBLEMAS IDENTIFICADOS

### 🔴 CRÍTICO - Latencia Inaceptable:
- **Tiempo actual:** 50-60 segundos de respuesta
- **Tiempo objetivo:** < 5 segundos
- **Cuello de botella:** n8n + Ollama procesamiento

### ⚠️ Otros Problemas:
- No permite interrupciones del usuario
- Conversación no fluida
- Audio se rechaza durante respuesta del agente

---

## 🏗️ ARQUITECTURA COMPLETA

### Stack Tecnológico:

```
┌─────────────────────────────────────────────────────┐
│                    LLAMADA TELEFÓNICA               │
│                   (Trunk Zadarma)                   │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │   ASTERISK PBX  │
         │   (ARI WebSocket)│
         └────────┬────────┘
                  │
                  ▼
    ┌────────────────────────────┐
    │    VOIP AGENT (Python)     │
    │  /root/la-voip-agent/      │
    │                            │
    │  app.py (main)             │
    │  ├─ rtp_realtime.py        │ ◄── Captura audio desde BRIDGE
    │  ├─ vad.py                 │ ◄── Detecta voz (Silero VAD)
    │  ├─ stt.py                 │ ◄── Whisper distil-large-v3
    │  ├─ tts.py                 │ ◄── Piper es_MX-claude-high
    │  ├─ config.py              │
    │  └─ metrics.py             │ ◄── Prometheus (puerto 9091)
    └──────────┬─────────────────┘
               │
               │ HTTP POST
               ▼
    ┌──────────────────────────┐
    │    N8N WORKFLOW          │
    │  "Grupo Sinergia"        │
    │                          │
    │  Webhook → AI Agent      │
    │    → Respond Webhook     │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │   OLLAMA (Docker)        │
    │  llama3.2:3b-instruct    │
    │  -q4_k_m                 │
    └──────────────────────────┘
```

### Puertos y URLs:
- **Asterisk ARI:** http://127.0.0.1:8088/ari
- **n8n:** http://0.0.0.0:5678
- **n8n Webhook:** http://0.0.0.0:5678/webhook/my-workflow
- **Prometheus Metrics:** http://127.0.0.1:9091/metrics
- **Ollama:** Docker container (red externa)

---

## 📁 ARCHIVOS CLAVE DEL PROYECTO

### Directorio Principal: `/root/la-voip-agent/`

#### Archivos Python Principales:

1. **app.py** - Orquestador principal
   - Maneja WebSocket ARI de Asterisk
   - Coordina todo el flujo de llamada
   - Integra todos los módulos

2. **rtp_realtime.py** - Captura de audio
   - **CRÍTICO:** Usa `bridge.record()` NO `channel.record()`
   - Captura audio del usuario desde el bridge
   - Parámetro `name` SIN prefijo "recording/"
   - Archivos: `/var/spool/asterisk/recording/realtime_bridge_*.slin`

3. **vad.py** - Voice Activity Detection
   - Usa Silero VAD
   - Sensitivity: 0.5 (0.3 - 0.5 recomendado)
   - Detecta segmentos de voz vs silencio

4. **stt.py** - Speech to Text
   - Faster Whisper
   - Modelo: distil-large-v3
   - Optimizado para español

5. **tts.py** - Text to Speech
   - Piper TTS
   - Voz: es_MX-claude-high
   - Output: 8kHz SLIN para Asterisk

6. **config.py** - Configuración
   - Variables de entorno
   - URLs y puertos

7. **metrics.py** - Métricas Prometheus
   - STT latency
   - TTS latency
   - Calls total

#### Archivos de Configuración:

- **.env** - Variables de entorno
- **run.sh** - Script de inicio del servicio
- **systemd.service** - Service unit file
- **.gitignore** - Archivos ignorados por git

#### Archivos de Respaldo:
- Múltiples `.backup` files con estados anteriores

---

## 💾 BACKUPS Y UBICACIONES

### Backups Principales:

```bash
/root/backups/
├── la-voip-agent_backup_20251001_030644.tar.gz  # 956KB - Código completo
│
└── n8n/
    ├── n8n_database_20251001_030611.sqlite      # 500KB - Base de datos n8n
    └── workflows_20251001_030512.json           # Workflows (vacío - requiere API key)
```

### Git Repository:
```bash
/root/la-voip-agent/.git/
Commit: 758f15b
Mensaje: "🎉 FASE 1: Sistema VoIP IA funcional - Audio capture + VAD + STT + Ollama + TTS working end-to-end"
Archivos: 58 files, 12,499 líneas
```

### Comandos para Restaurar:

```bash
# Restaurar código
cd /root
tar -xzf backups/la-voip-agent_backup_20251001_030644.tar.gz

# Ver commits
cd /root/la-voip-agent
git log --oneline

# Restaurar n8n database
docker cp backups/n8n/n8n_database_20251001_030611.sqlite root_n8n_1:/home/node/.n8n/database.sqlite
docker restart root_n8n_1
```

---

## 🔧 CONFIGURACIÓN DETALLADA

### N8N Workflow "Grupo Sinergia"

**Estructura:**
```
[Webhook]
    → [AI Agent VoIP]
        → [Respond to Webhook]
```

**Configuración del Webhook:**
- Method: POST
- Path: `my-workflow`
- Response Mode: Using Respond to Webhook Node

**Configuración del AI Agent:**
- Agent: Tools Agent
- Prompt (User Message): `={{ $json.text }}`
  - **IMPORTANTE:** Es `$json.text` NO `$json.body.text`
- Chat Model: Ollama llama3.2:3b-instruct-q4_k_m

**Configuración del Respond to Webhook:**
- Respond With: `Text` (NO JSON - causaba errores)
- Response Body: `={{ $json.response }}`

### Asterisk Configuration

**ARI Connection:**
- URL: http://127.0.0.1:8088/ari
- User: asterisk
- Password: (configurado en Asterisk)
- Aplicación: agente-ia

**Dialplan Entry:**
```
exten => _X.,1,Stasis(agente-ia)
```

### Python Dependencies

Principales:
- `aioari` - Asterisk ARI async client
- `faster-whisper` - STT
- `piper-tts` - TTS
- `silero-vad` - Voice Activity Detection
- `aiohttp` - HTTP async
- `prometheus_client` - Métricas

Ver `/root/la-voip-agent/.venv/` para virtualenv completo.

---

## 🔍 CORRECCIONES CRÍTICAS REALIZADAS

### 1. Bridge vs Channel Recording
**Problema:** `channel.record()` no funcionaba
**Causa:** No puedes grabar un canal que está dentro de un bridge
**Solución:** Usar `bridge.record()` en lugar de `channel.record()`

Código en `rtp_realtime.py`:
```python
# INCORRECTO:
recording = await channel.record(...)

# CORRECTO:
recording = await bridge.record(
    name=recording_name,  # SIN "recording/" prefix
    format="slin",
    maxDurationSeconds=int(duration) + 1,
    ifExists="overwrite",
    terminateOn="none"
)
```

### 2. Path de Grabación
**Problema:** Archivos no se creaban
**Causa:** `name=f"recording/{recording_name}"` creaba path doble
**Solución:** `name=recording_name` directo

Asterisk ARI ya usa `/var/spool/asterisk/recording/` como base.

### 3. Webhook n8n Field Mapping
**Problema:** AI Agent no recibía el mensaje
**Causa:** Buscaba `$json.body.message` pero enviábamos `{"text": "..."}`
**Solución:** Cambiar a `$json.text`

### 4. Response Format
**Problema:** "Invalid JSON in Response Body"
**Causa:** Intentar devolver JSON con `{{ $json.response }}` dentro
**Solución:** Cambiar a Text mode y dejar que app.py maneje texto plano

### 5. Boolean Parameter Error
**Problema:** `maxSilenceSeconds=0` causaba error de tipo
**Solución:** Eliminar parámetro, usar solo `terminateOn="none"`

---

## 📊 MÉTRICAS Y TIEMPOS MEDIDOS

### Timeline de una Llamada Típica:

```
00:00 - Usuario llama
00:02 - Asterisk responde
00:03 - TTS mensaje bienvenida inicia
00:10 - TTS mensaje bienvenida termina (7s)
00:11 - Sistema escucha (captura 5s)
00:16 - Audio capturado (5s de grabación)
00:18 - VAD detecta voz (2s procesamiento)
00:20 - STT transcribe (2s)
00:21 - Webhook a n8n (POST instantáneo)
01:11 - n8n + Ollama responde (50s ⚠️ BOTTLENECK)
01:12 - TTS genera audio (1s)
01:12 - Playback inicia
01:25 - Playback termina (13s de audio)
```

**PROBLEMA CRÍTICO:** 50 segundos entre transcripción y respuesta

### Desglose de Latencias:

| Componente | Tiempo Actual | Objetivo |
|------------|---------------|----------|
| Audio Capture | 5s (fijo) | 5s |
| VAD Detection | 2s | 1s |
| STT Transcription | 2s | 1s |
| **n8n + Ollama** | **50s** ⚠️ | **< 3s** |
| TTS Synthesis | 1s | 1s |
| **TOTAL** | **60s** | **< 11s** |

---

## 🎯 CUELLOS DE BOTELLA IDENTIFICADOS

### 🔴 CRÍTICO #1: Ollama Processing (50s)

**Causas Potenciales:**
1. Modelo muy grande (3B parámetros)
2. Sin límite de tokens en respuesta
3. Temperature alta (creatividad excesiva)
4. Sin optimización de prompt para brevedad
5. Recursos de Docker limitados

**Soluciones a Implementar:**
- [ ] Agregar `max_tokens: 50` en AI Agent
- [ ] Cambiar `temperature: 0.7` → `0.3`
- [ ] Optimizar system prompt: "Responde en MÁXIMO 2 oraciones"
- [ ] Considerar modelo más pequeño (1B)
- [ ] Verificar recursos Docker (CPU/RAM)
- [ ] Streaming de respuesta (parcial)

### ⚠️ #2: Audio Capture Loop (5s fijos)

Cada captura toma 5 segundos completos, incluso si el usuario habla 1 segundo.

**Soluciones:**
- [ ] Captura dinámica basada en VAD
- [ ] Stream de audio continuo
- [ ] Buffer circular de audio

### ⚠️ #3: Interrupciones No Funcionan

Usuario no puede interrumpir al agente mientras habla.

**Causas:**
- Audio se captura pero se rechaza por "baja calidad"
- No hay detección de interrupción activa

**Soluciones:**
- [ ] Detección de voz durante playback
- [ ] Cancelar playback si usuario habla
- [ ] Barge-in implementation

---

## 🚀 PRÓXIMA FASE: OPTIMIZACIÓN

### Objetivos FASE 2:

1. **Latencia < 5 segundos total**
   - Ollama: < 3s
   - Todo el resto: < 2s

2. **Interrupciones Funcionales**
   - Detectar cuando usuario habla
   - Cancelar respuesta del agente
   - Procesar nueva entrada

3. **Conversación Natural**
   - Respuestas más cortas (2-3 oraciones)
   - Menos formal, más humano
   - Contexto de conversación

4. **Monitoreo y Métricas**
   - Dashboard Grafana
   - Alertas de latencia
   - Logs estructurados

---

## 🛠️ COMANDOS ÚTILES

### Gestión del Servicio:
```bash
# Ver estado
systemctl status la-voip-agent

# Ver logs en tiempo real
journalctl -u la-voip-agent -f

# Reiniciar
systemctl restart la-voip-agent

# Ver métricas
curl http://127.0.0.1:9091/metrics
```

### Debugging:
```bash
# Ver grabaciones
ls -lh /var/spool/asterisk/recording/

# Escuchar grabación (convertir a WAV)
sox -t raw -r 8000 -e signed -b 16 -c 1 archivo.slin output.wav

# Ver logs de n8n
docker logs -f root_n8n_1

# Ver logs de Ollama
docker logs -f <ollama_container>
```

### Testing Manual:
```bash
# Probar webhook n8n
curl -X POST http://0.0.0.0:5678/webhook/my-workflow \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola, soy Ernesto"}'

# Probar webhook test (requiere Execute workflow primero)
curl -X POST http://0.0.0.0:5678/webhook-test/my-workflow \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola"}'
```

---

## 📝 NOTAS IMPORTANTES

### Lecciones Aprendidas:

1. **Asterisk ARI:** No puedes grabar un canal que está en un bridge
2. **Path conventions:** ARI ya agrega el directorio base, no duplicar
3. **n8n Field mapping:** Verificar estructura JSON exacta que llega
4. **Boolean vs Numbers:** Algunos parámetros ARI no aceptan 0 como boolean
5. **Text vs JSON:** A veces es más simple devolver texto plano

### Problemas Encontrados y Resueltos:

- ❌ `channel.record()` → ✅ `bridge.record()`
- ❌ `name="recording/file"` → ✅ `name="file"`
- ❌ `$json.body.message` → ✅ `$json.text`
- ❌ `maxSilenceSeconds=0` → ✅ Eliminado
- ❌ JSON Response → ✅ Text Response
- ❌ Port 9091 conflict → ✅ Kill old process

---

## 🎉 LOGROS DE FASE 1

✅ Sistema funcional de punta a punta
✅ Audio captura trabajando
✅ VAD detectando voz correctamente
✅ STT transcribiendo en español
✅ n8n + Ollama respondiendo
✅ TTS sintetizando voz
✅ Usuario puede conversar con el agente
✅ Código respaldado en Git
✅ Backups completos creados
✅ Arquitectura documentada

**PRÓXIMO OBJETIVO:** Reducir latencia de 60s a < 5s

---

## 📞 CONTACTO Y SOPORTE

- **Usuario:** Ernesto
- **Empresa:** Grupo Sinergia
- **Objetivo:** Mejor agente IA VoIP de LATAM
- **Fecha límite:** Lo antes posible

---

*Documento generado: 4 de Octubre 2025*
*Última actualización del sistema: 1 de Octubre 2025*
