import asyncio
import aiohttp
import os
import socket

TRACKER_URL = "http://127.0.0.1:8080"  # Replace with actual tracker IP

async def register_peer(peer_id, ip, port):
    """
    Registers the peer to the tracker.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{TRACKER_URL}/register", json={"peer_id": peer_id, "ip": ip, "port": port}) as response:
                result = await response.json()
                print(f"[INFO] Registration Response: {result}")  # Debugging Output

    except Exception as e:
        print(f"[ERROR] Failed to register peer: {e}")

async def get_peers():
    """
    Fetches the list of active peers from the tracker.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TRACKER_URL}/peers") as response:
                peers = await response.json()
                return peers.get("peers", {})
    
    except Exception as e:
        print(f"[ERROR] Failed to fetch peers: {e}")
        return {}

async def main():
    peer_id = f"peer_{os.getpid()}"
    
    try:
        ip = socket.gethostbyname(socket.gethostname())  # Automatically fetch the VM's IP
        port = 6881
        await register_peer(peer_id, ip, port)
        peers = await get_peers()
        print(f"[INFO] Active Peers: {peers}")
    
    except Exception as e:
        print(f"[ERROR] Peer execution failed: {e}")

asyncio.run(main())