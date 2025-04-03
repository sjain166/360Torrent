import aiohttp
import asyncio
import os
import socket
import random
import time
import sys

from scripts.class_object import FileMetadata
from scripts.utils import get_private_ip, get_max_threads, check_server_status, append_file_download_summary_to_json
from scripts.utils import TRACKER_URL, FILE_PATH
from scripts.prints import print_file_metadata



MAX_PARALLEL_DOWNLOADS = get_max_threads()
RESULTS_JSON_PATH = "download_results.json"

# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print


async def get_chunk_peers(file_name, chunk_name):
    """
    Queries the tracker for a list of peers hosting a specific chunk of the file.
    """
    VM_REGION = os.getenv("REGION_NAME", "UNKNOWN")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{TRACKER_URL}/chunk_peers",
                params={"file_name": file_name, "chunk_name": chunk_name, "vm_region" : VM_REGION},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("peers", []), data.get("same_region_count"), data.get("other_region_count")
                else:
                    print(
                        f"[ERROR] Tracker returned error for chunk {chunk_name}: {response.status}"
                    )
                    return []
        except Exception as e:
            print(f"[ERROR] Failed to fetch chunk peers: {e}")
            return []


async def register_downloaded_file(peer_id, ip, port, file_name):
    """
    Registers a newly downloaded file with the tracker so that other peers can request it.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{TRACKER_URL}/register",
                json={
                    "peer_id": peer_id,
                    "ip": ip,
                    "port": port,
                    "files": [file_name],  # Add the newly downloaded file
                },
            ) as response:
                result = await response.json()
                print(f"[INFO] Tracker updated with new file availability: {result}")
        except Exception as e:
            print(f"[ERROR] Failed to register downloaded file: {e}")


async def download_chunk(peer_ip, peer_id, file_name, chunk_name):
    """
    Downloads a specific chunk from the given peer with a progress bar.
    """
    URL = f"http://{peer_ip}:6881/file?file_name={file_name}&chunk_name={chunk_name}"
    folder_path = os.path.join(FILE_PATH, file_name)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, chunk_name)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                if response.status == 200:
                    with open(file_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(1024):
                            f.write(chunk)
                    return True
                else:
                    print(
                        f"[ERROR] Failed to download {chunk_name} from {peer_id}: {response.status}"
                    )
                    return False
    except Exception as e:
        print(f"[ERROR] Download failed for {chunk_name} from {peer_id}: {e}")
        return False


async def update_tracker_chunk_host(
    file_name, chunk_name, ip, port, dead_peers, download_status
):
    """
    Informs the tracker that the peer now hosts a newly downloaded chunk.
    """
    VM_NAME = os.getenv("PEER_VM_NAME", "UNKNOWN")
    VM_REGION = os.getenv("REGION_NAME", "UNKNOWN")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{TRACKER_URL}/update_chunk_host",
                json={
                    "peer_id" : VM_NAME,
                    "file_name": file_name,
                    "chunk_name": chunk_name,
                    "ip": ip,
                    "port": port,
                    "dead_peers": dead_peers,
                    "download_status": download_status,
                    "vm_region" : VM_REGION
                },
            ) as response:
                if response.status != 200:
                    print(
                        f"[WARN] Tracker update for {chunk_name} failed: {response.status}"
                    )
                    
        except Exception as e:
            print(f"[ERROR] Tracker update exception: {e}")


async def download_chunk_with_retry(chunk, metadata, semaphore, self_ip, self_port, PEER_SELECTION_METHOD):
    chunk_name = chunk.chunk_name
    chunk_size = chunk.chunk_size
    dead_peers = []

    start_time_chunk = time.time()
    peers_information = await get_chunk_peers(metadata.file_name, chunk_name)
    peers = peers_information[0]
    same_region_count = peers_information[1]
    other_region_count = peers_information[2]
    
    print("[INFO] List of Peers Hosting Chunk:", chunk_name, ":", ", ".join(peer["id"] for peer in peers))
    print("[INFO] SR : " , same_region_count)
    print("[INFO] OR : " , other_region_count)

    is_peer_same_region = False
    ip = get_private_ip()

    folder_path = os.path.join(FILE_PATH, metadata.file_name)
    file_path = os.path.join(folder_path, chunk_name)
    
    if os.path.exists(file_path):
        print(f"[WARN] Chunk already downloaded: {chunk_name}")
        chunk.download_status = True
        chunk.peers_tried.append("SELF")
        chunk.download_time = 0.0
        return
    
    async with semaphore:
        peer_index = 0
        while peers:
            
            if PEER_SELECTION_METHOD == "SEQ":
                peer = peers[peer_index]
            else :
                if same_region_count > 0 :
                    peer_idx = random.randint(0 , same_region_count - 1) # Randomized Peer Choice  
                    peer = peers[peer_idx]
                    is_peer_same_region = True
                else :
                    peer = random.choice(peers)
                    is_peer_same_region = False

            if peer["ip"] == ip:
                peers.pop(peer_index)

                if is_peer_same_region:
                    same_region_count -= 1
                else :
                    other_region_count -= 1
                
                if len(peers) == 0:
                    break

                peer_index = peer_index % len(peers)
                chunk.peers_tried.append("SELF")
                print(f"[WARN] SKIPPING self.peer_ip : {peer}")
                continue

            host_status = check_server_status(peer["ip"], peer["port"], path="/health_check", connect_timeout=2, get_timeout=4)

            if host_status == "UNREACHABLE":
                print(f"[WARN]❗ Unreachable peer removed: {peer}")

                if is_peer_same_region:
                    same_region_count -= 1
                else :
                    other_region_count -= 1

                dead_peers.append(peer)
                chunk.peers_failed.append(peer["id"])
                peers.pop(peer_index)
                if len(peers) == 0:
                    break
                peer_index = peer_index % len(peers)  # stay in bounds
                continue

            elif host_status == "BUSY":
                print(f"[INFO] ℹ️ Peer is busy, trying next: {peer}")
                chunk.peers_tried.append(peer["id"])
                if len(peers) == 0:
                    break
                peer_index = (peer_index + 1) % len(peers)
                continue

            # ✅ Peer is responsive → try download
            try:
                success = await download_chunk(peer["ip"], peer["id"], metadata.file_name, chunk_name)
            except Exception as e:
                print(f"[ERROR] Download attempt failed from {peer['id']}: {e}")
                success = False

            if success:
                chunk.download_status = True
                chunk.peers_tried.append(peer["id"])
                end_time_chunk = time.time()
                chunk.download_time = end_time_chunk-start_time_chunk

                await update_tracker_chunk_host(
                    metadata.file_name,
                    chunk_name,
                    self_ip,
                    self_port,
                    dead_peers,
                    True
                )
                break
            else:
                print(f"[WARN] Peer failed, skipping for now: {peer}")
                chunk.peers_tried.append(peer["id"])
                if len(peers) == 0:
                    break
                peer_index = (peer_index + 1) % len(peers)

        await update_tracker_chunk_host(
            metadata.file_name,
            chunk_name,
            self_ip,
            self_port,
            dead_peers,
            False
        )

async def main(metadata: FileMetadata, PEER_SELECTION_METHOD):
    try:
        print(f"[INFO] Preparing to download file: {metadata.file_name}")
        print_file_metadata(metadata)

        start_time = time.time()
        self_ip = get_private_ip()
        self_port = 6881

        semaphore = asyncio.Semaphore(MAX_PARALLEL_DOWNLOADS)
        download_tasks = [
            download_chunk_with_retry(chunk, metadata, semaphore, self_ip, self_port, PEER_SELECTION_METHOD)
            for idx, chunk in enumerate(metadata.chunks)
        ]
        await asyncio.gather(*download_tasks)

        # Default assumption: download was successful
        file_download_status = True
        
        for c in metadata.chunks:
            print(f"[DEBUG] {c.chunk_name}: Tried={c.peers_tried}, Failed={c.peers_failed}")
            if c.download_time == -1:
                file_download_status = False
        
        if not file_download_status:
            total_time = -1
            print("[WARNING] Some chunks failed. Marking download as failed.")
        else:
            end_time = time.time()
            total_time = end_time - start_time
        
        print("\n[INFO] Download Summary:")
        print_file_metadata(metadata)
        print("\n🕒 [INFO] Total download time: {:.2f} seconds".format(total_time))
        append_file_download_summary_to_json(metadata, total_time)

    except Exception as e:
        print(f"[ERROR] Peer Execution Failed: {e}")


if __name__ == "__main__":
    print(
        "[INFO] Downloader script expected to be invoked with metadata passed externally."
    )
    get_max_threads()
