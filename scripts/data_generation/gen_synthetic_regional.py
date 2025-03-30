import networkx as nx
import csv
import numpy as np
import math

import json


DATA_DIR = "../../data/"
NET_FILE = DATA_DIR + "synthetic_regional_delay.csv"
USER_FILE = DATA_DIR + "\\user_schedules.csv"


N_CLIENTS = 20
N_ELAPSED_EXPERIMENT_TIME = 60000 # in ms



users = [{
    "id": client_id,
    "region": None,
    "events": [],
    "content_roster": None,
    "last_request_index": 0
} for client_id in range(N_CLIENTS)]



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

# Define regions and their share of the userbase < 1
regions = [["W", 0.3, []], ["N", 0.4, []], ["C", 0.2, []], ["F", 0.1, []]] # This should probably be a map...

# Define delays between regions
net = nx.Graph(data=True)
net.add_edge("W","N", weight=100)
net.add_edge("W","C", weight=35)
net.add_edge("W", "F", weight=120)
net.add_edge("N", "C", weight=120)
net.add_edge("N", "F", weight = 35)
net.add_edge("C", "F", weight=100)


define_regional_userbase_and_delay(regions, N_CLIENTS, net, NET_FILE, users)


# ! Now I need to generate events per user !


# These are all hard coded to "per_minute" because for a baby test I'm just trying to simulate one minute of data


# - Generate content arrival times from a poisson distribution
content_arrival_intensity_per_minute = 4 # "4 videos arrive per minute on average"
content_arrival_intensity = content_arrival_intensity_per_minute / 60000 # Content arrived per millisecond

N_TOTAL_CONTENT = content_arrival_intensity * N_ELAPSED_EXPERIMENT_TIME # ex. 2 vids per minute, 8 minute simulation, should be 16 total videos - but this is scaled in ms

content_arrival_times = np.cumsum(np.random.exponential(1/content_arrival_intensity, N_TOTAL_CONTENT))


# - Generate request arrival times per user from a poisson distribution

request_arrival_intensity_per_minute_per_user = 1 # for the duration of our entire experiment, how much content do we want our users to request?

content_request_times_per_user = np.empty((N_CLIENTS, 0)) # Each user has their individual request times defined from a poisson process
for user in users:
    request_arrival_intensity = request_arrival_intensity_per_minute_per_user / 60000 # TODO: maybe set the total_number of requests per user up as a gaussian draw?
    user_request_times = np.cumsum(np.random.exponential(1/request_arrival_intensity, N_TOTAL_CONTENT))
    content_request_times_per_user[user, :] = user_request_times


# ! Now that we have defined upload and download times, we need to model file upload and download !

# 'content' json array of form
# {
#     "id": 1,
#     "name": "video1",
#     "seeder": [client_id],
#     "seeder_region": [region],
#     "popularity": 5
# }
content_arrived = []


def draw_content_from_roster(user):
    probabilities = map(user["content_roster"], lambda x: x["popularity"])

    drawn = np.random.choice(user["content_roster"], p=probabilities)
    user["content_roster"].remove(drawn)

    new_probabilities = map(user["content_roster"], lambda x: x["popularity"])
    new_probabilities /= new_probabilities.sum()

    # re-assign selection probabilities to each file
    for c, p in enumerate(new_probabilities):
        user["content_roster"][c] = p

    return drawn

def push_content_to_roster(user, content):
    probabilities = map(user["content_roster"], lambda x: x["popularity"])

    # What does "shifting down all content of equal or lesser popularity by one zipf position" mean?
    # If we just insert and renormalize, then we won't be "shifting"
    # "shifting" probabilities of other content down is what represents that the new content is inherently more popular / interesting?
    # Oh I see, so shifting content is basically just assigning each piece of content the popularity of the next highest popular node

    # TODO
    return 

    


for file_num, t_arrive in enumerate(content_arrival_times):

    seeder_client_id = np.random.uniform(range(N_CLIENTS))
    seeder_client_reigon = users[seeder_client_id]

    popularity = np.random.zipf(1, 1.0) # Generate 1 sample from a zipf(1) distribution

    content_arrived.append({
        "id": file_num,
        "name": f"video{file_num}",
        "seeder": seeder_client_id,
        "seeder_region": seeder_client_reigon,
        "popularity": popularity #probability of being selected
    })

    # Update each client's content roster
    for user in users:
        if file_num < user["last_request_index"]:

            # Need to write a method "Push content to user" that handles the zipf swap they talk about
            # Then at the user's next timestep they'll pull the data from their content roster
            user["content_roster"] 
    
    #

    

    # Note: set up a conditional so that files can only be requested after they are uploaded, ignore any timestamps before the first file upload.
