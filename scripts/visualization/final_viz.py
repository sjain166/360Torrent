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
POPULARITY_FILTER = True
POPULARITY_THRESHOLD = 5000

### Data Loader ###
all_data = []
for trial_idx, trace_name in enumerate(TRACE_NAMES):

    data = TraceData(trace_name, 
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

                file_latencies_in_region = latencies_per_region[vm_to_region(vmname)] # Get  "W": {}
                videoname = d["file_name"]

                if d["total_download_time_sec"] == -1:
                    a.downloads_failed.append(videoname)
                    continue # Skip over failed downloads

                if videoname in file_latencies_in_region: # if "W": {"video0":[(1,1)]}
                    # For each video downloaded in the region, store: when it was downloaded, for how long, and by whom

                    latencies_per_region[vm_to_region(vmname)][videoname].append(
                        (recover_timestamp(vmname,videoname, events_data), d["total_download_time_sec"], vmname)
                        )
                    

                else: # if "W": " video1: [...]", but no video0
                    latencies_per_region[vm_to_region(vmname)][videoname] = [(
                        (recover_timestamp(vmname,videoname, events_data), d["total_download_time_sec"], vmname) 
                        )]

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
                for download_idx, (timestamp, latency, vm) in enumerate(vid_data):

                    if POPULARITY_FILTER:
                        if recover_popularity_for_region(vid_name, region, events_data) < POPULARITY_THRESHOLD:
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
fig1, ax1 = plt.subplots(1,1, figsize = (10,8))
ax1.set_title(f"Average Download Latencys per Trial Over Multiple Downloads")
ax1.set_xlabel(f"Download Count")
ax1.set_ylabel("Average Improvement in Download Latency (Over All Videos) s")


cmap = plt.get_cmap('tab20')  # 'tab20' gives 20 distinct colors
colors = [cmap(i) for i in range(0, N_DOWNLOADS)]

trace_data: TraceData # you can type annotate like this in an iterator
for trial_idx, trace_data in enumerate(all_data):
    nth_download = [ i for i in range(0, N_DOWNLOADS)]
    diffs = trace_data.baseline.avg_latency - trace_data.solution.avg_latency
    ax1.plot(nth_download, diffs, color= colors[trial_idx], label = trace_data.name)

ax1.legend( loc="upper left")



trace = [ t for t in all_data if t.name == "light1"][0]

fig2, ax2 = plt.subplots(1,N_DOWNLOADS, figsize = (25, 5))
fig3, ax3 = plt.subplots(1, N_DOWNLOADS, figsize = (25, 5))

for i in range(0, N_DOWNLOADS):
    # where i is the download index
    ax2[i].set_title(f"Histogram of {i}st regional download latency")
    ax2[i].set_xlabel(f"Video Download Times (s)")
    ax2[i].set_ylabel(f"Quantity")

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

        ax3[i].plot(ts, bimodal_gauss_pdf, color='blue')



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
        ax3[i].plot(ts, bimodal_gauss_pdf, color='green')

plt.show()