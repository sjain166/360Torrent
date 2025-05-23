from aiohttp import web
import os

from scripts.utils import get_private_ip
from scripts.utils import FILE_PATH, DATA_WAREHOUSE
from scripts.utils import handle_prefetch_chunks 
from peer.downloader import main
from scripts.class_object import FileMetadata

# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print
import json

PEER_SELECTION_METHOD = "random"  # Default peer selection method

async def health_check(request):
    return web.Response(status=200, text="OK")

async def serve_file(request):
    """
    Serves a specific chunk file to requesting peers.
    URL should be in format: /file?file_name=<file>&chunk_name=<chunk>
    """
    # file_name = request.query.get("file_name")
    # chunk_name = request.query.get("chunk_name")

    # if not file_name or not chunk_name:
    #     return web.json_response(
    #         {"error": "file_name and chunk_name must be provided"}, status=400
    #     )

    # chunk_path = os.path.join(FILE_PATH, file_name, chunk_name)
    # print(f"[INFO] Requested chunk: {chunk_path}")

    # if not os.path.exists(chunk_path):
    #     print(f"[ERROR] Chunk not found: {chunk_name} in {file_name}")
    #     return web.json_response({"error": "Chunk not found"}, status=404)

    chunk_path = os.path.join(DATA_WAREHOUSE, "chunk.webm")
    print(f"[INFO] Serving chunk: {chunk_path}")
    return web.FileResponse(chunk_path)


async def handle_prefetch_chunk_request(request):
    try:
        data = await request.json()  # or .post() if form-data
        
        file_metadata = FileMetadata(
                        file_name=data["file_name"],
                        file_size=data["file_size"],
                        chunks=data["chunks"],
                    )
        print(f"[INFO] Received prefetch chunk request: {request}")
        await main(file_metadata, PEER_SELECTION_METHOD)
        # await handle_prefetch_chunks(data)
        return web.json_response({"status": "received"}, status=200)
    except Exception as e:
        print(f"[ERROR] Invalid prefetch request: {e}")
        return web.json_response({"error": "Invalid request format"}, status=400)


async def start_file_server(selection_method):
    """
    Starts the file server.
    """
    PEER_SELECTION_METHOD = selection_method
    try :
        ip = get_private_ip()  # Automatically fetch the VM's IP
        port = 6881
        app = web.Application()
        app.router.add_get("/file", serve_file)
        app.router.add_get("/health_check", health_check)
        app.router.add_post("/prefetch_chunks", handle_prefetch_chunk_request)  # Accept the Download Request from the Peer
        print(f"[INFO] File Server Started on {ip}:{port}")

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=ip, port=port)
        await site.start()

    except Exception as e:
        print(f"[ERROR] File server failed to start: {e}")
