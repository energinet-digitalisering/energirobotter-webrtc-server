import asyncio
import logging
import os
from aiohttp import web, WSMsgType
import aiohttp_cors
import json
import uuid


class WebRTCSignalingServer:
    def __init__(self, host="0.0.0.0", port=8080):
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)

        self.host = host
        self.port = port
        self.clients = set()
        self.offer_futures = {}
        self.root = os.path.dirname(__file__)

        self.app = web.Application()
        self._setup_routes()
        self._setup_cors()

        self.runner = web.AppRunner(self.app)

    def _setup_routes(self):
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/client.js", self.javascript)
        self.app.router.add_get("/ws", self.websocket_handler)
        self.app.router.add_post("/signal", self.signal_handler)

    def _setup_cors(self):
        cors = aiohttp_cors.setup(self.app, defaults={
            "http://localhost:8012": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            ),
            "https://gladly-destined-lacewing.ngrok-free.app": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        for route in list(self.app.router.routes()):
            cors.add(route)

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
        try:
            with open(os.path.join(self.root, "index.html"), "r") as f:
                return web.Response(content_type="text/html", text=f.read())
        except FileNotFoundError:
            return web.Response(status=404, text="index.html not found")

    async def javascript(self, request):
        try:
            with open(os.path.join(self.root, "client.js"), "r") as f:
                return web.Response(content_type="application/javascript", text=f.read())
        except FileNotFoundError:
            return web.Response(status=404, text="client.js not found")

    async def signal_handler(self, request):
        try:
            data = await request.json()
            self.logger.info(f"Received signaling data from {request.remote}: {data}")
            data_type = data.get('type')

            if data_type == 'offer':
                offer_id = str(uuid.uuid4())
                self.offer_futures[offer_id] = asyncio.Future()
                for client in self.clients:
                    await client.send_json({'type': 'offer', 'id': offer_id, 'sdp': data['sdp']})
                try:
                    answer = await asyncio.wait_for(self.offer_futures[offer_id], timeout=30)
                    self.logger.info(f"Sending HTTP response with SDP answer: {answer}")
                    del self.offer_futures[offer_id]
                    return web.json_response(answer)
                except asyncio.TimeoutError:
                    del self.offer_futures[offer_id]
                    return web.json_response({"error": "Timeout waiting for answer"}, status=408)
            else:
                self.logger.warning(f"Unknown signaling data type: {data_type}")
                return web.json_response({"error": "Invalid data type"}, status=400)
        except Exception as e:
            self.logger.error(f"Error in signal handler: {e}")
            return web.json_response({"error": str(e)}, status=400)

    async def websocket_handler(self, request):
        self.logger.info(f"WebSocket connection attempt from {request.remote}")
        ws = web.WebSocketResponse()
        ws.headers['Access-Control-Allow-Origin'] = (
            'https://gladly-destined-lacewing.ngrok-free.app' if 'ngrok' in request.host
            else 'http://localhost:8012'
        )
        ws.headers['Access-Control-Allow-Credentials'] = 'true'
        ws.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        ws.headers['Access-Control-Allow-Headers'] = '*'

        await ws.prepare(request)

        self.clients.add(ws)
        self.logger.info(f"Client connected. Total clients: {len(self.clients)}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    self.logger.debug(f"Received WebSocket message: {msg.data}")
                    try:
                        data = json.loads(msg.data)
                        if data.get('type') == 'answer' and 'id' in data:
                            offer_id = data['id']
                            if offer_id in self.offer_futures:
                                self.logger.info(f"Received SDP answer for offer_id {offer_id}: {data}")
                                self.offer_futures[offer_id].set_result(data)
                                self.logger.info(f"Sent SDP answer to client {request.remote}")
                            else:
                                self.logger.warning(f"No pending offer for ID {offer_id}")
                        else:
                            # Relay other messages (e.g., ICE candidates) to all other clients
                            for client in self.clients:
                                if client != ws:
                                    await client.send_str(msg.data)
                    except json.JSONDecodeError:
                        self.logger.error("Invalid JSON in WebSocket message")
        finally:
            self.clients.remove(ws)
            self.logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

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