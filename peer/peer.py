import asyncio
import aiohttp
import os
import peer.file_server as file_server
from scripts.class_object import FileMetadata
from scripts.utils import get_private_ip, scrape_data_folder

from peer.downloader import main as downloader
from scripts.prints import print_registry_summary
from scripts.utils import TRACKER_URL

# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print

# Rather a Fixed Hosted Files, Scrap the Data Folder to update teh Hosted Files before TRacker Registration
# HOSTED_FILE = ["test_data_send.txt"]
PEER_FILE_REGISTRY = []


async def register_peer(peer_id, ip, port):
    """
    Registers the peer to the tracker.
    """
    hosted_files = [
        {
            "file_name": f.file_name,
            "file_size": f.file_size,
            "chunks": [
                {
                    "chunk_name": c.chunk_name,
                    "chunk_size": c.chunk_size,
                    "peers": [{"ip": p.ip, "port": p.port} for p in c.peers],
                }
                for c in f.chunks
            ],
        }
        for f in PEER_FILE_REGISTRY
    ]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{TRACKER_URL}/register",
                json={
                    "peer_id": peer_id,
                    "ip": ip,
                    "port": port,
                    "files": hosted_files,
                },
            ) as response:
                result = await response.json()
                print(f"[INFO] Registration Response: {result}")  # Debugging Output
    except Exception as e:
        print(f"[ERROR] Failed to register peer: {e}")


async def get_tracker_registry_summary():
    """
    Fetches the list of available files and their seeder info from the tracker.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TRACKER_URL}/file_registry") as response:
                summary = await response.json()
                return summary.get("available_files", [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch file registry summary: {e}")
        return []


async def get_file_metadata(file_name):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TRACKER_URL}/file_metadata", params={"file_name": file_name}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return FileMetadata(
                        file_name=data["file_name"],
                        file_size=data["file_size"],
                        chunks=data["chunks"],
                    )
                else:
                    print(f"[ERROR] File metadata fetch failed: {response.status}")
                    return None
    except Exception as e:
        print(f"[ERROR] Exception during file metadata fetch: {e}")
        return None


async def prompt_user_action():
    while True:
        print("\n[OPTIONS] Select an action:")
        print("1. Get available files")
        print("2. Download a file")
        print("3. Exit")
        choice = (await asyncio.to_thread(input, ">> ")).strip()
        if choice == "1":
            summary = await get_tracker_registry_summary()
            print_registry_summary(summary)
        elif choice == "2":
            file_name = (await asyncio.to_thread(input, "Enter file name: >> ")).strip()
            if file_name:
                print(f"[INFO] You selected to download: {file_name}")
                metadata = await get_file_metadata(file_name)
                await downloader(metadata)
            else:
                print("[WARN] No file name entered.")
        elif choice == "3":
            print("[INFO] Exiting download prompt loop.")
            break
        else:
            print("[ERROR] Invalid choice. Please select 1, 2, or 3.")


async def main():
    global PEER_FILE_REGISTRY
    PEER_FILE_REGISTRY = scrape_data_folder()

    peer_id = f"peer_{os.getpid()}"
    try:
        ip = get_private_ip()  # Automatically fetch the VM's IP
        port = 6881
        await register_peer(peer_id, ip, port)
        await file_server.start_file_server()
        await prompt_user_action()  # Begin prompting user to download files repeatedly
    except Exception as e:
        print(f"[ERROR] Peer execution failed: {e}")


asyncio.run(main())
