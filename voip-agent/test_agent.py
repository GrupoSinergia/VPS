import asyncio
import websockets
import json
import logging
from config import ARI_URL, ARI_USERNAME, ARI_PASSWORD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ari_connection():
    """Probar conexión a ARI WebSocket"""
    try:
        # URL WebSocket para ARI
        ws_url = f"ws://localhost:8088/ari/events?app=voip-agent&api_key={ARI_USERNAME}:{ARI_PASSWORD}"
        
        logger.info("Conectando a ARI WebSocket...")
        async with websockets.connect(ws_url) as websocket:
            logger.info("✅ Conexión ARI exitosa - Esperando eventos...")
            
            # Escuchar eventos por 30 segundos
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                event = json.loads(message)
                logger.info(f"Evento recibido: {event['type']}")
            except asyncio.TimeoutError:
                logger.info("No hay eventos - Conexión estable")
                
    except Exception as e:
        logger.error(f"Error de conexión: {e}")

if __name__ == "__main__":
    asyncio.run(test_ari_connection())
