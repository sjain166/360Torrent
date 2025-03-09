from aiohttp import web
import os
import socket

FILE_PATH = "/Users/sidpro/Desktop/WorkPlace/UIUC/Spring-25/CS 525/Final Project/360Torrent/tests/data/test_data_send.txt"

async def serve_file(request):
    """
    Serves a file to requesting peers.
    """
    if not os.path.exists(FILE_PATH):
        print(f"[ERROR] File not found: {FILE_PATH}")
        return web.json_response({"error": "File not found"}, status=404)
    
    print(f"[INFO] Serving file: {FILE_PATH}")
    return web.FileResponse(FILE_PATH)

async def start_file_server():
    """
    Starts the file server.
    """
    try:
        ip = socket.gethostbyname(socket.gethostname())  # Automatically fetch the VM's IP
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