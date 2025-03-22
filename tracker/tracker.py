import asyncio
from aiohttp import web
import socket
from scripts.class_object import Peer, Chunk, File
from tabulate import tabulate

# Dictionary to store registered peers {peer_id: (ip, port)}
PEERS = {}

# Dictionary to store file locations {file_name: [list_of_peers_hosting_it]}
TRACKER_FILE_REGISTRY = []

def summarize_available_files():
    """
    Summarizes the files in TRACKER_FILE_REGISTRY and returns info on file_name, file_size, and number of seeders.
    """
    summary = []
    for file_obj in TRACKER_FILE_REGISTRY:
        min_seeders = min(len(chunk.peers) for chunk in file_obj.chunks) if file_obj.chunks else 0
        summary.append({
            "file_name": file_obj.file_name,
            "file_size": file_obj.file_size,
            "seeders": min_seeders
        })
    return summary

def print_tracker_file_registry():
    """
    Prints the TRACKER_FILE_REGISTRY in a tabular format without repeating file names.
    """
    table_data = []
    
    for file_obj in TRACKER_FILE_REGISTRY:
        file_displayed = False
        for chunk_obj in file_obj.chunks:
            peer_list = ", ".join([f"{peer.ip}:{peer.port}" for peer in chunk_obj.peers])
            table_data.append([
                file_obj.file_name if not file_displayed else "",  # Print file name only once
                file_obj.file_size if not file_displayed else "",  # Print file size only once
                chunk_obj.chunk_name,
                chunk_obj.chunk_size,
                peer_list
            ])
            file_displayed = True
    
    headers = ["File Name", "File Size (Bytes)", "Chunk Name", "Chunk Size (Bytes)", "Peers Hosting Chunk"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

async def register_peer(request):
    """
    Registers a new peer to the tracker and updates the file registry.
    """
    try:
        data = await request.json()
        peer_id, ip, port = data.get("peer_id"), data.get("ip"), data.get("port")
        hosted_files = data.get("files", [])  # List of files the peer hosts

        if not peer_id or not ip or not port:
            return web.json_response({"error": "Invalid peer data"}, status=400)
        
        PEERS[peer_id] = (ip, port)

        # Process files sent by the peer
        for file_data in hosted_files:
            file_name = file_data.get("file_name")
            file_size = file_data.get("file_size")
            chunks = file_data.get("chunks", [])
            
            # Check if file already exists in the registry
            existing_file = next((f for f in TRACKER_FILE_REGISTRY if f.file_name == file_name), None)
            if not existing_file:
                # If file does not exist, create a new file entry
                new_file = File(file_name=file_name, file_size=file_size)
                for chunk_data in chunks:
                    chunk_name = chunk_data.get("chunk_name")
                    chunk_size = chunk_data.get("chunk_size")
                    chunk_obj = Chunk(chunk_name=chunk_name, chunk_size=chunk_size)
                    chunk_obj.add_peer(Peer(ip, port))
                    new_file.chunks.append(chunk_obj)
                TRACKER_FILE_REGISTRY.append(new_file)
            else:
                # If file exists, update existing chunks
                for chunk_data in chunks:
                    chunk_name = chunk_data.get("chunk_name")
                    existing_chunk = next((c for c in existing_file.chunks if c.chunk_name == chunk_name), None)
                    if existing_chunk:
                        # If chunk exists, add new peer to it
                        existing_chunk.add_peer(Peer(ip, port))
                    else:
                        # If chunk does not exist, create and add it
                        chunk_size = chunk_data.get("chunk_size")
                        new_chunk = Chunk(chunk_name=chunk_name, chunk_size=chunk_size)
                        new_chunk.add_peer(Peer(ip, port))
                        existing_file.chunks.append(new_chunk)

        print(f"[INFO] Registered peer {peer_id} at {ip}:{port}")  # Debugging output
        print_tracker_file_registry()
        return web.json_response({"status": "registered", "peers": PEERS})
    
    except Exception as e:
        print(f"[ERROR] Peer registration failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)

async def get_tracker_registry_summary(request):
    """
    Returns a tracker file summary.
    """
    try:
        file_summary = summarize_available_files()
        return web.json_response({"status": "registered", "peers": PEERS, "available_files": file_summary})
    
    except Exception as e:
        print(f"[ERROR] Fetching Tracker File Summary failed: {e}")
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
app.router.add_get("/file_registry", get_tracker_registry_summary)
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
        print_tracker_file_registry()
        my_ip = get_private_ip()
        print("[INFO] Tracker Server Started on {}:8080".format(my_ip))
        web.run_app(app, host=my_ip, port=8080)
    except Exception as e:
        print(f"[ERROR] Tracker failed to start: {e}")
