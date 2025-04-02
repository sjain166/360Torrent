import networkx as nx
import csv
import numpy as np
import math
import json
import bisect
import matplotlib.pyplot as plt
import pickle
import sys
import os
import argparse

from types import SimpleNamespace

from gen_regions import *
from gen_utils import *

# Usage args gen_synthetic_regional -v -p -t <trace_name>
# Need to specify <trace_name>

parser = argparse.ArgumentParser(description="Workload generator")
parser.add_argument("--trace_name" , "-t", type=str)
parser.add_argument("--visualize", "-v", action="store_true")
parser.add_argument("--dbg_print", "-p", action="store_true")
args = parser.parse_args()

exp = SimpleNamespace() # Track constants used to generate this trace
exp.trace_name = args.trace_name

DATA_DIR = f"../../data/{args.trace_name}_workload/"
os.makedirs(DATA_DIR, exist_ok=True)
NET_FILE = DATA_DIR + "synthetic_regional_delay.csv"
EVENT_FILE = DATA_DIR + "events.json"
USER_FILE = DATA_DIR + "users_per_region.csv"
FILESIZE_FILE = DATA_DIR + "filesizes.csv"
TRACE_INFO_FILE = DATA_DIR + "trace_info.json"
TIMELINE_FILE = DATA_DIR + "timeline.pkl"

N_CLIENTS = 9
exp.n_clients = N_CLIENTS

users = [{
    "id": client_id,
    "region": None,
    "events": [],
    "content_roster": [],
    "last_request_index": 0,
    "upload_times": [],
    "request_times": [],
    "join_times": [],
    "leave_times": [],
} for client_id in range(2, 2+N_CLIENTS)] # Reserve client_id 1 for tracker

tracker = {
    "id":1,
    "region": None
}

exp.tracker_id = tracker["id"]
exp.tracker_region = tracker["region"]

users.insert(0, tracker) # Add tracker in for the sake of creating appropriate regional delays

### Generating regions and network conditions ###

# Define regions and their share of the userbase < 1
regions = [["W", 0.3, [tracker]], ["N", 0.4, []], ["C", 0.2, []], ["F", 0.1, []]] # This should probably be a map...

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
define_regional_userbase_and_delay(regions, N_CLIENTS+1, net, NET_FILE, users)

# Write user regions to file
with open(USER_FILE, 'w') as fs:
    for user in users:
        fs.write(f"{user['id']}, {user['region']}\n")


users.pop(0) # Remove tracker after you're done writing user files and regional delay files


### Generating workload per user ###

# All timing units in ms

minute = 60000 # TODO: I think events are being generated outside of the set interval
EXPERIMENT_T = 10 * minute
exp.experiment_t = EXPERIMENT_T
CHURN = True
exp.churn = CHURN

N_files_generated = 0

if CHURN:

    # - Generate client arrival/ times from a poisson distribution

    # These variables roughly correspond to "churn rate"
    STAY_VS_LEAVE_RATIO = 1.5 / 1 # clients spend a bit more time in the system than outside of it.
    INTERVAL_T = 4 * minute
    exp.stay_v_leave_ratio = STAY_VS_LEAVE_RATIO
    exp.interval_t = INTERVAL_T

    # Assume all 20 clients join, in the first 4th of the experiment
    INITIAL_JOIN_TIMES = np.random.uniform(0, EXPERIMENT_T/4, N_CLIENTS) # Assume initial arrival times are drawn at random from uniform distribution

    for i, user in enumerate(users):
        if len(user["join_times"]) == 0: user["join_times"].append(INITIAL_JOIN_TIMES[i])

        # While the join / leave event is still in the bound of our experiment
        while user["join_times"][-1] < EXPERIMENT_T or user["leave_times"][-1] < EXPERIMENT_T:

            if len(user["join_times"]) > len(user["leave_times"]): # Currently "haven't left"
                current_join_time = user["join_times"][-1]
                mean_stay_time = STAY_VS_LEAVE_RATIO * INTERVAL_T
                next_leave_time = current_join_time + np.random.normal(mean_stay_time, INTERVAL_T/4, 1)[0]
                # Determine how long we stay "in" from a gaussian
                user["leave_times"].append(next_leave_time)

            elif len(user["join_times"]) == len(user["leave_times"]): # Currently "left" the system
                current_leave_time = user["leave_times"][-1]
                mean_leave_time = INTERVAL_T
                next_join_time = current_leave_time + np.random.normal(mean_leave_time, INTERVAL_T/4, 1)[0]
                # Determine how long we stay "out" from a gaussian
                user["join_times"].append(next_join_time)

        if args.dbg_print:
            print()
            print(f"User {user['id']}")
            print(f" Join times: {user['join_times']}")
            print(f" Leave times: {user['leave_times']}")

        # Add join and leave times as events, they don't have to be sorted now, 
        # they'll get sorted later before file writing anyways
        for t_join, t_leave in zip(user["join_times"], user["leave_times"]):
            user["events"].append({
                "type":"join",
                "time": t_join,
                "content": None
            })
            user["events"].append({
                "type":"leave",
                "time": t_leave,
                "content": None
            })

    # Important NOTE: Here, I generate one Poisson process for reqests and one for uploads, 
    # for the duration of an interval where a client is IN the system

    UPLOAD_INTENSITY = 1 / minute
    REQUEST_INTENSITY = 2 / minute
    exp.upload_intensity = UPLOAD_INTENSITY
    exp.request_intensity = REQUEST_INTENSITY

    ALL_UPLOAD_TIMES = []

    for user in users:
        for t_join, t_leave in zip(user["join_times"], user["leave_times"]):

            total_uploads = UPLOAD_INTENSITY * (t_leave - t_join)
            uploads_in_interval = np.cumsum(np.random.exponential(1/UPLOAD_INTENSITY, int(total_uploads)))
            user["upload_times"] += list(uploads_in_interval[ (t_join < uploads_in_interval) & (uploads_in_interval < t_leave)])

            total_requests = REQUEST_INTENSITY * (t_leave - t_join)
            requests_in_interval = np.cumsum(np.random.exponential(1/REQUEST_INTENSITY, int(total_requests)))
            user["request_times"] += list(requests_in_interval[ (t_join < requests_in_interval) & (requests_in_interval < t_leave)])

        ALL_UPLOAD_TIMES += user["upload_times"] # Build this array so that you can easily define an interval between arrival i and arrival i+1

    ALL_UPLOAD_TIMES = sorted(ALL_UPLOAD_TIMES) # Sort by ascending upload times
    N_files_generated = len(ALL_UPLOAD_TIMES)
    exp.n_files = N_files_generated
    content_uploaded = []
    
    ZIPF_ALPHA = 1.01 # skewness param
    ZIPF_SIZE = 1 # draw one element from the distribution at any time
    ZIPF_N = 10**4 # Reasonable cap on zipf distribution draws for simulation experiments
    exp.zipf_a = ZIPF_ALPHA
    exp.zipf_size = ZIPF_SIZE
    exp.zipf_n = ZIPF_N

    for user in users:

        for t_upload in user["upload_times"]:

            last_upload_idx = len(content_uploaded)
            file_num = last_upload_idx

            seeder_client_id = user["id"]
            seeder_client_reigon = user["region"]
            popularity = np.random.zipf(ZIPF_ALPHA, ZIPF_SIZE)[0] # Generate 1 sample from a zipf(1) distribution
            popularity = np.clip(popularity, 1, ZIPF_N) # Clip rank to fit within a finite interval - this lets us recover probabilities
            new_content = {
                "id": file_num,
                "name": f"video{file_num}",
                "seeder": seeder_client_id,
                "seeder_region": seeder_client_reigon,
                "popularity": popularity #probability of being selected
            }

            content_uploaded.append(new_content)

            # Add this to the seeder client's list of events
            user["events"].append({
                "type":"upload",
                "time": t_upload,
                "content": new_content
            })

            users_excluding_seeder = [u for u in users if u["id"] != seeder_client_id]
            for r_user in users_excluding_seeder:
                push_content_to_roster(r_user, new_content)

            INTERVAL = [] # Define a window of requests that will run before the next content arrival
            if last_upload_idx+1 < len(ALL_UPLOAD_TIMES):
                INTERVAL = ALL_UPLOAD_TIMES[last_upload_idx : last_upload_idx+2] # Window of time between this, and the next upload
            else:
                INTERVAL = [t_upload, EXPERIMENT_T]

            # Now run the next request for each user
            for r_user in users_excluding_seeder:
                # Get all of this users request times, that fall between this arrival and the next arrival
                # These will all select from the same content roster, so we should generate them all at once
                if r_user["last_request_index"] < len(r_user["request_times"]): # If this user has requests remaining it its schedule
                    requests_to_generate = [ r for r in r_user["request_times"] if (INTERVAL[0] < r) and (r < INTERVAL[1])]
                    for t_req in requests_to_generate:
                        req_content = draw_content_from_roster(r_user) # Use 'fetch-at-most-once' behavior to make a request
                        # req_content can be None when there is no content that the user hasn't downloaded
                        if req_content != None:
                            # Add this request to this client's list of events
                            r_user["events"].append({
                                "type":"request",
                                "time": t_req,
                                "content": req_content
                            })
                        r_user["last_request_index"] += 1 # step forward to the next request timestamp

              
else: # NOTE: NO CHURN present

    # Important NOTE: Here I do not generate a upload poisson process per user. So the amount of uploads does NOT scale with N_CLIENTS here

    # - Generate content arrival times from a poisson distribution

    # Note: Poisson process will generate ON AVERAGE, TOTAL_UPLOADS per minute
    # but that does not necessarily mean that in each minute interval, you will see 4 uploads
    # what you actually see per minute will vary due to randomness, ex. you may get 1 or 0 events in one minute.
    # 1/UPLOAD_INTENSITY is the mean inter-arrival time

    UPLOAD_INTENSITY = 1 / minute
    TOTAL_UPLOADS = UPLOAD_INTENSITY * EXPERIMENT_T
    UPLOAD_TIMES = np.cumsum(np.random.exponential(1/UPLOAD_INTENSITY, int(TOTAL_UPLOADS)))
    exp.upload_intensity = UPLOAD_INTENSITY

    # - Generate request arrival times per user from a poisson distribution

    MEAN_REQ_INTENSITY = 2 / minute # TODO: Can vary this later to simulate clients with highly varying request rate
    for i, user in enumerate(users):
        TOTAL_REQ = MEAN_REQ_INTENSITY * EXPERIMENT_T
        user_request_times = np.cumsum(np.random.exponential(1/MEAN_REQ_INTENSITY, int(TOTAL_REQ)))
        user["request_times"] = user_request_times
    exp.request_intensity = MEAN_REQ_INTENSITY

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
    exp.zipf_a = ZIPF_ALPHA
    exp.zipf_size = ZIPF_SIZE
    exp.zipf_n = ZIPF_N

    for i, t_arrive in enumerate(UPLOAD_TIMES): # BAD NAMING, "t_arrive" should really be "t_upload"

        file_num = i

        seeder_client_id = int(np.random.uniform(low=0, high=N_CLIENTS))
        users["upload_times"].append(t_arrive)
        seeder_client_reigon = users[seeder_client_id]["region"]
        popularity = np.random.zipf(ZIPF_ALPHA, ZIPF_SIZE)[0] # Generate 1 sample from a zipf(1) distribution
        popularity = np.clip(popularity, 1, ZIPF_N) # Clip rank to fit within a finite interval - this lets us recover probabilities
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

                # Get all of this users request times, that fall between this arrival and the next arrival
                # These will all select from the same content roster, so we should generate them all at once
                requests_to_generate = user["request_times"][ (arrivals_interval[0] < user["request_times"]) & (user["request_times"] < arrivals_interval[1])]

                for t_req in requests_to_generate:

                    req_content = draw_content_from_roster(user) # Use 'fetch-at-most-once' behavior to make a request
                    # req_content can be None when there is no content that the user hasn't downloaded

                    if req_content != None:
                        # Add this request to this client's list of events
                        user["events"].append({
                            "type":"request",
                            "time": t_req,
                            "content": req_content
                        })
                    
                    user["last_request_index"] += 1 # step forward to the next request timestamp
    
    N_files_generated = len(content_arrived)
    exp.n_files = N_files_generated


global_events = []
for user in users:
    for event in user["events"]:
        global_events.append({"user":user["id"], "event":event})
global_events = sorted(global_events, key=lambda e: e["event"]["time"])



class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  # Handles int32, int64, etc.
            return int(obj)
        elif isinstance(obj, np.floating):  # Handles float32, float64
            return float(obj)
        elif isinstance(obj, np.ndarray):  # Handles numpy arrays
            return obj.tolist()
        return super().default(obj)
with open(EVENT_FILE, "w") as fs:
    json.dump(global_events, fs, indent=1, cls=NumpyEncoder)

# Testing churn. Verify that no user requests or downloads content outside of when they are "in" the system

if args.dbg_print:
    for user in users:
        joined_intervals = list(zip(user["join_times"], user["leave_times"]))
        for event in user["events"]:
            correct_event = False
            for t_join, t_leave in joined_intervals:
                correct_event = (t_join <= event["time"] <= t_leave) or correct_event # an event is correct, if it falls in at least one valid time interval
            if not correct_event: 
                print(f" User {user["id"]}, {t_join=}, {t_leave=}, INCORRECT EVENT AT {event["time"]}")


# Timeline for debugging

if args.visualize:

    fig, ax = plt.subplots(figsize=(10,2))

    # Print for debugging and timeline plotting
    for user in users:

        event_times = [event["time"] for event in user["events"]]
        event_labels = []

        for event in user["events"]:
            if event["type"] == "join" or event["type"] == "leave":
                event_labels.append(
                    f" User {user['id']}\n {event['type']} "
                    )
            else:
                event_labels.append(
                    f" User {user['id']}\n {event['type']}\n [{event["content"]["name"]}\n seeder {event["content"]["seeder"]} \n pop {int(event["content"]["popularity"])}] "
                    )
            
            

        levels = []
        level = 0.3
        for i in range(len(event_times)):
            levels.append(level * math.ceil(np.random.uniform(-4,4)))


        event_to_color = {
            "upload": "yellow",
            "request":"blue",
            "join":"green",
            "leave":"red"
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

    with open(TIMELINE_FILE, 'wb') as fs: pickle.dump(fig,fs)
    plt.show()

with open(TRACE_INFO_FILE, 'w') as fs:
    json.dump(vars(exp), fs, indent=1)