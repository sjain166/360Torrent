import asyncio
import aiohttp
import os
import socket
import file_server as file_server


TRACKER_URL = "http://127.0.0.1:8080"  # Replace with actual tracker IP

FILE_PATH = "/Users/sidpro/Desktop/WorkPlace/UIUC/Spring-25/CS 525/Final Project/360Torrent/tests/data" 
HOSTED_FILE = ["test_data_send.txt"]

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

async def register_peer(peer_id, ip, port):
    """
    Registers the peer to the tracker.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{TRACKER_URL}/register", json={"peer_id": peer_id, "ip": ip, "port": port, "files" : HOSTED_FILE}) as response:
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
        ip = get_private_ip() # Automatically fetch the VM's IP
        port = 6881
        await register_peer(peer_id, ip, port)

        peers = await get_peers()
        print(f"[INFO] Active Peers: {peers}")

        # Start the file server
        asyncio.create_task(file_server.start_file_server())
        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        print(f"[ERROR] Peer execution failed: {e}")

asyncio.run(main())