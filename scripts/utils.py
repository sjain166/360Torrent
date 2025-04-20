import socket
import multiprocessing
import os
import socket
import requests
import time
import json
import aiohttp
import shutil

from scripts.class_object import Peer, Chunk, File

# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print

import networkx as nx


####################################################################################################

# import debugpy
# debugpy.listen(("localhost", 5678))
# print("🔧 Waiting for debugger to attach on port 5678...")
# debugpy.wait_for_client()  # Blocks execution here

####################################################################################################

#TRACKER_URL = "http://sp25-cs525-1201.cs.illinois.edu:8080"  # Replace with actual tracker IP
TRACKER_URL = "http://10.0.0.130:8080"  # Replace with actual tracker IP
OBSERVE_INTERVAL = 15
HOT_THRESHOLD = 1 # To be decided by the user

FILE_PATH = "tests/data"
DATA_WAREHOUSE = "tests/data_warehouse"
JSON_LOG_FILE_PATH = "tests/summary.json"
TOTAL_FILE_SIZE = 1363089768
EACH_CHUNK_SIZE = 113590814
TOTAL_CHUNK_COUNT = 12


LATENCY_GRAPH = nx.Graph()
LATENCY_GRAPH.add_edge("WA", "NY", weight=65)
LATENCY_GRAPH.add_edge("WA", "CA", weight=31)
LATENCY_GRAPH.add_edge("WA", "FL", weight=79)
LATENCY_GRAPH.add_edge("NY", "CA", weight=62)
LATENCY_GRAPH.add_edge("NY", "FL", weight=34)
LATENCY_GRAPH.add_edge("CA", "FL", weight=63)





def get_private_ip():
    """
    Returns the actual private IP address of the machine.
    This avoids using 127.0.0.1 and ensures that the peer registers
    with its LAN IP.
    """
    try:
        # Create a dummy socket connection to determine the correct network interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(
            ("8.8.8.8", 80)
        )  # Connect to Google's DNS to determine the correct interface
        ip = s.getsockname()[0]  # Extract the private IP from the connection
        s.close()
        return ip
    except Exception as e:
        print(f"[ERROR] Failed to determine private IP: {e}")
        return "127.0.0.1"  # Fallback to loopback if no IP is found


def get_max_threads():
    try:
        max_threads = max(1, multiprocessing.cpu_count()-1)
        print(f"[INFO] Max threads available for downloading: {max_threads}")
        return max_threads
    except Exception as e:
        print(f"[ERROR] Unable to determine max threads: {e}")
        return 1


def scrape_data_folder(VM_NAME, VM_REGION):
    """
    Scrape the tests/data folder to discover all files and chunks.
    """
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
                        Peer(VM_NAME, peer_ip, peer_port, VM_REGION)
                    )  # Assign this peer as a host
                    file_obj.chunks.append(chunk_obj)
                    file_obj.file_size += chunk_size  # Update file size
            PEER_FILE_REGISTRY.append(file_obj)

    return PEER_FILE_REGISTRY


def check_server_status(host, port, path="/health_check", connect_timeout=4, get_timeout=6):
    try:
        # Step 1: Test TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(connect_timeout)
        sock.connect((host, port))
        sock.close()
    except socket.timeout:
        print("⛔ Server unreachable: connection timed out.")
        return "UNREACHABLE"
    except ConnectionRefusedError:
        print("🔌 Server unreachable: connection refused.")
        return "UNREACHABLE"
    except Exception as e:
        print(f"❗ Unexpected connection error: {e}")
        return "UNREACHABLE"

    try:
        # Step 2: Perform 5 GET requests to measure max latency
        url = f"http://{host}:{port}{path}"
        latencies = []

        for i in range(10):
            start = time.time()
            response = requests.get(url, timeout=get_timeout)
            end = time.time()
            latency = end - start
            latencies.append(latency)

            if response.status_code != 200:
                return "BUSY"
            
        max_latency = max(latencies)
        return "RESPONSIVE" if max_latency <= 1 else "BUSY"

    except requests.exceptions.Timeout:
        print("⏳ Server reachable but GET timed out — server likely busy.")
        return "BUSY"
    except Exception as e:
        print(f"❗ Error during GET request: {e}")
        return "BUSY"
    

def append_file_download_summary_to_json(metadata, total_time):
    
    result_summary = {
        "file_name": metadata.file_name,
        "file_size": metadata.file_size,
        "total_download_time_sec": round(total_time, 2),
        "download_finished_time" : time.time(),
        "chunks": [
            {
                "chunk_name": chunk.chunk_name,
                "chunk_size": chunk.chunk_size,
                "downloaded": chunk.download_status,
                "peers_tried" : ", ".join(chunk.peers_tried or []),
                "peers_failed" : ", ".join(chunk.peers_failed or []),
                "download_time" : chunk.download_time
            }
            for chunk in metadata.chunks
        ]
    }

    # Convert to JSON string
    json_result = json.dumps(result_summary, indent=4)
    print("\n📦 [JSON] Download Summary Result:")
    print(json_result)

    if os.path.exists(JSON_LOG_FILE_PATH):
        with open(JSON_LOG_FILE_PATH, "r") as f:
            data = json.load(f)
    else:
        data = []

    data.append(result_summary)

    with open(JSON_LOG_FILE_PATH, "w") as f:
        json.dump(data, f, indent=4)

async def register_peer(peer_id, ip, port, PEER_FILE_REGISTRY):
    """
    Registers the peer to the tracker.
    """
    VM_NAME = os.getenv("PEER_VM_NAME", "UNKNOWN")
    VM_REGION = os.getenv("REGION_NAME", "UNKNOWN")
    

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
                    "peer_id": VM_NAME,
                    "ip": ip,
                    "port": port,
                    "files": hosted_files,
                    "vm_region" : VM_REGION
                },
            ) as response:
                result = await response.json()
                print(f"[INFO] Registration Response: {result}")  # Debugging Output
    except Exception as e:
        print(f"[ERROR] Failed to register peer: {e}")


async def handle_prefetch_chunks(file_metadata_json):
    """
    Given a FileMetadata JSON, copy only the specified chunks from warehouse to data folder.
    """
    global PEER_FILE_REGISTRY

    WAREHOUSE_PATH = "/home/sj99/360Torrent/tests/data_warehouse"
    TARGET_DATA_PATH = "/home/sj99/360Torrent/tests/data"
    VM_NAME = os.getenv("PEER_VM_NAME", "UNKNOWN")
    VM_REGION = os.getenv("REGION_NAME", "UNKNOWN")
    IP = get_private_ip()  # Automatically fetch the VM's IP
    PORT = 6881

    # Parse the FileMetadata JSON
    try:
        if isinstance(file_metadata_json, str):
            file_metadata = json.loads(file_metadata_json)
        else:
            file_metadata = file_metadata_json

        file_name = file_metadata['file_name']
        chunks = file_metadata['chunks']
    except Exception as e:
        print(f"[ERROR] Failed to parse FileMetadata JSON: {e}")
        return

    source_folder = os.path.join(WAREHOUSE_PATH, file_name)
    dest_folder = os.path.join(TARGET_DATA_PATH, file_name)

    # Ensure destination folder exists
    if os.path.exists(dest_folder):
        print(f"[INFO] Prefetch Failed - Folder already exists: {dest_folder}")
        return
    
    os.makedirs(dest_folder, exist_ok=True)

    # Copy only the specified chunks
    copied_chunks = []
    for chunk in chunks:
        chunk_name = chunk['chunk_name']
        src_chunk_path = os.path.join(source_folder, chunk_name)
        dest_chunk_path = os.path.join(dest_folder, chunk_name)
        if os.path.exists(src_chunk_path):
            try:
                shutil.copy2(src_chunk_path, dest_chunk_path)
                copied_chunks.append(chunk_name)
                print(f"[INFO] Copied chunk '{chunk_name}' to data folder.")
            except Exception as e:
                print(f"[ERROR] Failed to copy chunk '{chunk_name}': {e}")
        else:
            print(f"[ERROR] Chunk not found in warehouse: {src_chunk_path}")

    # Update local registry and re-register peer
    PEER_FILE_REGISTRY = scrape_data_folder(VM_NAME, VM_REGION)
    await register_peer(VM_NAME, IP, PORT, PEER_FILE_REGISTRY)

    print(f"[INFO] Prefetch complete. Copied chunks: {copied_chunks}")
    return copied_chunks

