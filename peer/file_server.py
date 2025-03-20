from aiohttp import web
import os
import socket

FILES_DIRECTORY = "/Users/sidpro/Desktop/WorkPlace/UIUC/Spring-25/CS 525/Final Project/360Torrent/tests/peer1/"


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

async def serve_file(request):
    """
    Serves a file to requesting peers.
    """

    FILE_NAME = request.query.get("file_name")

    if not FILE_NAME:
        return web.json_response({"error": "No file name provided"}, status=400)
    
    FILE_PATH = os.path.join(FILES_DIRECTORY, FILE_NAME)
    print(f"[INFO] Requested file: {FILE_PATH}")

    if not os.path.exists(FILE_PATH):
        print(f"[ERROR] File not found: {FILE_NAME}")
        return web.json_response({"error": "File not found"}, status=404)
    
    print(f"[INFO] Serving file: {FILE_PATH}")
    return web.FileResponse(FILE_PATH)

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