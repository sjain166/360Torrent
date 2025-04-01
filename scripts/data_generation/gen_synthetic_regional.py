import networkx as nx
import csv
import numpy as np
import math
import json
import bisect
import matplotlib.pyplot as plt
import sys
import argparse

from gen_regions import *


DATA_DIR = "../../data/"
NET_FILE = DATA_DIR + "synthetic_regional_delay.csv"
USER_FILE = DATA_DIR + "\\user_schedules.csv"

parser = argparse.ArgumentParser(description="Workload generator")
parser.add_argument("--visualize", "-v", action="store_true")
parser.add_argument("--dbg_print", "-p", action="store_true")
args = parser.parse_args()

N_CLIENTS = 10

users = [{
    "id": client_id,
    "region": None,
    "events": [],
    "content_roster": [],
    "last_request_index": 0,
    "request_times": []
} for client_id in range(N_CLIENTS)]


### Generating regions and network conditions ###

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


### Generating workload per user ###

# All timing units in ms

minute = 60000 # TODO: I think events are being generated outside of the set interval
EXPERIMENT_T = minute
UPLOAD_INTENSITY = 4 / minute

# - Generate content arrival times from a poisson distribution

# Note: Poisson process will generate ON AVERAGE, TOTAL_UPLOADS per minute
# but that does not necessarily mean that in each minute interval, you will see 4 uploads
# what you actually see per minute will vary due to randomness, ex. you may get 1 or 0 events in one minute.
# 1/UPLOAD_INTENSITY is the mean inter-arrival time

TOTAL_UPLOADS = UPLOAD_INTENSITY * EXPERIMENT_T
UPLOAD_TIMES = np.cumsum(np.random.exponential(1/UPLOAD_INTENSITY, int(TOTAL_UPLOADS)))

# - Generate request arrival times per user from a poisson distribution

MEAN_REQ_INTENSITY = 2 / minute # TODO: Can vary this later to simulate clients with highly varying request rate
for i, user in enumerate(users):
    TOTAL_REQ = MEAN_REQ_INTENSITY * EXPERIMENT_T
    user_request_times = np.cumsum(np.random.exponential(1/MEAN_REQ_INTENSITY, int(TOTAL_REQ)))
    user["request_times"] = user_request_times


# Model file uploads and downloads

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
ZIPF_N = 10**4 # Reasonable cap on zipf distribution draws for simulation experiments

def zipf_rank_to_probability(rank):
    harmonic_sum = np.sum(1 / np.arange(1, ZIPF_N + 1) ** ZIPF_ALPHA)
    return (1 / rank**ZIPF_ALPHA) / harmonic_sum

def draw_content_from_roster(user):
    popularities = np.array([c["popularity"] for c in user["content_roster"]])

    probabilities = np.array([ zipf_rank_to_probability(p) for p in popularities] )
    probabilities /= np.sum(probabilities)
    drawn = np.random.choice(user["content_roster"], p=(probabilities))

    if args.dbg_print:
        print()
        print(f" Entering draw to user {user["id"]}")
        print(f" User {user["id"]} roster {user["content_roster"]}")
        print(f" Rank:Probability {list(zip(popularities, probabilities))}")
        print(f" User {user["id"]} draws {drawn}")

    user["content_roster"].remove(drawn)

    if len(user["content_roster"]) > 0:
        new_popularities = np.array([c["popularity"] for c in user["content_roster"]]) # Re-create popularities excluding our drawn object
        new_popularities = new_popularities * ZIPF_N / new_popularities.sum() # Normalize
        new_popularities = [int(p) for p in new_popularities] # Make sure popularity ranks are integers
        for c, p in enumerate(new_popularities):
            user["content_roster"][c]["popularity"] = p # Re-assign popularities to each file

    return drawn

def push_content_to_roster(user, new_content):

    if len(user["content_roster"]) == 0:
        user["content_roster"].append(new_content)
        return

    if args.dbg_print:
        print()
        print(f" Entering push to {user["id"]}")
        print(f" User {user["id"]} roster {user["content_roster"]}")
        print(f" Content {new_content}")

    roster_sorted_by_popularity = sorted(user["content_roster"], key=lambda c: c["popularity"]) # Sort list s.t. low ranks (more popular) are at the front

    old_popularities = np.array([c["popularity"] for c in roster_sorted_by_popularity])
    new_content_idx = bisect.bisect_left(old_popularities, new_content["popularity"]) # Index where the new_content's rank belongs in the sorted array
    popularities = np.insert(old_popularities, new_content_idx, new_content["popularity"])

    popularities = popularities * ZIPF_N / popularities.sum() # Normalize
    popularities = [int(p) for p in popularities] # Make sure ranks are ints

    if args.dbg_print:
        print(f" popularities pre-insert {old_popularities}")
        print(f" popularities post-insert {popularities}")

    roster_sorted_by_popularity.insert(new_content_idx, new_content) # Place new content at its proper index in the roster
    for c in range(len(roster_sorted_by_popularity)):
        roster_sorted_by_popularity[c]["popularity"] = popularities[c] # Map new popularities to content in roster

    user["content_roster"] = roster_sorted_by_popularity # Update content roster with new shifted and sorted roster


for i, t_arrive in enumerate(UPLOAD_TIMES):

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

    # Update each client's content roster
    # Exclude the seeder, they already have that content, so they won't be downloading it
    users_excluding_seeder = [user for user in users if user["id"] != seeder_client_id]
    for user in users_excluding_seeder:
        push_content_to_roster(user, new_content)
    
    arrivals_interval = [] # Define a window of requests that will run before the next content arrival
    if i+1 < len(UPLOAD_TIMES):
        arrivals_interval = [t_arrive, UPLOAD_TIMES[i+1]]
    else:
        arrivals_interval = [t_arrive, EXPERIMENT_T]
    
    # Now run the next request for each user
    for user in users_excluding_seeder:

        if user["last_request_index"] < len(user["request_times"]): # If this user has requests remaining it its schedule
            t_req = user["request_times"][user["last_request_index"]]

            # If our current request time falls in the window
            if arrivals_interval[0] < t_req and t_req < arrivals_interval[1]:

                req_content = draw_content_from_roster(user) # Use 'fetch-at-most-once' behavior to make a request

                # Add this request to this client's list of events
                user["events"].append({
                    "type":"request",
                    "time": t_req,
                    "content": req_content
                })
                
                user["last_request_index"] += 1 # step forward to the next request timestamp


# Timeline for debugging

if args.visualize:

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
    ax.set_xlim((0, EXPERIMENT_T))
    ax.set_xlabel('Time')
    ax.set_title(f'User Timeline')

plt.show()