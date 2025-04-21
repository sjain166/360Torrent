import os
import networkx as nx

USER = os.environ["UI_USER"]
PASS = os.environ["UI_PASS"]

def create_network_delay(TARGET_VMs, net, local_net, regions):

    BASE_TC_BANDS = 3
    LOCAL_DELAY_TC_BANDS = 1
    N_TC_BANDS = len(net.edges()) + BASE_TC_BANDS + LOCAL_DELAY_TC_BANDS
    # Each pair of regions, maps to its own network band

    for vm in TARGET_VMs:
        c = vm["connection"]
        print(vm)
        c.sudo(f"tc qdisc replace dev ens33 root handle 1: prio bands {N_TC_BANDS}", password=PASS)

    # Initialize by putting all VMs at a local delay w.r.t to each other
    
    # I think this actually worked but it stacked it twice, one from each.
    # so currently is 20

    # Need to make sure this doesn't run the delay command bidirectional
    for delay_id, (src, dst, delay) in enumerate(net.edges(data=True), start = BASE_TC_BANDS+LOCAL_DELAY_TC_BANDS+1):
        for vm1 in regions[src]:
            c = vm1["connection"]
            # Set up the traffic band that corresponds to this delay
            c.sudo(f"tc qdisc add dev ens33 parent 1:{delay_id} handle {2+delay_id}: netem delay {delay["weight"]}ms", password=PASS)
            # Map all VMs in the dst_region to this traffic band
            for vm2 in regions[dst]:
                # tc can only filter based off of ip
                c.sudo(f"tc filter add dev ens33 parent 1:0  prio 1 u32 match ip dst {vm2["ip"]} flowid 1:{delay_id}", password=PASS)


def create_network_delay_from_generated_workload(TARGET_VMs, user_to_user_delays, N_REGIONS):

    BASE_TC_BANDS = 3

    N_TC_BANDS = int((N_REGIONS*(N_REGIONS-1))/2 + BASE_TC_BANDS)
    print(f" N_TC_BANDS {N_TC_BANDS}")
    # Each pair of regions, maps to its own network band

    for vm in TARGET_VMs:
        c = vm["connection"]
        print(vm)
        # c.sudo("tc qdisc del dev ens33 root", password=PASS) # Clear whatever qdisc is already present
        # c.sudo(f"tc qdisc add dev ens33 root handle 1: prio bands {N_TC_BANDS}", password=PASS) # Generate a new one
        c.sudo(f"tc qdisc replace dev ens33 root handle 1: prio bands {N_TC_BANDS}", password=PASS) # Generate a new one

    for delay_id, (src, dst, delay) in enumerate(user_to_user_delays, start = BASE_TC_BANDS+1):
        c = TARGET_VMs[src]["connection"]
        dst_ip = TARGET_VMs[dst]["ip"]

        print(c)
        print(delay_id)

        # Set up the traffic band that corresponds to this delay
        c.sudo(f"tc qdisc add dev ens33 parent 1:{delay_id} handle {2+delay_id}: netem delay {delay}ms", password=PASS)
        c.sudo(f"tc filter add dev ens33 parent 1:0  prio 1 u32 match ip dst {dst_ip} flowid 1:{delay_id}", password=PASS)