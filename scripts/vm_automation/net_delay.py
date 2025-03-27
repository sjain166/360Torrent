import os

USER = os.environ["UI_USER"]
PASS = os.environ["UI_PASS"]

def create_network_delay(TARGET_VMs, net, regions):
    BASE_TC_BANDS = 3
    N_TC_BANDS = len(net.edges()) + BASE_TC_BANDS
    # Each pair of regions, maps to its own network band

    for vm in TARGET_VMs:
        c = vm["connection"]
        c.sudo(f"tc qdisc add dev ens33 root handle 1: prio bands {N_TC_BANDS}", password=PASS)


    # Need to make sure this doesn't run the delay command bidirectional
    for delay_id, (src, dst, delay) in enumerate(net.edges(data=True), start = BASE_TC_BANDS+1):
        for vm1 in regions[src]:
            c = vm1["connection"]
            # Set up the traffic band that corresponds to this delay
            c.sudo(f"tc qdisc add dev ens33 parent 1:{delay_id} handle {2+delay_id}: netem delay {delay["weight"]}ms", password=PASS)
            # Map all VMs in the dst_region to this traffic band
            for vm2 in regions[dst]:
                # tc can only filter based off of ip
                c.sudo(f"tc filter add dev ens33 parent 1:0  prio 1 u32 match ip dst {vm2["ip"]} flowid 1:{delay_id}", password=PASS)
