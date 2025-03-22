from fabric import Connection
import time
import sys
import os

from one_time_tasks import *
from recurring_tasks import *

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
        "address": f"sp25-cs525-12{i:02}.cs.illinois.edu",
        "connection": Connection(
            f"sp25-cs525-12{i:02}.cs.illinois.edu",
            user=USER,
            connect_kwargs={"password": PASS},
        ),
    }
    for i in range(15, 19)
]


def run_task_on_connection(c, task_func):
    task_func(c)


def run_task_on_VMs(target_VMs, task_func):
    for vm in target_VMs:
        print(f"Running task on {vm["id"]} : {vm["address"]}")
        run_task_on_connection(vm["connection"], task_func)
        print(f"Task completed")


# Example, on VMs 15-18:
#   Install kernel-modules-extra
#   Load sch_netem module
run_task_on_VMs(TARGET_VMS, install_kernel_modules_extra)
time.sleep(3 * CLI_DELAY)
run_task_on_VMs(TARGET_VMS, load_sch_netem)

# TODO: Automate 'tc' connection delay setup
