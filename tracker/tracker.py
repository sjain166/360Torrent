import asyncio
from aiohttp import web

# Dictionary to store registered peers {peer_id: (ip, port)}
peers = {}

async def register_peer(request):
    """
    Registers a new peer to the tracker.
    Expected JSON Input: {"peer_id": "peer1", "ip": "192.168.1.5", "port": 6881}
    """
    try:
        data = await request.json()
        peer_id, ip, port = data.get("peer_id"), data.get("ip"), data.get("port")
        
        if not peer_id or not ip or not port:
            return web.json_response({"error": "Invalid peer data"}, status=400)
        
        peers[peer_id] = (ip, port)
        print(f"[INFO] Registered peer {peer_id} at {ip}:{port}")  # Debugging output
        
        return web.json_response({"status": "registered", "peers": peers})
    
    except Exception as e:
        print(f"[ERROR] Peer registration failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)

async def get_peers(request):
    """
    Returns a list of active peers.
    """
    try:
        return web.json_response({"peers": peers})
    
    except Exception as e:
        print(f"[ERROR] Fetching peers failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)

app = web.Application()
app.router.add_post("/register", register_peer)
app.router.add_get("/peers", get_peers)

if __name__ == "__main__":
    try:
        print("[INFO] Tracker Server Started on 0.0.0.0:8080")
        web.run_app(app, host="0.0.0.0", port=8080)
    except Exception as e:
        print(f"[ERROR] Tracker failed to start: {e}")