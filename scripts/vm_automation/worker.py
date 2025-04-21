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
    for i in range(2, 21)
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


    ## Just paste this in from the trace paste.txt
    # Super janky but headache-free solution for setting up network delays
    # from a pre-generated trace
    regions = { "W": get_VMs_by_id([2,3,4,5,6]),
                "N": get_VMs_by_id([7,8,9,10,11]),
                "C": get_VMs_by_id([12,13,14,15,16]),
                "F": get_VMs_by_id([17, 18, 19, 20]) }

    # Define delays between regions
    regional = nx.Graph(data=True)
    regional.add_edge("W","N", weight=65)
    regional.add_edge("W","C", weight=31)
    regional.add_edge("W","F", weight=79)
    regional.add_edge("N","C", weight=62)
    regional.add_edge("N","F", weight=34)
    regional.add_edge("C","F", weight=63)

    net = nx.Graph(data=True)
    local_delay = 10

    BASE_TC_BANDS = 3
    tc_band_idx = BASE_TC_BANDS + 1
    delay_to_tc_band_idx = {} # Each unique delay, will map to its own tc band index

    for region, region_vms in regions.items():

        for src in region_vms:

            # For all local VMs, add an edge 10
            for dst in [ vm for vm in region_vms if not vm["id"] == src["id"]]:
                net.add_edge(src["id"], dst["id"], weight=local_delay)

                if local_delay not in delay_to_tc_band_idx:
                    delay_to_tc_band_idx[local_delay] = tc_band_idx
                    tc_band_idx += 1

            # For all VMs outside local, add the corresponding regional delay
            nonlocal_latencies = [e for e in regional.edges(region, data=True)]
            for src_region, dst_region, data in nonlocal_latencies:
                for nonlocal_vm in regions[dst_region]: # For each VM in this other region
                    net.add_edge(src["id"], nonlocal_vm["id"], weight = data["weight"])

                    if data["weight"] not in delay_to_tc_band_idx:
                        delay_to_tc_band_idx[data["weight"]] = tc_band_idx
                        tc_band_idx +=1
    

    print(f"{delay_to_tc_band_idx=}")

    N_TC_BANDS = 3 + len(delay_to_tc_band_idx.items()) + 1 # 3 base bands, plus one band per every unique delay
    for user in net.nodes:
        vm = get_VMs_by_id([user])[0]
        c = vm["connection"]
        print(vm)
        c.sudo(f"tc qdisc replace dev ens33 root handle 1: prio bands 16", password=PASS)

    # Can it not handle 10 specifically because of the hex thing?
    # so N_TC_BANDS is interpreted in decimal,
    # but the actual band is interpreted in hex
    # so if I want 10 hex (16 decimal) to be a valid band, I need to create 17 bands?

    handle = 5

    print(f"{delay_to_tc_band_idx=}")
    # Now going over each edge once
    for src, dst, data in net.edges(data=True):

        vm1 = get_VMs_by_id([src])[0]
        vm2 = get_VMs_by_id([dst])[0]
        delay = data["weight"]

        delay_id = delay_to_tc_band_idx[delay]
        print(f"src {src} {delay_id=}")
        if delay_id == 10: delay_id = 'a'

        c = vm1["connection"]
        c.sudo(f"tc qdisc replace dev ens33 parent 1:{delay_id} handle {handle}: netem delay {delay}ms", password=PASS)
        c.sudo(f"tc filter replace dev ens33 parent 1:0  prio 1 u32 match ip dst {vm2["ip"]} flowid 1:{delay_id}", password=PASS)

        handle +=1 
     