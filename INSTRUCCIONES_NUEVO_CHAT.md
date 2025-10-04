# 🤖 INSTRUCCIONES PARA NUEVO CHAT DE CLAUDE CODE

## 📖 CONTEXTO RÁPIDO

Comparte esto con el nuevo chat:

```
Hola, necesito que me ayudes a optimizar un sistema VoIP IA que ya está funcional.

SITUACIÓN ACTUAL:
- Sistema funciona end-to-end ✅
- Problema: 50-60 segundos de latencia (INACEPTABLE)
- Objetivo: Reducir a < 5 segundos

LEE PRIMERO ESTE DOCUMENTO:
/root/la-voip-agent/FASE1_RESUMEN_COMPLETO.md

Este documento tiene:
- Arquitectura completa
- Todos los archivos y su función
- Ubicación de backups
- Problemas identificados
- Cuellos de botella
- Todo lo que necesitas saber
```

---

## 🎯 OBJETIVO PRINCIPAL

**REDUCIR LATENCIA DE 60s A < 5s**

Actualmente:
- Transcripción STT: 2s ✅
- **n8n + Ollama: 50s** ⚠️ BOTTLENECK
- TTS síntesis: 1s ✅
- Audio capture: 5s (fijo)

**Meta:** Respuesta total < 5 segundos

---

## 📁 ARCHIVOS CLAVE A REVISAR

```bash
# Documento principal con TODO
cat /root/la-voip-agent/FASE1_RESUMEN_COMPLETO.md

# Archivos principales del sistema
/root/la-voip-agent/app.py              # Orquestador
/root/la-voip-agent/rtp_realtime.py     # Audio capture
/root/la-voip-agent/stt.py              # Speech to Text
/root/la-voip-agent/tts.py              # Text to Speech
/root/la-voip-agent/vad.py              # Voice Activity Detection

# Backups
/root/backups/la-voip-agent_backup_20251001_030644.tar.gz
/root/backups/n8n/n8n_database_20251001_030611.sqlite

# Git
cd /root/la-voip-agent
git log --oneline
```

---

## 🔍 CUELLOS DE BOTELLA IDENTIFICADOS

### 1. **Ollama Processing: 50 segundos** 🔴

**Ubicación:** n8n workflow "Grupo Sinergia"
**URL:** http://0.0.0.0:5678

**Causas probables:**
- Modelo muy grande (llama3.2:3b)
- Sin límite de tokens
- Temperature muy alta
- Prompt no optimizado
- Recursos Docker insuficientes

**Acciones sugeridas:**
```bash
# Ver workflow en n8n
# Navegador: http://72.60.116.136:5678
# Login: admin / Sparkurlife5.

# Configurar en AI Agent node:
# - max_tokens: 50
# - temperature: 0.3
# - System prompt: "Responde en MÁXIMO 2 oraciones cortas"
```

### 2. **Audio Capture Loop: 5 segundos fijos**

**Ubicación:** `/root/la-voip-agent/rtp_realtime.py`

Actualmente espera 5s completos incluso si usuario habla 1s.

**Mejoras posibles:**
- Captura dinámica basada en VAD
- Stream continuo de audio
- Reducir a 2-3 segundos

### 3. **No permite interrupciones**

Usuario no puede interrumpir al agente mientras habla.

**Implementar:**
- Detección de voz durante playback
- Cancelación de playback
- Procesamiento de nueva entrada

---

## 📊 MÉTRICAS A MONITOREAR

```bash
# Ver métricas Prometheus
curl http://127.0.0.1:9091/metrics | grep -E "stt_latency|tts_latency"

# Logs en tiempo real
journalctl -u la-voip-agent -f

# Ver grabaciones de audio
ls -lh /var/spool/asterisk/recording/
```

---

## 🧪 TESTING

### Probar Webhook n8n:
```bash
curl -X POST http://0.0.0.0:5678/webhook/my-workflow \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola, me llamo Ernesto"}' \
  -w "\nTiempo total: %{time_total}s\n"
```

**Tiempo esperado actualmente:** ~50 segundos
**Tiempo objetivo:** < 3 segundos

### Hacer una llamada de prueba:
1. Llamar al número configurado en Zadarma
2. Escuchar mensaje de bienvenida
3. Hablar claramente: "Hola, me llamo Ernesto"
4. **Cronometrar** cuánto tarda en responder
5. Reportar tiempo medido

---

## 🚀 PLAN DE OPTIMIZACIÓN SUGERIDO

### FASE 2A: Optimización Rápida (< 1 día)

1. **n8n AI Agent:**
   ```
   ✓ Agregar max_tokens: 50
   ✓ Cambiar temperature: 0.3
   ✓ Optimizar system prompt
   ✓ Medir nueva latencia
   ```

2. **Ollama Docker:**
   ```
   ✓ Verificar recursos asignados
   ✓ Probar modelo más pequeño (1B)
   ✓ Ajustar configuración
   ```

3. **Audio Capture:**
   ```
   ✓ Reducir duración de 5s a 3s
   ✓ Probar si afecta calidad
   ```

**Objetivo:** Reducir de 60s a ~15-20s

### FASE 2B: Optimización Profunda (1-2 días)

4. **Streaming:**
   ```
   ✓ Stream de respuesta Ollama
   ✓ TTS incremental
   ✓ Playback mientras genera
   ```

5. **Interrupciones:**
   ```
   ✓ VAD durante playback
   ✓ Cancelación de audio
   ✓ Barge-in implementation
   ```

6. **Cache de respuestas:**
   ```
   ✓ Respuestas comunes pre-generadas
   ✓ Cache de transcripciones
   ```

**Objetivo:** Reducir a < 5s

---

## 🔧 COMANDOS DE GESTIÓN

```bash
# Estado del servicio
systemctl status la-voip-agent

# Reiniciar después de cambios
systemctl restart la-voip-agent

# Ver logs detallados
journalctl -u la-voip-agent --since "5 minutes ago" -f

# Verificar n8n
docker ps | grep n8n
docker logs -f root_n8n_1

# Verificar Ollama
docker ps | grep ollama
docker logs -f <ollama_container>
```

---

## ⚠️ COSAS IMPORTANTES A NO ROMPER

### ✅ LO QUE FUNCIONA (NO TOCAR):

1. **Bridge Recording**
   ```python
   # En rtp_realtime.py
   recording = await bridge.record(
       name=recording_name,  # NO agregar "recording/" prefix
       format="slin",
       ...
   )
   ```

2. **n8n Webhook Field**
   ```javascript
   // En AI Agent node
   Prompt: ={{ $json.text }}  // NO $json.body.text
   ```

3. **Response Format**
   ```javascript
   // En Respond to Webhook
   Respond With: Text  // NO JSON
   Response Body: ={{ $json.response }}
   ```

4. **Service Port**
   ```
   Puerto 9091 para Prometheus
   Verificar que no esté ocupado antes de iniciar
   ```

### ❌ ERRORES COMUNES A EVITAR:

- No usar `channel.record()` → Usar `bridge.record()`
- No poner `maxSilenceSeconds=0` → Causa error boolean
- No duplicar path en name → Ya incluye `/var/spool/asterisk/recording/`
- No devolver JSON mal formado → Usar Text mode

---

## 📞 INFORMACIÓN DE ACCESO

### Servicios:
- **n8n Web:** http://72.60.116.136:5678
  - User: admin
  - Pass: Sparkurlife5.

- **Asterisk ARI:** http://127.0.0.1:8088/ari
  - User: asterisk
  - App: agente-ia

- **Prometheus:** http://127.0.0.1:9091/metrics

### Ubicaciones:
- **Código:** `/root/la-voip-agent/`
- **Backups:** `/root/backups/`
- **Grabaciones:** `/var/spool/asterisk/recording/`
- **Logs:** `journalctl -u la-voip-agent`

---

## 🎯 RESULTADO ESPERADO

Después de optimizar, una llamada típica debería ser:

```
00:00 - Usuario llama
00:02 - Mensaje bienvenida (7s TTS)
00:09 - Escucha usuario (2-3s)
00:12 - STT transcribe (1s)
00:13 - Ollama responde (2s) ← OPTIMIZADO
00:15 - TTS genera (1s)
00:16 - Playback respuesta
00:22 - Fin respuesta

LATENCIA TOTAL: ~13 segundos ✅
```

**vs situación actual de 60+ segundos** ❌

---

## 🤝 COLABORACIÓN

Si necesitas más información:
1. Lee `/root/la-voip-agent/FASE1_RESUMEN_COMPLETO.md`
2. Revisa logs: `journalctl -u la-voip-agent -n 100`
3. Prueba webhook: `curl http://0.0.0.0:5678/webhook/my-workflow ...`
4. Haz una llamada de prueba y mide tiempos

**META FINAL:** EL MEJOR AGENTE DE IA VOIP DE LATAM 🏆

---

*Preparado para continuidad de desarrollo*
*Fecha: 4 de Octubre 2025*
