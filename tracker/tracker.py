import asyncio
from aiohttp import web

"""
This is a simple tracker that keeps track of all the peers in the network. ON VM1
"""

peers = {} # Dictionary to store peers

async def register_peer(request):
    """
    Registera new peer
    """
    data = await request.json()
    peer_id, ip, port = data["peer_id"], data["ip"], data["port"]
    peers[peer_id] = (ip, port)
    return web.json_response({"status": "REGISTERED", "peers": peers})

async def get_peers(request):
    """
    Get all peers
    """
    return web.json_response({"peers": peers})

app = web.Application()
app.router.add_post("/register", register_peer)
app.router.add_get("/peers", get_peers)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080) 

