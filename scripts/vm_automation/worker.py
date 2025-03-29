from fabric import Connection
import time
import sys
import os
import re

import networkx as nx

if not len(sys.argv) == 3:
    print("worker.py <your_username> <your_password>")
    exit()
# Temporarily store pass in os.environ, this gets wiped after script finishes execution
os.environ["UI_USER"] = sys.argv[1]
os.environ["UI_PASS"] = sys.argv[2]

from simple_tasks import *
from net_delay import *


def run_simple_task(target_VMs, task_func):
    for vm in target_VMs:
        print(f"Running task on {vm["id"]} : {vm["address"]}")
        task_func(vm["connection"])
        print(f"Task completed")


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
    for i in range(2, 21)
]

def get_resolved_ip_addr(c, dns_address):
    result = c.sudo(f"host {dns_address}", password=PASS)
    print("! result !")
    print(result)

    ip_pattern = r'\d+\.\d+\.\d+\.\d+'
    match = re.search(ip_pattern, result.stdout)
    print (" match")
    print(match)

    if match:
        ip = match.group(0)
        return ip
    else:
        print("IP Address not found")
        return None

for vm in TARGET_VMS:
    vm["ip"] = get_resolved_ip_addr(vm["connection"], vm["address"])

if __name__ == "__main__":

    # Example, on VMs 15-18:
    #   Install kernel-modules-extra
    #   Load sch_netem module
    # run_simple_task(TARGET_VMS, install_kernel_modules_extra)

    time.sleep(3 * CLI_DELAY)
    run_simple_task(TARGET_VMS, load_sch_netem)

    # Example
    # Setting up a network delay on VMs 15-20

    # run_simple_task(TARGET_VMS, load_sch_netem)
    time.sleep(CLI_DELAY)

    # For easy mapping
    def get_VMs_by_id(ids): return [vm for vm in TARGET_VMS if vm['id'] in ids]
    
    # Map VMs to their region
    regions = { "W": get_VMs_by_id([2,3,4,5]),
                "N": get_VMs_by_id([6,7,8,9,10]) ,
                "C": get_VMs_by_id([11,12,13,14,15]),
                "F": get_VMs_by_id([16,17,18,19,20])}

    # Define delays between regions
    net = nx.Graph(data=True)
    net.add_edge("W","N", weight=100)
    net.add_edge("W","C", weight=35)
    net.add_edge("W", "F", weight=120)
    net.add_edge("N", "C", weight=120)
    net.add_edge("N", "F", weight = 35)
    net.add_edge("C", "F", weight=100)

    create_network_delay(TARGET_VMS, net, regions)

    # Make sure to either run
    # run_simple_task(TARGET_VMS, remove_network_delay)
    # or
    # manually execute clear_delays.py
    # to remove the VM delays when you're done testing
    
    # Checked the following ping times are correct by hand:
    # 20->19
    # 20->17
    # 17->20
    # 17->16
    # 20->15
    # 15->16
    # 15->17
    # 15->20