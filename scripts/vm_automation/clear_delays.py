from fabric import Connection
import time
import sys
import os

if not len(sys.argv) == 3:
    print("worker.py <your_username> <your_password>")
    exit()
# Temporarily store pass in os.environ, this gets wiped after script finishes execution
os.environ["UI_USER"] = sys.argv[1]
os.environ["UI_PASS"] = sys.argv[2]
USER = os.environ["UI_USER"]
PASS = os.environ["UI_PASS"]

CLI_DELAY = 1

TARGET_VMS = [
    {
        "id": i,
        "ip": None,
        "address": f"sp25-cs525-12{i:02}.cs.illinois.edu",
        "connection": Connection(
            f"sp25-cs525-12{i:02}.cs.illinois.edu",
            user=USER,
            connect_kwargs={"password": PASS},
        ),
    }
    for i in range(15, 21)
]

from worker import run_simple_task
from simple_tasks import remove_network_delay

run_simple_task(TARGET_VMS, remove_network_delay)