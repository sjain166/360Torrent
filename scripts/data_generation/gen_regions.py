import math
import csv

# Map userids to regions
# for simplicity, contiguous id users will be assigned the same region
# Mutates 'regions' and 'users'
# Dumps computed regional delays to 'NET_FILE'
def define_regional_userbase_and_delay(regions, N_CLIENTS, net, NET_FILE, users):

    lower = 0 # id=0 is reserved for the tracker! So assume the tracker is always in the first region
    for i in range(len(regions)):
        region, percent, _ = regions[i]
        upper = lower + percent

        client_range_for_region = list(range(math.floor(lower*N_CLIENTS), math.ceil(upper*N_CLIENTS), 1))
        regions[i][2] = client_range_for_region # Assign region its list of clients
        for client_id in client_range_for_region: # Assign each client its corresponding region
            users[client_id]["region"] = region

        lower = upper


    def get_regionusers_by_string(region_str): return [r[2] for r in regions if r[0]==region_str][0]

    with open(NET_FILE, 'w', newline='') as csvfile:
        fieldnames = ['src', 'dst', 'rtt']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        for src, dst, delay in net.edges(data=True):

            src_users = get_regionusers_by_string(src)
            dst_users = get_regionusers_by_string(dst)

            for srcu in src_users:
                for dstu in dst_users:
                    writer.writerow({'src': srcu, 'dst': dstu, 'rtt': delay["weight"]})

    return users