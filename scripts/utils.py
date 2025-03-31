import socket
import multiprocessing
import os
import socket
import requests
import time
import json

from scripts.class_object import Peer, Chunk, File

# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print


####################################################################################################

# import debugpy
# debugpy.listen(("localhost", 5678))
# print("🔧 Waiting for debugger to attach on port 5678...")
# debugpy.wait_for_client()  # Blocks execution here

####################################################################################################

TRACKER_URL = "http://sp25-cs525-1201.cs.illinois.edu:8080"  # Replace with actual tracker IP
# TRACKER_URL = "http://10.0.0.130:8080"  # Replace with actual tracker IP

FILE_PATH = "tests/data"
JSON_LOG_FILE_PATH = "tests/summary.json"


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
        max_threads = max(1, multiprocessing.cpu_count() - 2)
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
                return "UNREACHABLE"

        max_latency = max(latencies)
        return "RESPONSIVE" if max_latency <= 1 else "BUSY"

    except requests.exceptions.Timeout:
        print("⏳ Server reachable but GET timed out — server likely busy.")
        return "BUSY"
    except Exception as e:
        print(f"❗ Error during GET request: {e}")
        return "BUSY"
    

def append_file_download_summary_to_json(metadata, total_time):
    for chunk in metadata.chunks:
        peers_tried_str = ", ".join(
                    [f"{peer_id}" for peer_id in chunk.peers_tried]
                )
        peers_failed_str = ", ".join(
                    [f"{peer_id}" for peer_id in chunk.peers_failed]
                )
    
    result_summary = {
        "file_name": metadata.file_name,
        "file_size": metadata.file_size,
        "total_download_time_sec": round(total_time, 2),
        "chunks": [
            {
                "chunk_name": chunk.chunk_name,
                "chunk_size": chunk.chunk_size,
                "downloaded": chunk.download_status,
                "peers_tried" : peers_tried_str,
                "peers_failed" : peers_failed_str,
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

