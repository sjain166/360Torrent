import aiohttp
import asyncio
import os
import socket


TRACKER_URL = "http://127.0.0.1:8080"

async def get_file_peers(file_name):
    """
    Queries the tracker for a list of peers hosting the requested file.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{TRACKER_URL}/file_peers", params={"file_name": file_name}) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[INFO] Peers hosting {file_name}: {data.get('peers', [])}")
                    return data.get("peers", [])
                else:
                    print(f"[ERROR] Tracker returned error: {response.status}")
                    return []
        except Exception as e:
            print(f"[ERROR] Failed to fetch file peers from tracker: {e}")
            return []



async def download_file(peer_ip, file_name):
    """
    Downloads a file from the peer.
    """
    URL = f"http://{peer_ip}:6881/file"
    DOWNLOAD_PATH = f"/Users/sidpro/Desktop/WorkPlace/UIUC/Spring-25/CS 525/Final Project/360Torrent/tests/data/test_data_recv.txt"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                if response.status == 200:
                    with open(DOWNLOAD_PATH, "wb") as f:
                        f.write(await response.read())
                    print(f"[INFO] File downloaded successfully to {DOWNLOAD_PATH}")
                else:
                    print(f"[ERROR] Failed to download file: {response.status}")
    except Exception as e:
        print(f"[ERROR] File download failed: {e}")

async def main():
    file_name = "test_data_send.txt"

    # Get the list of peers hosting the file
    peers = await get_file_peers(file_name)

    if not peers:
        print(f"[ERROR] No peers found hosting {file_name}")
        return

    # Select the first available peer
    peer_ip, _ = peers[0]
    print(f"[INFO] Downloading from peer: {peer_ip}")

    await download_file(peer_ip, file_name)

asyncio.run(main())

