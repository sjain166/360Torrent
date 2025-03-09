import aiohttp
import asyncio
import os
import socket

async def download_file(peer_ip):
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
    peer_ip = socket.gethostbyname(socket.gethostname())
    await download_file(peer_ip)

asyncio.run(main())

