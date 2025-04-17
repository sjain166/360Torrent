from scripts.prints import print_tracker_file_registry
from aiohttp import web
from scripts.class_object import Peer, Chunk, File, FileMetadata
from scripts.utils import get_private_ip
import aiohttp


# Rich Print
import builtins
from rich import print as rich_print
import sys
builtins.print = rich_print


PEERS = {}  # Dictionary to store registered peers {peer_id: (ip, port)}
TRACKER_FILE_REGISTRY = (
    []
)  # Dictionary to store file locations {file_name: [list_of_peers_hosting_it]}
REGION_PEER_MAP = {}  # Dictionary to track peers per region: {region: [Peer]}


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

        is_peer_registered_in_region = False
        if region:
            if region not in REGION_PEER_MAP:
                REGION_PEER_MAP[region] = []
            
            for peer in REGION_PEER_MAP[region]:
                if peer.id == peer_id:
                    print(f"[WARN] Peer {peer_id} already registered in region {region}.")
                    is_peer_registered_in_region = True
                    break
            if not is_peer_registered_in_region:
                REGION_PEER_MAP[region].append(new_peer)
        
        print(REGION_PEER_MAP)

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


def get_best_peers(chunk_obj, requester_region):
    """
    Placeholder function for advanced peer selection logic.
    Currently returns all peers hosting the chunk.
    """
    if PEER_SELECTION_CRITERIA == "LF":
        peers_list = [{"ip": peer.ip, "port": peer.port, "id": peer.id} for peer in (chunk_obj.peers)]
        return peers_list, 0, len(peers_list)
     
    else :
        same_region = []
        other_region = []

        for peer in chunk_obj.peers:
            peer_info = {"ip": peer.ip, "port": peer.port, "id": peer.id}
            if requester_region and peer.region == requester_region:
                same_region.append(peer_info)  # Prioritize peers from same region
            else:
                other_region.append(peer_info)

        return list(reversed(same_region)) + list(reversed(other_region)), len(same_region), len(other_region)
        


async def get_chunk_peers(request):
    try:
        file_name = request.query.get("file_name")
        chunk_name = request.query.get("chunk_name")
        requester_region = request.query.get("vm_region")

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

        peer_information = get_best_peers(chunk_obj, requester_region)
        return web.json_response({"peers": peer_information[0],  "same_region_count" : peer_information[1], "other_region_count" : peer_information[2]})

    except Exception as e:
        print(f"[ERROR] Fetching chunk peers failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)


async def get_file_metadata(request):
    try:
        file_name = request.query.get("file_name")
        region = request.query.get("region")
        peer_id = request.query.get("peer_id")

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
        sorted_chunks = sorted(file_obj.chunks, key=lambda c: len(c.peers))

        chunk_dicts = [
            {"chunk_name": chunk.chunk_name, "chunk_size": chunk.chunk_size}
            for chunk in sorted_chunks
        ]

        metadata = FileMetadata(file_obj.file_name, file_obj.file_size, chunk_dicts)
        ############################### PURELY TO TEST THE TRACKER COMMANDS TO PREFETCH PEER ###############################
        for peer in list(REGION_PEER_MAP.get(region, [])):
            if peer.id != peer_id:
                await command_peer_to_prefetch(peer, file_obj, len(file_obj.chunks) // 3)
        ####################################################################################################################
        return web.json_response(metadata.to_dict())
    except Exception as e:
        print(f"[ERROR] Fetching file metadata failed: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)


async def command_peer_to_prefetch(peer: Peer, file_obj: File, num_chunks: int):
    """
    Command a peer to prefetch a few chunks of a file.
    """
    if not file_obj or not peer:
        print(f"[WARN] Invalid file or peer object for prefetch.")
        return

    # Select random chunks
    import random
    selected_chunks = random.sample(file_obj.chunks, min(num_chunks, len(file_obj.chunks)))

    # Prepare metadata for sending
    chunk_dicts = [
        {"chunk_name": chunk.chunk_name, "chunk_size": chunk.chunk_size}
        for chunk in selected_chunks
    ]
    metadata = FileMetadata(file_obj.file_name, file_obj.file_size, chunk_dicts)

    try:
        url = f"http://{peer.ip}:{peer.port}/prefetch_chunks"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=metadata.to_dict()) as response:
                if response.status == 200:
                    print(f"[INFO] Prefetch command sent to {peer.id}")
                else:
                    print(f"[WARN] Prefetch failed for {peer.id}, status: {response.status}")
    except Exception as e:
        print(f"[ERROR] Exception while sending prefetch to {peer.id}: {e}")

app = web.Application()
app.router.add_post("/register", register_peer)
app.router.add_get("/file_registry", get_tracker_registry_summary)
app.router.add_get("/file_metadata", get_file_metadata)
app.router.add_get("/chunk_peers", get_chunk_peers)
app.router.add_post("/update_chunk_host", update_chunk_host)


if __name__ == "__main__":
    try:
        # if sys.argv != 2 :
        #     print("[ERROR] Invalid Argument Count" + len(sys.argv))
            
        global PEER_SELECTION_CRITERIA
        PEER_SELECTION_CRITERIA = sys.argv[1]
        print("[INFO] Peer Selection Criteria Activated : " + PEER_SELECTION_CRITERIA)
        
        print_tracker_file_registry(TRACKER_FILE_REGISTRY)
        my_ip = get_private_ip()
        print("[INFO] Tracker Server Started on {}:8080".format(my_ip))
        web.run_app(app, host=my_ip, port=8080)
    except Exception as e:
        print(f"[ERROR] Tracker failed to start: {e}")
