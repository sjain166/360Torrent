import asyncio
import aiohttp
import os
import sys
import peer.file_server as file_server

from scripts.class_object import FileMetadata, File, Chunk
from scripts.utils import get_private_ip, scrape_data_folder, TOTAL_FILE_SIZE, EACH_CHUNK_SIZE, TOTAL_CHUNK_COUNT

from peer.downloader import main as downloader
from scripts.prints import print_registry_summary
from scripts.utils import TRACKER_URL
from scripts.utils import register_peer

# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print
import shutil
import json

# Rather a Fixed Hosted Files, Scrap the Data Folder to update teh Hosted Files before TRacker Registration
# HOSTED_FILE = ["test_data_send.txt"]
PEER_FILE_REGISTRY = []



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
    global VM_NAME, VM_REGION

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TRACKER_URL}/file_metadata", params={"file_name": file_name, "region" : VM_REGION, "peer_id" : VM_NAME}
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
                    return FileMetadata (
                        file_name=file_name,
                        file_size= -1,
                        chunks = [],
                    )
    except Exception as e:
        print(f"[ERROR] Exception during file metadata fetch: {e}")
        return None


async def handle_user_upload(folder_name):
    global PEER_FILE_REGISTRY 

    # WAREHOUSE_PATH = "/home/sj99/360Torrent/tests/data_warehouse"
    # TARGET_DATA_PATH = "/home/sj99/360Torrent/tests/data"

    # source_path = os.path.join(WAREHOUSE_PATH, folder_name)
    # destination_path = os.path.join(TARGET_DATA_PATH, folder_name)

    # if not os.path.exists(source_path):
    #     print(f"[ERROR] Folder not found in warehouse: {source_path}")
    #     return

    try:
        # if os.path.exists(destination_path):
        #     shutil.rmtree(destination_path)  # Clean if folder already exists
        # shutil.copytree(source_path, destination_path)
        # print(f"[INFO] Copied '{folder_name}' from warehouse to data folder.")
        # PEER_FILE_REGISTRY = scrape_data_folder(VM_NAME, VM_REGION)

        ############ NEW TESTING IMPLEMENTATION ############
        file_name = folder_name
        newFile = File(file_name, TOTAL_FILE_SIZE)
        for i in range(0, TOTAL_CHUNK_COUNT + 1) :
            chunk_name = f"chunk_{i}"
            chunk_size = EACH_CHUNK_SIZE
            newChunk = Chunk(chunk_name, chunk_size, download_status=False)
            newFile.add_chunk(newChunk)
        PEER_FILE_REGISTRY.append(newFile)
        await register_peer(VM_NAME, IP, PORT, PEER_FILE_REGISTRY)
        
    except Exception as e:
        print(f"[ERROR] Failed to copy folder: {e}")
        return
    return


async def prompt_user_action():
    while True:
        print("\n[OPTIONS] Select an action:")
        print("1. Get available files")
        print("2. Download a file")
        print("3. Upload a folder to share")
        print("4. Exit")
        choice = (await asyncio.to_thread(input, ">> ")).strip()
        if choice == "1":
            summary = await get_tracker_registry_summary()
            print_registry_summary(summary)
        elif choice == "2":
            file_name = (await asyncio.to_thread(input, "Enter file name: >> ")).strip()
            if file_name:
                print(f"[INFO] You selected to download: {file_name}")
                metadata = await get_file_metadata(file_name)
                await downloader(metadata, PEER_SELECTION_METHOD)
            else:
                print("[WARN] No file name entered.")
        elif choice == "3":
            folder_name= (await asyncio.to_thread(input, "Enter full folder path to upload: >> ")).strip()
            await handle_user_upload(folder_name)
        elif choice == "4":
            print("[INFO] Exiting download prompt loop.")
            break
        else:
            print("[ERROR] Invalid choice. Please select 1, 2, or 3.")

async def main():

    global PEER_FILE_REGISTRY
    global VM_NAME, VM_REGION
    global IP, PORT

    VM_NAME = os.getenv("PEER_VM_NAME", "UNKNOWN")
    VM_REGION = os.getenv("REGION_NAME", "UNKNOWN")

    global PEER_SELECTION_METHOD
    PEER_SELECTION_METHOD = sys.argv[1]
    print("[INFO] Peer Selection Criteria Method : " + PEER_SELECTION_METHOD)

    ##################### SCRAPING TURNED OFF #####################
    # PEER_FILE_REGISTRY = scrape_data_folder(VM_NAME, VM_REGION)
    ###############################################################

    # PEER_FILE_REGISTRY = []
    peer_id = VM_NAME
    try:
        IP = get_private_ip()  # Automatically fetch the VM's IP
        PORT = 6881
        await register_peer(peer_id, IP, PORT, PEER_FILE_REGISTRY)
        await file_server.start_file_server()
        await prompt_user_action()  # Begin prompting user to download files repeatedly
    except Exception as e:
        print(f"[ERROR] Peer execution failed: {e}")

asyncio.run(main())
