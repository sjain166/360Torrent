import asyncio
import aiohttp
import os
import socket
import peer.file_server as file_server
from scripts.class_object import Peer, Chunk, File, FileMetadata
from scripts.utils import get_private_ip
from tabulate import tabulate
from peer.downloader import main as downloader
import time




TRACKER_URL = "http://10.0.0.130:8080"  # Replace with actual tracker IP
FILE_PATH = "tests/data"

# Rather a Fixed Hosted Files, Scrap the Data Folder to update teh Hosted Files before TRacker Registration
# HOSTED_FILE = ["test_data_send.txt"]
PEER_FILE_REGISTRY = []


def scrape_data_folder():
    """
    Scrape the tests/data folder to discover all files and chunks.
    """
    global PEER_FILE_REGISTRY
    PEER_FILE_REGISTRY = []
    peer_ip = get_private_ip()
    peer_port = 6881
    if not os.path.exists(FILE_PATH):
        print(f"[ERROR] Data folder not found: {FILE_PATH}")
        return
    for folder in os.listdir(FILE_PATH):
        folder_path = os.path.join(FILE_PATH, folder)
        if os.path.isdir(folder_path):
            file_obj = File(file_name=folder, file_size=0)  # Initialize file object
            for chunk in os.listdir(folder_path):
                chunk_path = os.path.join(folder_path, chunk)
                if os.path.isfile(chunk_path):
                    chunk_size = os.path.getsize(chunk_path)
                    chunk_obj = Chunk(chunk_name=chunk, chunk_size=chunk_size)
                    chunk_obj.peers.append(
                        Peer(peer_ip, peer_port)
                    )  # Assign this peer as a host
                    file_obj.chunks.append(chunk_obj)
                    file_obj.file_size += chunk_size  # Update file size
            PEER_FILE_REGISTRY.append(file_obj)


def print_peer_file_registry():
    """
    Prints the PEER_FILE_REGISTRY in a tabular format without repeating file names.
    """
    table_data = []

    for file_obj in PEER_FILE_REGISTRY:
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


def print_registry_summary(summary):
    """
    Display the tracker file registry summary in a table.
    """
    if not summary:
        print("[WARN] No files available on the tracker.")
        return
    table_data = [
        [file["file_name"], file["file_size"], file["seeders"]] for file in summary
    ]
    headers = ["File Name", "File Size (Bytes)", "Number of Seeders"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


async def get_file_metadata(file_name):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TRACKER_URL}/file_metadata", params={"file_name": file_name}) as response:
                if response.status == 200:
                    data = await response.json()
                    return FileMetadata(file_name=data["file_name"], file_size=data["file_size"], chunks=data["chunks"])
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
        choice = input(">> ").strip()
        if choice == "1":
            summary = await get_tracker_registry_summary()
            print_registry_summary(summary)
        elif choice == "2":
            file_name = input(
                "Enter the name of the file you wish to download: >> "
            ).strip()
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
    scrape_data_folder()
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
