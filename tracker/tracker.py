import asyncio
from aiohttp import web
import socket
from scripts.class_object import Peer, Chunk, File, FileMetadata
from scripts.utils import get_private_ip
from tabulate import tabulate

PEERS = {}  # Dictionary to store registered peers {peer_id: (ip, port)}
TRACKER_FILE_REGISTRY = (
    []
)  # Dictionary to store file locations {file_name: [list_of_peers_hosting_it]}


def summarize_available_files():
    """
    Summarizes the files in TRACKER_FILE_REGISTRY and returns info on file_name, file_size, and number of seeders.
    """
    summary = []
    for file_obj in TRACKER_FILE_REGISTRY:
        min_seeders = (
            min(len(chunk.peers) for chunk in file_obj.chunks) if file_obj.chunks else 0
        )
        summary.append(
            {
                "file_name": file_obj.file_name,
                "file_size": file_obj.file_size,
                "seeders": min_seeders,
            }
        )
    return summary


def print_tracker_file_registry():
    """
    Prints the TRACKER_FILE_REGISTRY in a tabular format without repeating file names.
    """
    table_data = []
    for file_obj in TRACKER_FILE_REGISTRY:
        file_displayed = False
        for chunk_obj in file_obj.chunks:
            peer_list = ", ".join(
                [f"{peer.ip}:{peer.port}" for peer in chunk_obj.peers]
            )
            table_data.append(
                [
                    (
                        file_obj.file_name if not file_displayed else ""
                    ),  # Print file name only once
                    (
                        file_obj.file_size if not file_displayed else ""
                    ),  # Print file size only once
                    chunk_obj.chunk_name,
                    chunk_obj.chunk_size,
                    peer_list,
                ]
            )
            file_displayed = True
    headers = [
        "File Name",
        "File Size (Bytes)",
        "Chunk Name",
        "Chunk Size (Bytes)",
        "Peers Hosting Chunk",
    ]
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
            existing_file = next(
                (f for f in TRACKER_FILE_REGISTRY if f.file_name == file_name), None
            )
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
                    existing_chunk = next(
                        (c for c in existing_file.chunks if c.chunk_name == chunk_name),
                        None,
                    )
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


async def update_chunk_host(request):
    try:
        data = await request.json()
        file_name = data.get("file_name")
        chunk_name = data.get("chunk_name")
        ip = data.get("ip")
        port = data.get("port")
        dead_peers = data.get("dead_peers", [])
        download_status = data.get("download_status", False)

        if not file_name or not chunk_name or not ip or not port:
            return web.json_response({"error": "Missing required fields"}, status=400)

        file_obj = next((f for f in TRACKER_FILE_REGISTRY if f.file_name == file_name), None)
        if not file_obj:
            return web.json_response({"error": "File not found"}, status=404)

        chunk_obj = next((c for c in file_obj.chunks if c.chunk_name == chunk_name), None)
        if not chunk_obj:
            return web.json_response({"error": "Chunk not found"}, status=404)

        if download_status:
            chunk_obj.add_peer(Peer(ip, port))

        for dead in dead_peers:
            chunk_obj.peers = [p for p in chunk_obj.peers if not (p.ip == dead["ip"] and p.port == dead["port"])]
        
        print_tracker_file_registry()
        
        print(f"[INFO] Updated chunk {chunk_name} of {file_name} with peer {ip}:{port}")
        return web.json_response({"status": "updated"})

    except Exception as e:
        print(f"[ERROR] Failed to update chunk host: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)


async def get_tracker_registry_summary(request):
    """
    Returns a tracker file summary.
    """
    try:
        file_summary = summarize_available_files()
        return web.json_response(
            {"status": "registered", "peers": PEERS, "available_files": file_summary}
        )
    except Exception as e:
        print(f"[ERROR] Fetching Tracker File Summary failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)


def get_best_peers(chunk_obj):
    """
    Placeholder function for advanced peer selection logic.
    Currently returns all peers hosting the chunk.
    """
    return [{"ip": peer.ip, "port": peer.port} for peer in chunk_obj.peers]

async def get_chunk_peers(request):
    try:
        file_name = request.query.get("file_name")
        chunk_name = request.query.get("chunk_name")
        if not file_name or not chunk_name:
            return web.json_response({"error": "Missing file_name or chunk_name"}, status=400)

        file_obj = next((f for f in TRACKER_FILE_REGISTRY if f.file_name == file_name), None)
        if not file_obj:
            return web.json_response({"error": "File not found"}, status=404)

        chunk_obj = next((c for c in file_obj.chunks if c.chunk_name == chunk_name), None)
        if not chunk_obj:
            return web.json_response({"error": "Chunk not found"}, status=404)

        peer_list = get_best_peers(chunk_obj)
        return web.json_response({"peers": peer_list})

    except Exception as e:
        print(f"[ERROR] Fetching chunk peers failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)



async def get_file_metadata(request):
    try:
        file_name = request.query.get("file_name")
        if not file_name:
            return web.json_response({"error": "Missing file_name parameter"}, status=400)

        file_obj = next((f for f in TRACKER_FILE_REGISTRY if f.file_name == file_name), None)
        if not file_obj:
            return web.json_response({"error": "File not found"}, status=404)

        chunk_dicts = [
            {
                "chunk_name": chunk.chunk_name,
                "chunk_size": chunk.chunk_size
            }
            for chunk in file_obj.chunks
        ]
        metadata = FileMetadata(file_obj.file_name, file_obj.file_size, chunk_dicts)
        return web.json_response(metadata.to_dict())
    except Exception as e:
        print(f"[ERROR] Fetching file metadata failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)


app = web.Application()
app.router.add_post("/register", register_peer)
app.router.add_get("/file_registry", get_tracker_registry_summary)
app.router.add_get("/file_metadata", get_file_metadata)
app.router.add_get("/chunk_peers", get_chunk_peers)
app.router.add_post("/update_chunk_host", update_chunk_host)


if __name__ == "__main__":
    try:
        print_tracker_file_registry()
        my_ip = get_private_ip()
        print("[INFO] Tracker Server Started on {}:8080".format(my_ip))
        web.run_app(app, host=my_ip, port=8080)
    except Exception as e:
        print(f"[ERROR] Tracker failed to start: {e}")
