import networkx as nx
import csv
import numpy as np
import math
import json
import bisect
import matplotlib.pyplot as plt
import sys

from gen_regions import *


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

# 1. Map userids to regions (for simplicity, contiguous id users will be assigned the same region)
# 2. Mutates 'regions' and 'users' accordingly
# 3. Dumps computed regional delays to 'NET_FILE' - we can later read these to set up net_delay.py
define_regional_userbase_and_delay(regions, N_CLIENTS, net, NET_FILE, users)




# ! Now I need to generate events per user !


# These are all hard coded to "per_minute" because for a baby test I'm just trying to simulate one minute of data


# - Generate content arrival times from a poisson distribution


VISUALIZE = len(sys.argv) > 1 and sys.argv[1] == 'vis'

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

    print(f" User {user["id"]} roster {user["content_roster"]}")
    print(f" User {user["id"]} draws {drawn}")

    user["content_roster"].remove(drawn)

    if len(user["content_roster"]) > 0:

        # Now re-normalize ranks

        new_popularities = np.array([c["popularity"] for c in user["content_roster"]])
        # Normalize ranks with ranks
        # new_popularities = popularities / (old_total - drawn["popularity"])
        new_popularities = new_popularities * ZIPF_N / new_popularities.sum()
        new_popularities = [int(p) for p in new_popularities]

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

    print(f"Entering push to {user["id"]}")
    print(f" Roster: {user["content_roster"]} \ncontent : {new_content}")
    roster_sorted_by_popularity = sorted(user["content_roster"], key=lambda c: c["popularity"]) 
    # Sort list s.t. low ranks (more popular) are at the front

    # Lower ranks are inherently more popular, we sort in opposite order so that higher ranks (less popular) are to the left

    popularities = np.array([c["popularity"] for c in roster_sorted_by_popularity])
    print(f" popularities pre-insert {popularities}")
    # TODO: Shifting is going wrong somewhere

    # The way this is set up now, it is deleting content at the highest (least popular rank)
    # We want to insert the element at the bisection point
    # Shift current content down by one rank
    new_content_idx = bisect.bisect_left(popularities, new_content["popularity"]) # Index where the new_conent's rank belongs in the sorted array
    print(f" new content idx {new_content_idx}")
    # popularities = np.append(popularities, 0) # Leave a space at the end for content to be shifted to

    # if new_content_idx < popularities.shape[0]:
    #     popularities[new_content_idx-1:] = popularities[new_content_idx:] # Shift Zipf ranks up by one 
    #     print(f" popularities post shift {popularities}")
    # popularities[new_content_idx] = new_content["popularity"]

    popularities = np.insert(popularities, new_content_idx, new_content["popularity"])

    # Re-normalize s.t. probabilites sum to 1   

    popularities =popularities * ZIPF_N / popularities.sum() # re-normalize ranks using ranks
    popularities = [int(p) for p in popularities]

    print(f" popularities post-insert {popularities}")

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

    


for i, t_arrive in enumerate(content_arrival_times):

    file_num = i

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

    # Its like new content neve gets pushed to certain user's rosters...
    users_excluding_seeder = [user for user in users if user["id"] != seeder_client_id]
    # print(f" Seeded at {seeder_client_id}, pushing to {users_excluding_seeder}")
    # Update each client's content roster
    # Exclude the seeder, beause they won't be downloading that content, they already have it
    for user in users_excluding_seeder:
        push_content_to_roster(user, new_content)
    
    arrivals_interval = []
    if i+1 < len(content_arrival_times):
        arrivals_interval = [t_arrive, content_arrival_times[i+1]]
    else:
        arrivals_interval = [t_arrive, N_ELAPSED_EXPERIMENT_TIME]
    
    # Now run the next request for each user
    for user in users_excluding_seeder:

        if user["last_request_index"] < len(user["request_times"]):

            t_req = user["request_times"][user["last_request_index"]]

            # This should cover all requests between the first and the next arrival time...
            if arrivals_interval[0] < t_req and t_req < arrivals_interval[1]:

                req_content = draw_content_from_roster(user) # Only running once

                # Add this request to this client's list of events
                user["events"].append({
                    "type":"request",
                    "time": t_req,
                    "content": req_content
                })
                
                user["last_request_index"] += 1 # step forward to the next request


# TODO: Shouldn't be getting decimal popularity ever!
# Timeline for debugging

if VISUALIZE:

    fig, ax = plt.subplots(figsize=(10,2))

    # Print for debugging and timeline plotting
    for user in users:
        print(f" USER: {user["id"]}")
        print(user["events"])

        event_times = [event["time"] for event in user["events"]]
        event_labels = [
            f" User {user['id']}\n {event['type']}\n [{event["content"]["name"]}\n seeder {event["content"]["seeder"]} \n pop {int(event["content"]["popularity"])}] " 
            
            for event in user["events"]
            ]

        levels = []
        level = 0.3
        for i in range(len(event_times)):
            levels.append(level * math.ceil(np.random.uniform(-4,4)))


        event_to_color = {
            "upload": "yellow",
            "request":"blue",
            "join":"green",
            "exit":"red"
        }

        ax.vlines(event_times, 0, levels, color=[(event_to_color[e["type"]]) for e in user["events"]])
        ax.axhline(0, c="black")

        ax.plot(event_times, np.zeros_like(event_times), "ko", mfc="white")
        # Add labels for each event

        stagger_step = 0.1
        for time, level, label in zip(event_times, levels, event_labels):

            ax.annotate(label, xy=(time, level),
            xytext=(-3, np.sign(level)*3), textcoords="offset points",
                    verticalalignment="bottom" if level > 0 else "top",
                    weight="normal",
                    bbox=dict(boxstyle='square', pad=0, lw=0, fc=(1, 1, 1, 0.7))          
                        )

    # Format the plot
    ax.yaxis.set_visible(False)
    ax.spines[["left","top","right"]].set_visible(False)

    ax.set_ylim((-3,3))
    ax.set_xlim((0, N_ELAPSED_EXPERIMENT_TIME))
    ax.set_xlabel('Time')
    ax.set_title(f'User Timeline')

plt.show()