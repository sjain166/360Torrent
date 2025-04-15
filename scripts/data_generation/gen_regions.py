import math
import csv
import networkx as nx

# Map userids to regions
# for simplicity, contiguous id users will be assigned the same region
# Mutates 'regions' and 'users'
# Dumps computed regional delays to 'NET_FILE'
# Dumps code you paste into worker as 'CODE_DUMP' lol
def define_regional_userbase_and_delay(regions, N_CLIENTS, net, NET_FILE, CODE_FILE, users):

    lower = 0 # id=0 is reserved for the tracker! So assume the tracker is always in the first region
    for i in range(len(regions)):
        region, percent, _ = regions[i]
        upper = lower + percent

        client_range_for_region = list(range(math.floor(lower*N_CLIENTS), math.ceil(upper*N_CLIENTS), 1))
        regions[i][2] = client_range_for_region # Assign region its list of clients
        for client_id in client_range_for_region: # Assign each client its corresponding region
            users[client_id]["region"] = region

        lower = upper

    with open(CODE_FILE, 'w') as fs:
        region_net_definition_template = f"""
    regions = {{ "{regions[0][0]}": get_VMs_by_id({regions[0][2]}),
                "{regions[1][0]}": get_VMs_by_id({regions[1][2]}),
                "{regions[2][0]}": get_VMs_by_id({regions[2][2]}),
                "{regions[3][0]}": get_VMs_by_id({regions[3][2]}) }}

    # Define delays between regions
    net = nx.Graph(data=True)
    net.add_edge("W","N", weight={ net.get_edge_data('W','N')['weight'] })
    net.add_edge("W","C", weight={net.get_edge_data('W','C')['weight']})
    net.add_edge("W","F", weight={net.get_edge_data('W','F')['weight']})
    net.add_edge("N","C", weight={net.get_edge_data('N','C')['weight']})
    net.add_edge("N","F", weight={net.get_edge_data('N','F')['weight']})
    net.add_edge("C","F", weight={net.get_edge_data('C','F')['weight']})
            """

        fs.write(region_net_definition_template)



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