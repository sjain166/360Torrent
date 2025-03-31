import networkx as nx
import csv
import numpy as np
import math

import json
import bisect


DATA_DIR = "../../data/"
NET_FILE = DATA_DIR + "synthetic_regional_delay.csv"
USER_FILE = DATA_DIR + "\\user_schedules.csv"


N_CLIENTS = 10
N_ELAPSED_EXPERIMENT_TIME = 60000 # in ms



users = [{
    "id": client_id,
    "region": None,
    "events": [],
    "content_roster": [],
    "last_request_index": 0,
    "request_times": []
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


## TODO: is 1/intensity correct?
content_arrival_times = np.cumsum(np.random.exponential(1/content_arrival_intensity, int(N_TOTAL_CONTENT)))


# - Generate request arrival times per user from a poisson distribution

request_arrival_intensity_per_minute_per_user = 2 # for the duration of our entire experiment, how much content do we want our users to request?

content_request_times_per_user = np.empty((N_CLIENTS, 0)) # Each user has their individual request times defined from a poisson process
# Don't really need to modify this array, just going to store this on each user.

for i, user in enumerate(users):
    request_arrival_intensity = request_arrival_intensity_per_minute_per_user / 60000 # TODO: maybe set the total_number of requests per user up as a gaussian draw?
    N_TOTAL_REQ = request_arrival_intensity * N_ELAPSED_EXPERIMENT_TIME
    user_request_times = np.cumsum(np.random.exponential(1/request_arrival_intensity, int(N_TOTAL_REQ)))
    # content_request_times_per_user[i, :] = user_request_times
    user["request_times"] = user_request_times


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

ZIPF_ALPHA = 1.01 # skewness param
ZIPF_SIZE = 1 # draw one element from the distribution at any time
ZIPF_N = 10**4

def zipf_rank_to_probability(rank):
    harmonic_sum = np.sum(1 / np.arange(1, ZIPF_N + 1) ** ZIPF_ALPHA)
    return (1 / rank**ZIPF_ALPHA) / harmonic_sum

def zipf_probability_to_rank(prob):
    harmonic_sum = np.sum(1 / np.arange(1, ZIPF_N + 1) ** ZIPF_ALPHA)
    rank = (1 / (prob * harmonic_sum)) ** (1 / ZIPF_ALPHA)
    print(f"computed rank {rank}")
    # return int(round(rank)) #TODO: A problem somewhere here...
    return 1/prob

def draw_content_from_roster(user):
    popularities = np.array([c["popularity"] for c in user["content_roster"]])

    old_total = popularities.sum()


    probabilities = np.array([ zipf_rank_to_probability(p) for p in popularities] )
    probabilities /= np.sum(probabilities)
    drawn = np.random.choice(user["content_roster"], p=(probabilities))

    user["content_roster"].remove(drawn)

    if len(user["content_roster"]) > 0:

        # Now re-normalize ranks

        new_popularities = np.array([c["popularity"] for c in user["content_roster"]])
        # Normalize ranks with ranks
        # new_popularities = popularities / (old_total - drawn["popularity"])
        new_popularities = new_popularities * ZIPF_N / new_popularities.sum()

        print(new_popularities)

        # re-assign popularities to each file
        for c, p in enumerate(new_popularities):
            print(f"c {c} p {p} ")
            user["content_roster"][c]["popularity"] = p

    return drawn

def push_content_to_roster(user, new_content):

    if len(user["content_roster"]) == 0:
        user["content_roster"].append(new_content)
        return

    print("Entering push")
    print(f" Roster: {user["content_roster"]} content : {new_content}")
    roster_sorted_by_popularity = sorted(user["content_roster"], key=lambda c: c["popularity"], reverse=True) 
    # Lower ranks are inherently more popular, we sort in opposite order so that higher ranks (less popular) are to the left

    popularities = np.array([c["popularity"] for c in roster_sorted_by_popularity])
    old_total = popularities.sum()

    # The way this is set up now, it is deleting content at the highest (least popular rank)
    # We want to insert the element at the bisection point
    # Shift current content down by one rank
    new_content_idx = bisect.bisect_right(popularities, new_content["popularity"]) # Index where the new_conent's rank belongs in the sorted array

    popularities = np.insert(popularities, 0, 0)
    popularities[0:new_content_idx] = popularities[1:new_content_idx+1] # Shift Zipf ranks down by one i.e. popularities
    popularities[new_content_idx] = new_content["popularity"]
    print(f" popularities post shift {popularities}")
    # Re-normalize s.t. probabilites sum to 1   


    # Zipf_rank_to_probability is tweaking!
    # probabilities = np.array([ zipf_rank_to_probability(p) for p in popularities])
    # print(probabilities)
    # probabilities /= probabilities.sum()
    # print(f"probabilities post normalization {probabilities}")
    # popularities = [ zipf_probability_to_rank(p) for p in probabilities]
    # print(f"popularities converted by gpt code {popularities}") # So I think the ranks it gets back are <1, and then it runs int round, turning them int 0,1?

    popularities = popularities * ZIPF_N / popularities.sum() # re-normalize ranks using ranks

    roster_sorted_by_popularity.insert(new_content_idx, new_content) # Place new content at its proper index in the roster
    # Map new popularities to content in roster

    for c in range(len(roster_sorted_by_popularity)):
        roster_sorted_by_popularity[c]["popularity"] = popularities[c]

    user["content_roster"] = roster_sorted_by_popularity # Update content roster with new shifted and sorted roster
    print(" Exiting push ")
    print(user["content_roster"])


    # What does "shifting down all content of equal or lesser popularity by one zipf position" mean?
    # If we just insert and renormalize, then we won't be "shifting"
    # "shifting" probabilities of other content down is what represents that the new content is inherently more popular / interesting?
    # Oh I see, so shifting content is basically just assigning each piece of content the popularity of the next highest popular node

    


for file_num, t_arrive in enumerate(content_arrival_times):

    seeder_client_id = int(np.random.uniform(low=0, high=N_CLIENTS))
    seeder_client_reigon = users[seeder_client_id]["region"]

    popularity = np.random.zipf(ZIPF_ALPHA, ZIPF_SIZE)[0] # Generate 1 sample from a zipf(1) distribution
    popularity = np.clip(popularity, 0, ZIPF_N) # Clip rank to fit within a finite interval - this lets us recover probabilities

    new_content = {
        "id": file_num,
        "name": f"video{file_num}",
        "seeder": seeder_client_id,
        "seeder_region": seeder_client_reigon,
        "popularity": popularity #probability of being selected
    }

    content_arrived.append(new_content)

    # Add this to the seeder client's list of events
    seeder = users[seeder_client_id]
    seeder["events"].append({
        "type":"upload",
        "time": t_arrive,
        "content": new_content
    })

    users_excluding_seeder = [user for user in users if user != seeder]
    # Update each client's content roster
    # Exclude the seeder, beause they won't be downloading that content, they already have it
    for user in users_excluding_seeder:
        push_content_to_roster(user, new_content)
    
    # Now run the next request for each user
    for user in users_excluding_seeder:
        print(f" req times {user["request_times"]}")
        print(f" user last req idx {user["last_request_index"]}")

        if user["last_request_index"] < len(user["request_times"]):
            t_req = user["request_times"][user["last_request_index"]]

            if t_arrive < t_req:

                req_content = draw_content_from_roster(user)

                # Add this request to this client's list of events
                user["events"].append({
                    "type":"request",
                    "time": t_req,
                    "content": req_content
                })
                
                user["last_request_index"] += 1 # step forward to the next request


# Print for debugging
for user in users:
    print(f" USER: {user["id"]}")
    print(user["events"])