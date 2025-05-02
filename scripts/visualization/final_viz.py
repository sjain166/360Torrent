import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D

from dataclasses import dataclass
from scipy.stats import norm
from sklearn.mixture import GaussianMixture


import os
import json

TRACE_NAMES = ['light1', 'med1', 'heavy1', 'light_churn1', 'heavy_churn1']
DISPLAY_TRACE_NAMES = ["Light Traffic", "Medium Traffic", "Heavy Traffic", "Medium Traffic, Light Churn", "Medium Traffic, Heavy Churn"]


@dataclass
class Algorithm:
    latencies_per_region: dict
    avg_latency: np.array # average latencies over all video, on its nth regional re-download
    stdev_latency: np.array
    downloads_failed: list
    latency_matrix: list

@dataclass
class TraceData:
    name: str
    display_name: str
    baseline: Algorithm
    solution: Algorithm


DATA_DIR = "C:\\Users\\soula\\OneDrive\\Desktop\\Final"
EVENTS_DIR = "C:\\Users\\soula\\OneDrive\\Desktop\\Programming\\CS525\\360Torrent\\data\\final"

BASE_NAME = "BitTorrent"
SOL_NAME = "360Torrent"

regions_to_vms = { 
            "W": [f"vm{i:02d}" for i in [1,2,3,4,5]],
            "N": [f"vm{i:02d}" for i in [6,7,8,9,10]] ,
            "C": [f"vm{i:02d}" for i in [11,12,13,14,15]],
            "F": [f"vm{i:02d}" for i in [16,17,18,19,20]]
            }
def vm_to_region(vm): 
    res = [ r for r, arr in regions_to_vms.items() if vm in arr]
    return res[0]

def recover_timestamp(vmname, video, events_data):
    # Given the trace, vmname, and video name
    # recover the time it was downloaded at
    for d in events_data:
        if d["user"] == int(vmname[2:]):
            if not d["event"]["content"] == None:
                if d["event"]["content"]["name"] == video:
                    return d["event"]["time"]
                
def recover_popularity_for_region(video, region, events_data):
    # Recover the original popularity that a video was seeded at in its region

    print(f" {video=} { region=}")
    for d in events_data:
        if d["event"]["type"] == "upload":
            if str(d["event"]["content"]["name"]) == video:
                return d["event"]["content"]["popularity"][region]


N_DOWNLOADS = 5 # max number of downloads per region
POPULARITY_FILTER = False
POPULARITY_THRESHOLD = 5000

### Data Loader ###
all_data = []
for trial_idx, trace_name in enumerate(TRACE_NAMES):

    data = TraceData(trace_name, DISPLAY_TRACE_NAMES[trial_idx],
                     Algorithm({"W": {}, "F": {}, "C":{}, "N":{}}, np.zeros(N_DOWNLOADS),  np.zeros(N_DOWNLOADS), [], []),
                     Algorithm({"W": {}, "F": {}, "C":{}, "N":{}},   np.zeros(N_DOWNLOADS),  np.zeros(N_DOWNLOADS), [], [])
                     )
    
    all_data.append(data)

    EVENTS_FILE = f"{EVENTS_DIR}\\{trace_name}_workload\\events.json"
    events_data = json.load(open(EVENTS_FILE, 'r'))

    BASE_VM_FILES = os.listdir(f"{DATA_DIR}\\{trace_name}\\{trace_name}_baseline\\LF + SEQ (1.0)\\json")
    SOL_VM_FILES = os.listdir(f"{DATA_DIR}\\{trace_name}\\{trace_name}_sol\\GF + RND (1.0)\\json")

    for is_baseline, a, vm_files in [(True, data.baseline, BASE_VM_FILES), (False, data.solution, SOL_VM_FILES)]:

        # Set a reference to the current trace data
        vm_jsons = None
        latencies_per_region = None
        if is_baseline: 
            latencies_per_region = a.latencies_per_region
            vm_jsons = [json.load(open(f"{DATA_DIR}\\{trace_name}\\{trace_name}_baseline\\LF + SEQ (1.0)\\json\\{vm_file}", 'r')) for vm_file in vm_files]
        else:
            latencies_per_region = a.latencies_per_region
            vm_jsons = [json.load(open(f"{DATA_DIR}\\{trace_name}\\{trace_name}_sol\\GF + RND (1.0)\\json\\{vm_file}", 'r')) for vm_file in vm_files]

        for vm_num, vm_data in enumerate(vm_jsons, start = 2):
            vmname = f"vm{vm_num:02}"

            for d in vm_data:

                region = vm_to_region(vmname)

                file_latencies_in_region = latencies_per_region[region] # Get  "W": {}
                videoname = d["file_name"]

                if d["total_download_time_sec"] == -1:
                    a.downloads_failed.append(videoname)
                    continue # Skip over failed downloads

                if videoname in file_latencies_in_region: # if "W": {"video0":[(1,1)]}
                    # For each video downloaded in the region, store: 
                    # (when it was downloaded, for how long, by whom, its popularity in this region, videoname)

                    latencies_per_region[region][videoname].append(
                        (recover_timestamp(vmname,videoname, events_data), d["total_download_time_sec"], 
                         vmname, recover_popularity_for_region(videoname, region, events_data), videoname)
                        )
                    
                else: # if "W": " video1: [...]", but no video0
                    latencies_per_region[region][videoname] = [                    
                        (recover_timestamp(vmname,videoname, events_data), d["total_download_time_sec"], 
                         vmname, recover_popularity_for_region(videoname, region, events_data), videoname)
                         ]

        for region, videos in latencies_per_region.items():
            for vid, times in videos.items():
                latencies_per_region[region][vid]  = sorted(latencies_per_region[region][vid], key=lambda x: x[0])

# import pprint
# pprint.pp(all_data[1].solution.latencies_per_region)


### Compute Average over all videos ### 
for trial_idx, trace_data in enumerate(all_data):

    N_VIDEOS = int(json.load(open(f"{EVENTS_DIR}\\{trace_name}_workload\\trace_info.json", 'r'))["total_files_generated"])

    EVENTS_FILE = f"{EVENTS_DIR}\\{trace_data.name}_workload\\events.json"
    events_data = json.load(open(EVENTS_FILE, 'r'))

    for is_baseline, a in [
        (True, trace_data.baseline), (False, trace_data.solution) 
          ]:
    
        latencies_per_video = a.latency_matrix # will be jagged list, can't use np :(

        vid_idx = 0
        number_of_downloads_nth_time = np.zeros(N_DOWNLOADS)
        for region, _ in regions_to_vms.items():
            for vid_name, vid_data in a.latencies_per_region[region].items():
                download_latencies = []
                for download_idx, (timestamp, latency, vm, rpop, _) in enumerate(vid_data):

                    if POPULARITY_FILTER:
                        # if recover_popularity_for_region(vid_name, region, events_data) < POPULARITY_THRESHOLD:
                        if rpop < POPULARITY_THRESHOLD:
                            download_latencies.append(latency)
                    else:
                        download_latencies.append(latency)
                    
                    number_of_downloads_nth_time[download_idx] += 1
                latencies_per_video.append(download_latencies) # video1 downloaded in C and video1 downloaded in F for the first time will get mapped into the same column of 'first download'
        print(f"{number_of_downloads_nth_time=}")

        # Compute mean per column
        num_unique_downloads = [] # number of downloads that get downloaded for the nth time . the denominator for the average, per each redownload
        sum_unique_download_latencies = []
        for n in range(N_DOWNLOADS): # Per column
            sum_latencies = 0
            nth_unique_redownloads = 0
            for i in range(len(latencies_per_video)): # Go over every row
                if n < len(latencies_per_video[i]): # Add values to the average for that column
                    nth_unique_redownloads +=1
                    sum_latencies += latencies_per_video[i][n]
            num_unique_downloads.append(nth_unique_redownloads)
            sum_unique_download_latencies.append(sum_latencies) 
            #TODO add failed download case (per discord messages)

        for i, (num, denom) in enumerate(zip (sum_unique_download_latencies, num_unique_downloads)):
            ep = 0.000001
            a.avg_latency[i] = num/(denom + ep)

        # Compute stdev per column
        stdev_numerator = 0
        nth_unique_redownloads = 0
        for n in range(N_DOWNLOADS): # Per column
            nth_unique_redownloads = 0
            for i in range(len(latencies_per_video)): # Go over every row
                if n < len(latencies_per_video[i]): # Add values to the average for that column
                    nth_unique_redownloads +=1
                    stdev_numerator += (latencies_per_video[i][n] - a.avg_latency[n]) ** 2

            a.stdev_latency[n] = np.sqrt(stdev_numerator/nth_unique_redownloads)
            

    print(trace_data.baseline.avg_latency)
    print(trace_data.solution.avg_latency)

all_data = [t for t in all_data if not t.name == "heavy1"] # Exclude heavy1

# Plot of average re-download latencies, one line per trial we ran
# fig1, ax1 = plt.subplots(1,1, figsize = (10,8))
fig1, ax1 = plt.subplots(1,1)
ax1.set_title(f"Average Improvement of 360Torrent over BitTorrent")
ax1.set_xlabel(f"Nth Regional Download")
ax1.set_ylabel("Average Improvement in Video Download Time (s)")


cmap = plt.get_cmap('tab20')  # 'tab20' gives 20 distinct colors
colors = [cmap(i) for i in range(0, N_DOWNLOADS)]

nth_download = [ i for i in range(0, N_DOWNLOADS)]
trace_data: TraceData # you can type annotate like this in an iterator
for trial_idx, trace_data in enumerate(all_data):
    diffs = trace_data.baseline.avg_latency - trace_data.solution.avg_latency
    ax1.set_xticks(range(0, N_DOWNLOADS))
    ax1.plot(nth_download, diffs, color= colors[trial_idx], label = trace_data.display_name)
    ax1.grid(True)

ax1.axhline(y=0, color = 'grey')

ax1.legend( loc="upper left")



FOCUS_TRACE, FOCUS_TRACE_NAME = "light_churn1", "Light Churn"
trace = [ t for t in all_data if t.name == FOCUS_TRACE][0]

fig2, ax2 = plt.subplots(1,N_DOWNLOADS, figsize = (25, 5))
fig3, ax3 = plt.subplots(1, N_DOWNLOADS, figsize = (25, 5))
fig3.suptitle(f"Distribution of Download Durations (s) Over Successive Regional Downloads (Trace: {FOCUS_TRACE_NAME})")

for i in range(0, N_DOWNLOADS):
    # where i is the download index
    ax2[i].set_title(f"Histogram of {i}st regional download latency")
    ax2[i].set_xlabel(f"Video Download Times (s)")
    ax2[i].set_ylabel(f"Quantity")

    ax3[i].set_ylim((0,0.075))
    ax3[i].set_xlim((0,200))
    ax3[i].set_xlabel(f"Video Download Times (s)")
    ax3[i].set_title(f"Distribution of Download Times (s)\n for Download #{i+1}")
    ax3[i].grid(True)

    max_t_download = 200
    ax2[i].set_xlim(0,max_t_download)

    download_times = []
    lm = trace.solution.latency_matrix
    for row in range(len(lm)):
        if i < len(lm[row]):
            download_times.append(lm[row][i])
    
    download_times = np.array(download_times)
    # Plot histogram
    ax2[i].hist(download_times, bins=100, color='blue', label='360Torrent')

    ts = np.linspace(0,max_t_download)
    # baseline_gauss = norm.pdf(ts, loc=np.mean(download_times), scale = np.std(download_times))
    if len(download_times) > 1:   
        gauss_mix = GaussianMixture(n_components=2)
        gauss_mix.fit(download_times.reshape(-1,1)) #How is it getting download_times of length 1?
        bimodal_gauss_pdf = np.exp(gauss_mix.score_samples(ts.reshape(-1,1)))

        ax3[i].plot(ts, bimodal_gauss_pdf, color='blue', label='360Torrent')

    download_times = []
    lm = trace.baseline.latency_matrix
    for row in range(len(lm)):
        if i < len(lm[row]):
            download_times.append(lm[row][i])
    # Plot histogram
    download_times = np.array(download_times)
    ax2[i].hist(download_times, bins=100, color='green', label='BitTorrent')

    ts = np.linspace(0,max_t_download)

    if len(download_times) > 1:   
        # solution_gauss = norm.pdf(ts, loc=np.mean(download_times), scale = np.std(download_times))
        gauss_mix = GaussianMixture(n_components=2)
        gauss_mix.fit(download_times.reshape(-1,1))
        bimodal_gauss_pdf = np.exp(gauss_mix.score_samples(ts.reshape(-1,1)))
        ax3[i].plot(ts, bimodal_gauss_pdf, color='green', label='BitTorrent')
    
    ax3[i].legend(loc = 'upper right')

fig4, ax4 = plt.subplots(1, len(regions_to_vms.items()), figsize = (25,5))

def print_reg(region):
    for vidname, records in region:
        print(vidname)
        print(records)

for i, (region, _) in enumerate(regions_to_vms.items(), start=0):

    for is_baseline, arr in [(True, trace.solution.latencies_per_region[region].items()), 
                             (False, trace.baseline.latencies_per_region[region].items())]:

        # Am I tagging them with popularity properly? Yes, I think so.
        # Am I sorting properly?
            # Maybe you could add an extra sorting rule? If popularities are identical sort by X

        # print(arr)
        #TODO: Many places you could be going wrong with these tuple accesses
        data = sorted(arr, key=lambda x: (x[1][0][3], x[1][0][1])) # Sort a region's videos first by popularity, then by download time
        
        print(f"\nvideos sorted by popularity")
        print_reg(data)
        # For each video, sort its downloads chronologically (currently sorted by latency), and pick the last element from that.
        data = [ (vname, sorted(dlowds, key=lambda x:x[0])) for vname, dlowds in data] # Look at the last download that occured
        print(f"\nvideos sorted by popularity and downloads sorted chronologically")
        print_reg(data)

        # Yeah looking at the data, there really is no clear lowering of latency for the last download.
        # How about when we average over all downloads, then will we see a clearer trend w.r.t popularity?

        # data = [ (vname, dlowds) for vname, dlowds in data]


        labels = []
        latencys = []

        z = 0
        for name, records in data:

            n=len(records)
            sum = 0
            for record in records:
                sum += record[1]

            labels.append(record[3])
            latencys.append(sum/n) # Average latency over all downloads in this region
            z+=1

        c = 'blue'
        if is_baseline: c= 'green'
        ax4[i].plot(labels, latencys, color=c) 
        arr = trace.baseline.latencies_per_region[region].items()


    ax4[i].set_title(f"Average Download of Each Video in Region {region}")
    ax4[i].set_ylabel("Latency (s)")
    ax4[i].set_xlabel("Popularity Ranking (Lower is Better)")

    # Yeah it doesn't seem like latency is notably lower for popular videos... at all.
    # We'll see what this is like compared to a baseline.

    # ax4[i].set_xscale('log')
    ax4[i].set_ylim((0, 100))


plt.show()