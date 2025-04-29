import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D

from dataclasses import dataclass


import os
import json

TRACE_NAMES = ['light1', 'med1', 'heavy1', 'light_churn1', 'heavy_churn1']
DISPLAY_TRACE_NAMES = ["Light Traffic", "Medium Traffic", "Heavy Traffic", "Medium Traffic, Light Churn", "Medium Traffic, Heavy Churn"]


@dataclass
class Algorithm:
    latencies_per_region: dict
    avg_latency: np.array # average latencies over all video, on its nth regional re-download
    std_latency: np.array
    downloads_failed: int

@dataclass
class TraceData:
    name: str
    baseline_latencies_per_region: dict #latencies per region
    baseline_avg_latency: np.array # average latencies over all video, on its nth regional re-download
    baseline_std_latency: np.array
    baseline_download_failures: int
    solution_latencies_per_region: dict
    solution_avg_latency: np.array # average latencies over all video, on its nth regional re-download
    solution_std_latency: np.array
    solution_download_failures: int


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


N_DOWNLOADS = 5 # max number of downloads per region

### Data Loader ###
all_data = []
for trial_idx, trace_name in enumerate(TRACE_NAMES):

    data = TraceData(trace_name, 
                     {"W": {}, "F": {}, "C":{}, "N":{}}, np.zeros(N_DOWNLOADS),  np.zeros(N_DOWNLOADS),
                     {"W": {}, "F": {}, "C":{}, "N":{}},   np.zeros(N_DOWNLOADS),  np.zeros(N_DOWNLOADS))
    all_data.append(data)

    EVENTS_FILE = f"{EVENTS_DIR}\\{trace_name}_workload\\events.json"
    events_data = json.load(open(EVENTS_FILE, 'r'))

    BASE_VM_FILES = os.listdir(f"{DATA_DIR}\\{trace_name}\\{trace_name}_baseline\\LF + SEQ (1.0)\\json")
    SOL_VM_FILES = os.listdir(f"{DATA_DIR}\\{trace_name}\\{trace_name}_sol\\GF + RND (1.0)\\json")

    for is_baseline, vm_files in [(True, BASE_VM_FILES), (False, SOL_VM_FILES)]:

        # Set a reference to the current trace data
        vm_jsons = None
        latencies_per_region = None
        if is_baseline: 
            latencies_per_region = data.baseline_latencies_per_region
            vm_jsons = [json.load(open(f"{DATA_DIR}\\{trace_name}\\{trace_name}_baseline\\LF + SEQ (1.0)\\json\\{vm_file}", 'r')) for vm_file in vm_files]
        else:
            latencies_per_region = data.solution_latencies_per_region
            vm_jsons = [json.load(open(f"{DATA_DIR}\\{trace_name}\\{trace_name}_sol\\GF + RND (1.0)\\json\\{vm_file}", 'r')) for vm_file in vm_files]

        for vm_num, vm_data in enumerate(vm_jsons, start = 2):
            vmname = f"vm{vm_num:02}"

            for d in vm_data:

                file_latencies_in_region = latencies_per_region[vm_to_region(vmname)] # Get  "W": {}
                videoname = d["file_name"]

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

### Compute Average over all videos ### 
for trial_idx, trace_data in enumerate(all_data):

    N_VIDEOS = int(json.load(open(f"{EVENTS_DIR}\\{trace_name}_workload\\trace_info.json", 'r'))["total_files_generated"])

    for is_baseline, latencies_per_region, avg_latency, stdev_latency in [
        (True, trace_data.baseline_latencies_per_region, trace_data.baseline_avg_latency, trace_data.baseline_std_latency),
          (False, trace_data.solution_latencies_per_region, trace_data.solution_avg_latency, trace_data.solution_std_latency)
          ]:
    
        latencies_per_video = [] # will be jagged list, can't use np :(

        vid_idx = 0
        for region, _ in regions_to_vms.items():
            for vid_name, vid_data in latencies_per_region[region].items():
                download_latencies = []
                for download_idx, (timestamp, latency, vm) in enumerate(vid_data):
                    # TODO: Put any filters here
                    #    if latency > 150: vid_outlier = True
                    # latencies_per_video[vid_idx, download_idx] = latency
                    download_latencies.append(latency)
                latencies_per_video.append(download_latencies) # video1 downloaded in C and video1 downloaded in F for the first time will get mapped into the same column of 'first download'

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

        # print(f"{trace_data=}")
        for i, (num, denom) in enumerate(zip (sum_unique_download_latencies, num_unique_downloads)):
            avg_latency[i] = num/denom


        # Compute stdev per column
        stdev_numerator = 0
        nth_unique_redownloads = 0
        for n in range(N_DOWNLOADS): # Per column
            nth_unique_redownloads = 0
            for i in range(len(latencies_per_video)): # Go over every row
                if n < len(latencies_per_video[i]): # Add values to the average for that column
                    nth_unique_redownloads +=1
                    stdev_numerator += (latencies_per_video[i][n] - avg_latency[n]) ** 2

            stdev_latency[n] = np.sqrt(stdev_numerator/nth_unique_redownloads)


    print(trace_data.baseline_avg_latency)
    print(trace_data.baseline_std_latency)


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

    print(f"{trace_data.name=}")
    print(f"{trace_data.solution_avg_latency=}")
    print(f"{trace_data.baseline_avg_latency=}")

    diffs = trace_data.baseline_avg_latency - trace_data.solution_avg_latency
    

    ax1.plot(nth_download, diffs, color= colors[trial_idx], label = trace_data.name)

ax1.legend( loc="upper left")
plt.show()


    
# SUBPLOT_X_SPACE = 0.3

# # axes = []
# fig, ax = plt.subplots(1,4, figsize=(25, 5))
# plt.subplots_adjust(wspace=SUBPLOT_X_SPACE)

# for i, (region, _ ) in enumerate(regions_to_vms.items()):
#     # fig, ax = plt.subplots(1, 1)
#     ax[i].set_title(f"Download of Each Video \n in Region {region} Over Time")
#     ax[i].set_xlabel(f"Download Count in {region}")
#     ax[i].set_ylabel("Download Latency (s)")
#     ax[i].set_ylim(0,200)
#     ax[i].xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
#     # axes.append(ax)



# # Each video has its own color, assuming 20 videos is enough
# cmap = plt.get_cmap('tab20')  # 'tab20' gives 20 distinct colors
# colors = [cmap(i) for i in range(20)]

# show_video_range = range(0,12)

# diff_latencies_per_region = []

# for system, dir, dirfiles in [(BASE_NAME, DATA_DIR_BASELINE, files), (SOL_NAME, DATA_DIR_SOL, files2)]:


#     for ax_i, (region, _) in enumerate(regions_to_vms.items()):
#         for name, vid_data in latencies_per_region[region].items():
#             timestamps = []
#             latencys = []
#             nth_download = []
#             vms = []
#             # print(f" {len(vid_data)=} for region {name}")

#             vid_outlier = False
#             for i, (timestamp, latency, vm) in enumerate(vid_data):
#                 if latency > 150: vid_outlier = True
#                 timestamps.append(timestamp)
#                 latencys.append(latency)
#                 nth_download.append(i)
#                 vms.append(vm)

#             if not vid_outlier:
#                 vidnum = int(name[5:])
#                 if vidnum in show_video_range:
#                     color = colors[vidnum]

#                     if system == BASE_NAME:
#                         ax[ax_i].scatter(nth_download, latencys, color=color)
#                         ax[ax_i].plot(nth_download, latencys, color=color, linestyle="-", label=name)
#                     else:
#                         ax[ax_i].scatter(nth_download, latencys, color=color)
#                         ax[ax_i].plot(nth_download, latencys, color=color, linestyle="--", label='__nolegend__')

#     diff_latencies_per_region.append(latencies_per_region)

# for i in range(len(ax)):
#     handles, labels = ax[i].get_legend_handles_labels()
#     # Sort legend items alphabetically (or however you like)
#     sorted_items = sorted(zip(labels, handles), key=lambda x: int(x[0][5:]))  # sort by label
#     labels, handles = zip(*sorted_items)
    
#     video_legend = ax[i].legend(handles, labels, loc="upper right", ncol=2)

#     style_legend = [
#         Line2D([0], [0], color='black', linestyle='-', label=BASE_NAME),
#         Line2D([0], [0], color='black', linestyle='--', label=SOL_NAME)
#     ]
#     ax[i].legend(handles=style_legend, loc="upper left")
#     ax[i].add_artist(video_legend)


# fig.savefig(OUT_DIR+"video_download_latencies_over_time.png")



# fig, ax = plt.subplots(1,4, figsize=(25, 5))
# plt.subplots_adjust(wspace=SUBPLOT_X_SPACE)
# for i, (region, _ ) in enumerate(regions_to_vms.items()):
#     ax[i].set_title(f"Improvement over {BASE_NAME} \n in Region {region} Over Time")
#     ax[i].set_xlabel(f"Download Count in {region}")
#     ax[i].set_ylabel(f"Latency Improvement over {BASE_NAME} (s)")
#     ax[i].set_ylim(-100,100)
#     ax[i].xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

# show_video_range = range(0,12)
# for ax_i, (region, _) in enumerate(regions_to_vms.items()):
        
#     for (bname, bvid_data), (sname, svid_data) in zip(diff_latencies_per_region[0][region].items(), diff_latencies_per_region[1][region].items()):

#         vid_outlier = False

#         nth_download = []
#         diffs = []

#         for (i, (_ , blatency, _)), (j, (_, slatency, _)) in zip(enumerate(bvid_data), enumerate(svid_data)):
#             # if blatency or slatency > 150: vid_outlier = True
#             diffs.append(blatency - slatency) # So more positive is better
#             nth_download.append(i)

#         print(diffs)
#         # if not vid_outlier:
#         vidnum = int(bname[5:])
#         if vidnum in show_video_range:
#             color = colors[vidnum]
#             ax[ax_i].scatter(nth_download, diffs, color=color)
#             ax[ax_i].plot(nth_download, diffs, color=color, linestyle="-", label=bname)

#     ax[ax_i].legend(ncol=2)

# fig.savefig(OUT_DIR+"improvement_over_baseline.png")

# plt.show()