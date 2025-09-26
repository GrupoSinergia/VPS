from aioari import Client
from utils import setup_log

class DTMFHandler:
    def __init__(self, ari_client):
        self.logger = setup_log("dtmf")
        self.ari = ari_client
        self.ari.on_channel_event('ChannelDtmfReceived', self.handle_dtmf)

    async def handle_dtmf(self, channel, event):
        dtmf_digit = event.get('digit')
        if dtmf_digit:
            self.logger.info(f"DTMF detectado: {dtmf_digit}")
            if dtmf_digit == '#':
                await self.ari.channels.hangup(channel_id=channel.id)
            elif dtmf_digit in ['1', '2', '3']:
                await self.ari.channels.play(channel_id=channel.id, media=f'sound:digits/{dtmf_digit}')

def start_dtmf_handler(ari_client):
    return DTMFHandler(ari_client)
