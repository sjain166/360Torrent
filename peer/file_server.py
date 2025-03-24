from aiohttp import web
import os
import socket

from scripts.utils import get_private_ip
from scripts.utils import FILE_PATH


async def serve_file(request):
    """
    Serves a specific chunk file to requesting peers.
    URL should be in format: /file?file_name=<file>&chunk_name=<chunk>
    """
    file_name = request.query.get("file_name")
    chunk_name = request.query.get("chunk_name")

    if not file_name or not chunk_name:
        return web.json_response(
            {"error": "file_name and chunk_name must be provided"}, status=400
        )

    chunk_path = os.path.join(FILE_PATH, file_name, chunk_name)
    print(f"[INFO] Requested chunk: {chunk_path}")

    if not os.path.exists(chunk_path):
        print(f"[ERROR] Chunk not found: {chunk_name} in {file_name}")
        return web.json_response({"error": "Chunk not found"}, status=404)

    print(f"[INFO] Serving chunk: {chunk_path}")
    return web.FileResponse(chunk_path)


async def start_file_server():
    """
    Starts the file server.
    """
    try:
        ip = get_private_ip()  # Automatically fetch the VM's IP
        port = 6881
        app = web.Application()
        app.router.add_get("/file", serve_file)
        print(f"[INFO] File Server Started on {ip}:{port}")

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=ip, port=port)
        await site.start()

    except Exception as e:
        print(f"[ERROR] File server failed to start: {e}")
