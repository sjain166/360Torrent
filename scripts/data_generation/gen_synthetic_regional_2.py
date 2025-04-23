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

print(exp.trace_name)


# NOTE: This path is from where your current path is in shell! not from where the file is.
DATA_DIR = f"../../data/final/{args.trace_name}_workload/"
try:
    print(f"{os.path.abspath(DATA_DIR)=}")
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError as e:
    print(e)

NET_FILE = DATA_DIR + "synthetic_regional_delay.csv"
CODE_FILE = DATA_DIR + "paste_delay.txt"
EVENT_FILE = DATA_DIR + "events.json"
USER_FILE = DATA_DIR + "users_per_region.csv"
FILESIZE_FILE = DATA_DIR + "filesizes.csv"
TRACE_INFO_FILE = DATA_DIR + "trace_info.json"
TIMELINE_FILE = DATA_DIR + "timeline.pkl"

N_CLIENTS = 19
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

users.insert(0, tracker) # Add tracker in for the sake of creating appropriate regional delays

### Generating regions and network conditions ###

# Define regions and their share of the userbase < 1
# regions = [["W", 0.3, [tracker]], ["N", 0.4, []], ["C", 0.2, []], ["F", 0.1, []]] # This should probably be a map...
regions = [["W", 0.25, [tracker]], ["N", 0.25, []], ["C", 0.25, []], ["F", 0.25, []]] # This should probably be a map...

# Define delays between regions
net = nx.Graph(data=True)
net.add_edge("W","N", weight=65)
net.add_edge("W","C", weight=31)
net.add_edge("W", "F", weight=79)
net.add_edge("N", "C", weight=62)
net.add_edge("N", "F", weight=34)
net.add_edge("C", "F", weight=63)

# 1. Map userids to regions (for simplicity, contiguous id users will be assigned the same region)
# 2. Mutates 'regions' and 'users' accordingly
# 3. Dumps computed regional delays to 'NET_FILE' - we can later read these to set up net_delay.py
define_regional_userbase_and_delay(regions, N_CLIENTS+1, net, NET_FILE, CODE_FILE, users)
exp.tracker_id = tracker["id"]
exp.tracker_region = tracker["region"]

try:
    # Write user regions to file
    with open(USER_FILE, 'w') as fs:
        for user in users:
            fs.write(f"{user['id']}, {user['region']}\n")
except Exception as e:
    print(f"Failed to write file: {e}")
    

users.pop(0) # Remove tracker after you're done writing user files and regional delay files


### Generating workload per user ###

# All timing units in ms

minute = 60000
EXPERIMENT_T = 30 * minute
exp.experiment_t_min = EXPERIMENT_T / minute
CHURN = True
exp.churn = CHURN

N_files_generated = 0

# - Generate client sessions from a Pareto distribution

# MIN_STAY_TIME = 1 * minute
# MEAN_STAY_TIME = 1 * minute
# MAX_STAY_TIME = EXPERIMENT_T
# MEAN_LEAVE_TIME = 1 * minute
# STD_LEAVE_TIME = 0 * minute


### Churn params

MIN_STAY_TIME = EXPERIMENT_T
MEAN_STAY_TIME = EXPERIMENT_T
MAX_STAY_TIME = EXPERIMENT_T
MEAN_LEAVE_TIME = 1 * minute
STD_LEAVE_TIME = 0 * minute

exp.min_stay_t_min = MIN_STAY_TIME / minute
exp.mean_stay_t_min = MEAN_STAY_TIME / minute
exp.mean_leave_t_min = MEAN_LEAVE_TIME / minute
exp.std_leave_t_min = STD_LEAVE_TIME / minute

#PARETO_ALPHA = 2.5 # 2.5 is very heavy tailed, i.e. a lot of sessions will fall far less than the mean
PARETO_ALPHA = 5
# PARETO_ALPHA = 50 # 50 is very tight, most sessions will fall at the mean
PARETO_K = MEAN_STAY_TIME * (PARETO_ALPHA - 1) / PARETO_ALPHA

exp.pareto_alpha = PARETO_ALPHA
exp.pareto_k = PARETO_K

JOIN_T_LIM = EXPERIMENT_T/6
exp.first_join_upper_limit_min = JOIN_T_LIM / minute


### Upload & Download params

UPLOAD_INTENSITY = 1/5 / minute
REQUEST_INTENSITY = 1 / minute
exp.upload_intensity_per_min = UPLOAD_INTENSITY * minute
exp.request_intensity_per_min = REQUEST_INTENSITY * minute

ZIPF_ALPHA = 1.01 # skewness param
ZIPF_SIZE = 1 # draw one element from the distribution at any time
ZIPF_N = 10**4 # Reasonable cap on zipf distribution draws for simulation experiments
exp.zipf_a = ZIPF_ALPHA
exp.zipf_size = ZIPF_SIZE
exp.zipf_n = ZIPF_N


# Assume all 20 clients join, in the first 4th of the experiment
INITIAL_JOIN_TIMES = np.random.uniform(0, JOIN_T_LIM, N_CLIENTS) # Assume initial arrival times are drawn at random from uniform distribution

for i, user in enumerate(users):
    if len(user["join_times"]) == 0: user["join_times"].append(INITIAL_JOIN_TIMES[i])

    # While the join / leave event is still in the bound of our experiment
    while user["join_times"][-1] < EXPERIMENT_T or user["leave_times"][-1] < EXPERIMENT_T:

        if len(user["join_times"]) > len(user["leave_times"]): # Currently "haven't left"
            current_join_time = user["join_times"][-1]
            next_leave_time = current_join_time + np.clip((np.random.pareto(PARETO_ALPHA)+1) * PARETO_K, MIN_STAY_TIME, MAX_STAY_TIME)
            # Determine how long we stay "in" from a pareto distribution
            user["leave_times"].append(next_leave_time)

        elif len(user["join_times"]) == len(user["leave_times"]): # Currently "left" the system
            current_leave_time = user["leave_times"][-1]
            next_join_time = current_leave_time + np.random.normal(MEAN_LEAVE_TIME, STD_LEAVE_TIME, 1)[0]
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


if args.dbg_print and False:
    print("\n Checking if Pareto session durations fall around the expected value ")

    for user in users:
        N_sessions_recorded = 0
        session_durations_sum = 0
        for t_join, t_leave in zip(user["join_times"], user["leave_times"]):
            N_sessions_recorded +=1
            session_durations_sum += t_leave - t_join

        print(f" User {user["id"]}, mean session duration = {session_durations_sum/N_sessions_recorded/minute} | specified mean: {MEAN_STAY_TIME/minute}, min: {MIN_STAY_TIME/minute}")


ALL_UPLOAD_TIMES = []

for user in users:

    for t_join, t_leave in zip(user["join_times"], user["leave_times"]):

        # print(f" Interval {(t_join, t_leave)=} T={t_leave-t_join}")

        total_uploads = UPLOAD_INTENSITY * (t_leave - t_join)
        uploads_in_interval = np.cumsum(np.random.exponential(1/UPLOAD_INTENSITY, int(total_uploads))) + t_join

        added_uploads = list(uploads_in_interval[ (t_join < uploads_in_interval) & (uploads_in_interval < t_leave)])
        # print(f" {added_uploads=}")
        user["upload_times"] += added_uploads

        total_requests = REQUEST_INTENSITY * (t_leave - t_join)
        requests_in_interval = np.cumsum(np.random.exponential(1/REQUEST_INTENSITY, int(total_requests))) + t_join
        added_requests = list(requests_in_interval[ (t_join < requests_in_interval) & (requests_in_interval < t_leave)])
        # print(f" {added_requests=}")
        user["request_times"] += added_requests

    ALL_UPLOAD_TIMES += user["upload_times"] # Build this array so that you can easily define an interval between arrival i and arrival i+1

ALL_UPLOAD_TIMES = sorted(ALL_UPLOAD_TIMES) # Sort by ascending upload times
ALL_UPLOAD_TIMES_idx = 0

N_files_generated = len(ALL_UPLOAD_TIMES)
exp.total_files_generated = N_files_generated


content_uploaded = []


for upload_time in ALL_UPLOAD_TIMES:

    user = None
    t_upload = upload_time
    for u in users:
        if upload_time in u["upload_times"]:
            user = u 

    last_upload_idx = len(content_uploaded)
    file_num = ALL_UPLOAD_TIMES_idx

    seeder_client_id = user["id"]
    seeder_client_region = user["region"]
    # popularity = np.random.zipf(ZIPF_ALPHA, ZIPF_SIZE)[0] # Generate 1 sample from a zipf(1) distribution
    # popularity = np.clip(popularity, 1, ZIPF_N) # Clip rank to fit within a finite interval - this lets us recover probabilities
    new_content = {
        "id": file_num,
        "t_upload": t_upload,
        "name": f"video{file_num}",
        "seeder": seeder_client_id,
        "seeder_region": seeder_client_region,
        "popularity": {region[0]: np.clip(np.random.zipf(ZIPF_ALPHA, ZIPF_SIZE)[0], 1, ZIPF_N) 
                       for region in regions} #Generate a unique popularity rank of this video, PER REGION
    }

    content_uploaded.append(new_content)
    ALL_UPLOAD_TIMES_idx += 1

    # Add this to the seeder client's list of events
    user["events"].append({
        "type":"upload",
        "time": t_upload,
        "content": new_content
    })

    users_excluding_seeder = [u for u in users if u["id"] != seeder_client_id]
    for r_user in users_excluding_seeder:
        # Maybe here, tweak the new_content passed in to only include the popularity for this user's region.
        roster_content = new_content.copy()
        roster_content["popularity"] = new_content["popularity"][r_user["region"]] 
        # User will select content from its roster solely based off of the popularity in THEIR region.
        # Roster content is what will be the json that appears in the users events.
        # i.e. each request stored at a user, will only display the local popularity of that video
        push_content_to_roster(r_user, roster_content)

    INTERVAL = [] # Define a window of requests that will run before the next content arrival


    # print(f"{ALL_UPLOAD_TIMES=}")
    # print(f"{t_upload=}")
    next_upload_time = 0
    for ut in ALL_UPLOAD_TIMES:
        if t_upload < ut: # The first upload time that is <= to our t_upload
            next_upload_time = ut
            break

    if next_upload_time < EXPERIMENT_T:
        INTERVAL = [t_upload, next_upload_time] # Window of time between this, and the next upload
    else:
        INTERVAL = [t_upload, EXPERIMENT_T]

    # Now run the next request for each user
    for r_user in users_excluding_seeder:
        # Get all of this users request times, that fall between this arrival and the next arrival
        # These will all select from the same content roster, so we should generate them all at once
        if r_user["last_request_index"] < len(r_user["request_times"]): # If this user has requests remaining it its schedule
            requests_to_generate = [ r for r in r_user["request_times"] if (INTERVAL[0] < r) and (r < INTERVAL[1])]
            # print(f" Arrival interval {INTERVAL}")
            # print(f" Requests to generate {requests_to_generate}")

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
                    # print(f" Content request generated at {t_req}")
                r_user["last_request_index"] += 1 # step forward to the next request timestamp


# Tracking number of files requested so trace doesn't go over VM storage limits
max_files_req_at_some_client = 0
mean_files_req_at_a_client = 0
for user in users:
    mean_files_req_at_a_client += len(user["request_times"])
    if len(user["request_times"]) > max_files_req_at_some_client:
        max_files_req_at_some_client = len(user["request_times"])
mean_files_req_at_a_client /= len(users)

exp.max_files_requested_to_a_client = max_files_req_at_some_client
exp.mean_files_requested_to_a_client = mean_files_req_at_a_client


global_events = []
time_outlier_events = 0
for user in users:
    for event in user["events"]:
        if (event["time"] <= EXPERIMENT_T):
            global_events.append({"user":user["id"], "event":event})
        else: time_outlier_events += 1
global_events = sorted(global_events, key=lambda e: e["event"]["time"])
print(f" \nCropped {time_outlier_events} out of { len(global_events) + time_outlier_events} total global events. ")




class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  # Handles int32, int64, etc.
            return int(obj)
        elif isinstance(obj, np.floating):  # Handles float32, float64
            return float(obj)
        elif isinstance(obj, np.ndarray):  # Handles numpy arrays
            return obj.tolist()
        return super().default(obj)
try:
    with open(EVENT_FILE, "w") as fs:
        json.dump(global_events, fs, indent=1, cls=NumpyEncoder)
except Exception as e:
    print(f"Failed to write file: {e}")


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

if args.dbg_print:
    file_saturation_times = []

    for file in content_uploaded:
        t_upload = file["t_upload"]
        t_last_request = t_upload

        for e in global_events:
            if e["event"]["type"] == 'request' or e["event"]["type"] == 'upload':
                if e["event"]["content"]["name"] == file["name"]:
                    t_last_request = e["event"]["time"]

        file_saturation_times.append(t_last_request-t_upload)
    
    file_saturation_times = np.array(file_saturation_times)
    print(f" Time before all peers download a file mean={np.mean(file_saturation_times)/minute}min, stdev={np.std(file_saturation_times)/minute}min")

with open(TRACE_INFO_FILE, 'w') as fs:
    json.dump(vars(exp), fs, indent=1)

# Plotting regional request patterns to verify users are requesting videos according to regional popularities


if args.dbg_print and False:
    test_files = ["video5", "video10"]

    print("\n Eyeballing regional popularity trends... ")
    for file in test_files:

        file_upload = []
        file_requests = []

        for event_ in global_events:
            event = event_["event"]
            if event['type'] == 'upload':
                if event['content']['name'] == file:
                    file_upload.append(event_)
            elif event['type'] == 'request':
                if event['content']['name'] == file:
                    file_requests.append(event_)

        print(file)
        for region, _, region_users in regions:
            regional_popularity = file_upload[0]["event"]["content"]["popularity"][region] # should only be of size 1
            upload_time = file_upload[0]["event"]["time"]
            print(f"File {file} seeded at t={int(upload_time)} with p={regional_popularity} in region {region}")

            # print all requests for this file that happened within this region
            for req in file_requests:
                # get region requested originated in by looking up that user's region.
                if req["user"] in region_users:
                    print(f"User {req['user']} request, at t={int(req['event']['time'])}, at p={req['event']['content']['popularity']}")

        print()


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
            elif event["type"] == "upload":
                # If seeding the content, future popularity is recorded as a global list
                event_labels.append(
                    f" User {user['id']}\n {event['type']}\n [{event['content']['name']}\n seeder {event['content']['seeder']} \n pop {event['content']['popularity']}] "
                    )
            else:
                # If requesting content popularity is a single value local to the user's region
                event_labels.append(
                    f" User {user['id']}\n {event['type']}\n [{event['content']['name']}\n seeder {event['content']['seeder']} \n pop {int(event['content']['popularity'])}] "
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