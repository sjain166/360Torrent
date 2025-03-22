import socket
import multiprocessing

####################################################################################################

# import debugpy
# debugpy.listen(("localhost", 5678))
# print("🔧 Waiting for debugger to attach on port 5678...")
# debugpy.wait_for_client()  # Blocks execution here

####################################################################################################

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
