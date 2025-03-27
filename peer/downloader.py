import aiohttp
import asyncio
import os
import socket
import random
from tqdm import tqdm
import time

from scripts.class_object import FileMetadata
from scripts.utils import get_private_ip, get_max_threads
from tabulate import tabulate
from scripts.utils import TRACKER_URL
from scripts.prints import print_file_metadata

MAX_PARALLEL_DOWNLOADS = get_max_threads() - 4

# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print


async def get_chunk_peers(file_name, chunk_name):
    """
    Queries the tracker for a list of peers hosting a specific chunk of the file.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{TRACKER_URL}/chunk_peers",
                params={"file_name": file_name, "chunk_name": chunk_name},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("peers", [])
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


async def download_chunk(peer_ip, file_name, chunk_name, chunk_size):
    """
    Downloads a specific chunk from the given peer with a progress bar.
    """
    URL = f"http://{peer_ip}:6881/file?file_name={file_name}&chunk_name={chunk_name}"
    folder_path = os.path.join("tests/data", file_name)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, chunk_name)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                if response.status == 200:
                    with open(file_path, "wb") as f:
                        downloaded = 0
                        pbar = tqdm(
                            total=chunk_size,
                            unit="B",
                            unit_scale=True,
                            desc=f"Chunk: {chunk_name[:15]}",
                            leave=True,
                        )
                        async for chunk in response.content.iter_chunked(1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            pbar.update(len(chunk))
                        pbar.close()
                    print(f"[INFO] Downloaded {chunk_name} from {peer_ip}")
                    return True
                else:
                    print(
                        f"[ERROR] Failed to download {chunk_name} from {peer_ip}: {response.status}"
                    )
                    return False
    except Exception as e:
        print(f"[ERROR] Download failed for {chunk_name} from {peer_ip}: {e}")
        return False


async def update_tracker_chunk_host(
    file_name, chunk_name, ip, port, dead_peers, download_status
):
    """
    Informs the tracker that the peer now hosts a newly downloaded chunk.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{TRACKER_URL}/update_chunk_host",
                json={
                    "file_name": file_name,
                    "chunk_name": chunk_name,
                    "ip": ip,
                    "port": port,
                    "dead_peers": dead_peers,
                    "download_status": download_status,
                },
            ) as response:
                if response.status == 200:
                    print(f"[INFO] Tracker updated with new host for {chunk_name}")
                else:
                    print(
                        f"[WARN] Tracker update for {chunk_name} failed: {response.status}"
                    )
        except Exception as e:
            print(f"[ERROR] Tracker update exception: {e}")


async def download_chunk_with_retry(chunk, metadata, semaphore, dead_peer_map, self_ip, self_port):
    chunk_name = chunk.chunk_name
    chunk_size = chunk.chunk_size
    dead_peers = []
    peers = await get_chunk_peers(metadata.file_name, chunk_name)

    async with semaphore:
        while peers:
            peer = random.choice(peers)
            try:
                success = await download_chunk(peer["ip"], metadata.file_name, chunk_name, chunk_size)
            except Exception as e:
                print(f"[ERROR] Failed to download chunk {chunk_name} from {peer}: {e}")
                success = False

            if success:
                chunk.download_status = True
                await update_tracker_chunk_host(
                    metadata.file_name,
                    chunk_name,
                    self_ip,
                    self_port,
                    dead_peers,
                    True
                )
                return
            else:
                peers.remove(peer)
                dead_peers.append(peer)
                print(f"[WARN] Removed {peer} from retry list for {chunk_name}")

        await update_tracker_chunk_host(
            metadata.file_name,
            chunk_name,
            self_ip,
            self_port,
            dead_peers,
            False
        )
        dead_peer_map[chunk_name] = dead_peers
        print(f"[ERROR] Failed to download chunk: {chunk_name}")

async def main(metadata: FileMetadata):
    try:
        print(f"[INFO] Preparing to download file: {metadata.file_name}")
        print_file_metadata(metadata)
        dead_peer_map = {}  # {chunk_name: [dead_peer_ips]}

        start_time = time.time()
        self_ip = get_private_ip()
        self_port = 6881

        semaphore = asyncio.Semaphore(MAX_PARALLEL_DOWNLOADS)
        download_tasks = [
            download_chunk_with_retry(chunk, metadata, semaphore, dead_peer_map, self_ip, self_port)
            for chunk in metadata.chunks
        ]
        await asyncio.gather(*download_tasks)

        end_time = time.time()  # End timer
        total_time = end_time - start_time

        print("\n[INFO] Download Summary:")
        print_file_metadata(metadata)
        print("\n🕒 [INFO] Total download time: {:.2f} seconds".format(total_time))

        print("\n[INFO] Dead Peer Map:")
        for chunk_name, peers in dead_peer_map.items():
            print(f"  {chunk_name}: {peers}")

    except Exception as e:
        print(f"[ERROR] Peer Execution Failed: {e}")


if __name__ == "__main__":
    print(
        "[INFO] Downloader script expected to be invoked with metadata passed externally."
    )
    get_max_threads()
