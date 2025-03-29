from scripts.prints import print_tracker_file_registry
from aiohttp import web
from scripts.class_object import Peer, Chunk, File, FileMetadata
from scripts.utils import get_private_ip

# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print


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


async def register_peer(request):
    """
    Registers a new peer to the tracker and updates the file registry.
    """
    try:
        data = await request.json()
        peer_id, ip, port, region = data.get("peer_id"), data.get("ip"), data.get("port"), data.get("vm_region")
        hosted_files = data.get("files", [])  # List of files the peer hosts
        if not peer_id or not ip or not port:
            return web.json_response({"error": "Invalid peer data"}, status=400)
        new_peer = Peer(peer_id, ip, port, region)
        PEERS[peer_id] = new_peer
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
                    chunk_obj.add_peer(new_peer)
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
                        existing_chunk.add_peer(new_peer)
                    else:
                        # If chunk does not exist, create and add it
                        chunk_size = chunk_data.get("chunk_size")
                        new_chunk = Chunk(chunk_name=chunk_name, chunk_size=chunk_size)
                        new_chunk.add_peer(new_peer)
                        existing_file.chunks.append(new_chunk)
        print(f"[INFO] Registered peer {peer_id} at {ip}:{port}")  # Debugging output
        print_tracker_file_registry(TRACKER_FILE_REGISTRY)
        return web.json_response({
            "status": "registered",
            "peers": {peer_id: peer_obj.to_dict() for peer_id, peer_obj in PEERS.items()}
        })

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
        peer_id = data.get("peer_id")
        region = data.get("vm_region")
        dead_peers = data.get("dead_peers", [])
        download_status = data.get("download_status", False)
        new_peer = Peer(peer_id, ip, port, region)

        if not file_name or not chunk_name or not ip or not port:
            return web.json_response({"error": "Missing required fields"}, status=400)

        file_obj = next(
            (f for f in TRACKER_FILE_REGISTRY if f.file_name == file_name), None
        )
        if not file_obj:
            return web.json_response({"error": "File not found"}, status=404)

        chunk_obj = next(
            (c for c in file_obj.chunks if c.chunk_name == chunk_name), None
        )
        if not chunk_obj:
            return web.json_response({"error": "Chunk not found"}, status=404)

        if download_status:
            chunk_obj.add_peer(new_peer)

        for dead in dead_peers:
            chunk_obj.peers = [
                p
                for p in chunk_obj.peers
                if not (p.ip == dead["ip"] and p.port == dead["port"])
            ]

        print_tracker_file_registry(TRACKER_FILE_REGISTRY)

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
            {"status": "registered", "peers": {peer_id: peer_obj.to_dict() for peer_id, peer_obj in PEERS.items()} , "available_files": file_summary}
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
            return web.json_response(
                {"error": "Missing file_name or chunk_name"}, status=400
            )

        file_obj = next(
            (f for f in TRACKER_FILE_REGISTRY if f.file_name == file_name), None
        )
        if not file_obj:
            return web.json_response({"error": "File not found"}, status=404)

        chunk_obj = next(
            (c for c in file_obj.chunks if c.chunk_name == chunk_name), None
        )
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
            return web.json_response(
                {"error": "Missing file_name parameter"}, status=400
            )

        file_obj = next(
            (f for f in TRACKER_FILE_REGISTRY if f.file_name == file_name), None
        )
        if not file_obj:
            return web.json_response({"error": "File not found"}, status=404)

        ################ Using Rarest First Policy ################
        # Sorting based on number of peers serving a chunk #
        sorted_chunks = sorted(file_obj.chunks, key=lambda c: len(c.peers))
        ###########################################################

        chunk_dicts = [
            {"chunk_name": chunk.chunk_name, "chunk_size": chunk.chunk_size}
            for chunk in sorted_chunks
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
        print_tracker_file_registry(TRACKER_FILE_REGISTRY)
        my_ip = get_private_ip()
        print("[INFO] Tracker Server Started on {}:8080".format(my_ip))
        web.run_app(app, host=my_ip, port=8080)
    except Exception as e:
        print(f"[ERROR] Tracker failed to start: {e}")
