import asyncio
from aiohttp import web
import socket

# Dictionary to store registered peers {peer_id: (ip, port)}
peers = {}

# Dictionary to store file locations {file_name: [list_of_peers_hosting_it]}
file_registry = {}

async def register_peer(request):
    """
    Registers a new peer to the tracker.
    Expected JSON Input: {"peer_id": "peer1", "ip": "192.168.1.5", "port": 6881}
    """
    try:
        data = await request.json()
        peer_id, ip, port = data.get("peer_id"), data.get("ip"), data.get("port")
        hosted_files = data.get("files", []) # List of files the peer hosts

        if not peer_id or not ip or not port:
            return web.json_response({"error": "Invalid peer data"}, status=400)
        
        peers[peer_id] = (ip, port)

        # Register files hosted by the peer
        for file_name in hosted_files:
            if file_name not in file_registry:
                file_registry[file_name] = []
            if (ip, port) not in file_registry[file_name]:
                file_registry[file_name].append((ip, port))
        
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


async def get_file_peers(request):
    """
    Returns the list of peers hosting a requested file.
    """
    try:
        file_name = request.query.get("file_name")

        if not file_name or file_name not in file_registry:
            return web.json_response({"error": "File not found"}, status=404)

        return web.json_response({"peers": file_registry[file_name]})

    except Exception as e:
        print(f"[ERROR] Fetching file peers failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)


app = web.Application()
app.router.add_post("/register", register_peer)
app.router.add_get("/peers", get_peers)
app.router.add_get("/file_peers", get_file_peers)


def get_private_ip():
    """
    Returns the actual private IP address of the machine.
    This avoids using 127.0.0.1 and ensures that the peer registers
    with its LAN IP.
    """
    try:
        # Create a dummy socket connection to determine the correct network interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google's DNS to determine the correct interface
        ip = s.getsockname()[0]  # Extract the private IP from the connection
        s.close()
        return ip
    except Exception as e:
        print(f"[ERROR] Failed to determine private IP: {e}")
        return "127.0.0.1"  # Fallback to loopback if no IP is found
    
if __name__ == "__main__":
    try:
        my_ip = get_private_ip()
        print("[INFO] Tracker Server Started on {}:8080".format(my_ip))
        web.run_app(app, host=my_ip, port=8080)
    except Exception as e:
        print(f"[ERROR] Tracker failed to start: {e}")
