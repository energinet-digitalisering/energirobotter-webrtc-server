import asyncio
import logging
import os
import json
from aiohttp import web, WSMsgType


class WebRTCSignalingServer:
    def __init__(self, host="0.0.0.0", port=8080):
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)

        self.host = host
        self.port = port
        self.clients = set()
        self.root = os.path.dirname(__file__)

        self.app = web.Application()
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/client.js", self.javascript)
        self.app.router.add_get("/ws", self.websocket_handler)

        self.runner = web.AppRunner(self.app)

    async def start(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, host=self.host, port=self.port)
        await site.start()
        self.logger.info(f"Signaling server running at http://{self.host}:{self.port}")

    async def stop(self):
        self.logger.info("Shutting down signaling server...")
        for ws in list(self.clients):
            await ws.close()
        await self.app.shutdown()
        await self.app.cleanup()
        await self.runner.cleanup()

    async def index(self, request):
        with open(os.path.join(self.root, "index.html"), "r") as f:
            return web.Response(content_type="text/html", text=f.read())

    async def javascript(self, request):
        with open(os.path.join(self.root, "client.js"), "r") as f:
            return web.Response(content_type="application/javascript", text=f.read())

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.clients.add(ws)
        self.logger.info(f"Client connected. Total: {len(self.clients)}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    self.logger.debug(f"Received: {msg.data}")
                    # Relay to all other clients
                    for client in self.clients:
                        if client != ws:
                            await client.send_str(msg.data)
        finally:
            self.clients.remove(ws)
            self.logger.info(f"Client disconnected. Total: {len(self.clients)}")

        return ws


if __name__ == "__main__":
    server = WebRTCSignalingServer()

    async def main():
        await server.start()
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await server.stop()

    asyncio.run(main())
