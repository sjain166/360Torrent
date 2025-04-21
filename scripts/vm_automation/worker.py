from fabric import Connection
import time
import sys
import os
import re
import csv

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
        "region": None,
        "address": f"sp25-cs525-12{i:02}.cs.illinois.edu",
        "connection": Connection(
            f"sp25-cs525-12{i:02}.cs.illinois.edu",
            user=USER,
            connect_kwargs={"password": PASS},
        ),
    }
    for i in range(15, 21)
]


# To generate TARGET_VMS from generated workload
# TARGET_VMS = []
# REGIONS = []

# USER_REGION_FILE = "../../data/None_workload/users_per_region.csv"
# with open(USER_REGION_FILE, 'r', newline="") as fs:
#     reader = csv.reader(fs)
#     data = [(int(row[0]), row[1].strip()) for row in reader]
#     for id, region in data:
#         if not region in REGIONS: REGIONS.append(region)

#         TARGET_VMS.append(
#             {
#             "id": id,
#             "ip": None,
#             "region": region,
#             "address": f"sp25-cs525-12{id:02}.cs.illinois.edu",
#             "connection": Connection(
#                 f"sp25-cs525-12{id:02}.cs.illinois.edu",
#                 user=USER,
#                 connect_kwargs={"password": PASS},
#             ),
#         }
#         )

# print(f" REGIONS: {REGIONS}")
# N_REGIONS = len(REGIONS)


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

    # run_simple_task([TARGET_VMS[0]], install_kernel_modules_extra)

    run_simple_task(TARGET_VMS, load_sch_netem)
    # time.sleep(CLI_DELAY)
    

    ## Hard coded example
    # For easy mapping
    def get_VMs_by_id(ids): return [vm for vm in TARGET_VMS if vm['id'] in ids]
    # # Map VMs to their region


    regions = { 
                "N": get_VMs_by_id([15]),
                "C": get_VMs_by_id([16, 17]),
                "F": get_VMs_by_id([18, 19]) }
    
    
    # Define delays between regions
    net = nx.Graph(data=True)
    net.add_edge("N","C", weight=62)
    net.add_edge("N","F", weight=34)
    net.add_edge("C","F", weight=63)

    # Define the local delay
    local_net = nx.Graph(data=True)
    local_delay = 10
    for vm1 in TARGET_VMS:
        for vm2 in [vm for vm in TARGET_VMS if not vm["id"] == vm1["id"]]:
            local_net.add_edge(vm1["id"], vm2["id"], weight=local_delay)


    BASE_TC_BANDS = 3
    LOCAL_DELAY_TC_BANDS = 1
    N_TC_BANDS = len(net.edges()) + BASE_TC_BANDS + LOCAL_DELAY_TC_BANDS
    # Each pair of regions, maps to its own network band

    for vm in TARGET_VMS:
        c = vm["connection"]
        print(vm)
        c.sudo(f"tc qdisc replace dev ens33 root handle 1: prio bands {N_TC_BANDS}", password=PASS)

    handle_idx = 5


    for delay_id, (src, dst, delay) in enumerate(net.edges(data=True), start = BASE_TC_BANDS+LOCAL_DELAY_TC_BANDS+1):
        for vm1 in regions[src]:
            c = vm1["connection"]
            # Set up the traffic band that corresponds to this delay
            print(vm1)
            print(f"tc qdisc add dev ens33 parent 1:{delay_id} handle {handle_idx}: netem delay {delay["weight"]}ms")
            c.sudo(f"tc qdisc replace dev ens33 parent 1:{delay_id} handle {handle_idx}: netem delay {delay["weight"]}ms", password=PASS)
            handle_idx += 1
            # Map all VMs in the dst_region to this traffic band
            for vm2 in regions[dst]:
                c.sudo(f"tc filter replace dev ens33 parent 1:0  prio 1 u32 match ip dst {vm2["ip"]} flowid 1:{delay_id}", password=PASS)

    
    # When you have two filters for the same ip, the lower handle one wins.
    # So we need to set the regional delays at a lower handle (higher priority)
    for id1, id2, delay in local_net.edges(data=True):
        vm1 = get_VMs_by_id([id1])[0]
        vm2 = get_VMs_by_id([id2])[0]
        c = vm1["connection"]
        delay_id = BASE_TC_BANDS+LOCAL_DELAY_TC_BANDS

        print(vm1)
        print(f"tc qdisc add dev ens33 parent 1:{delay_id} handle {handle_idx}: netem delay {local_delay}ms")
        c.sudo(f"tc qdisc replace dev ens33 parent 1:{delay_id} handle {handle_idx}: netem delay {local_delay}ms", password=PASS)
        print(f"tc filter add dev ens33 parent 1:0  prio 1 u32 match ip dst {vm2["ip"]} flowid 1:{delay_id}")
        c.sudo(f"tc filter add dev ens33 parent 1:0  prio 1 u32 match ip dst {vm2["ip"]} flowid 1:{delay_id}", password=PASS)

        handle_idx +=1