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
    regions = { "W": get_VMs_by_id([1,2,3,4,5]),
                "N": get_VMs_by_id([6,7,8,9,10]) ,
                "C": get_VMs_by_id([11,12,13,14,15]),
                "F": get_VMs_by_id([16,17,18,19,20])}

    # # Define delays between regions
    net = nx.Graph(data=True)
    net.add_edge("W","N", weight=100)
    net.add_edge("W","C", weight=35)
    net.add_edge("W", "F", weight=120)
    net.add_edge("N", "C", weight=120)
    net.add_edge("N", "F", weight = 35)
    net.add_edge("C", "F", weight=100)

    ## Reading from workload generator output example
    DELAY_FILE = "../../data/None_workload/synthetic_regional_delay.csv"

    create_network_delay(TARGET_VMS, net, regions)
    # net = nx.Graph(data=True)
    # with open(DELAY_FILE, 'r', newline="") as fs:
    #     reader = csv.reader(fs)
    #     data = [(int(row[0]), int(row[1]), int(row[2])) for row in reader]
    #     create_network_delay_from_generated_workload(TARGET_VMS, data, N_REGIONS)


    # Make sure to either run
    # run_simple_task(TARGET_VMS, remove_network_delay)
    # or
    # manually execute clear_delays.py
    # to remove the VM delays when you're done testing