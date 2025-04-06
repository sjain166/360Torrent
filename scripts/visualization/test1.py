import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D

import os
import json

# DATA_DIR_BASELINE = "C:\\Users\\soula\\OneDrive\\Desktop\\light1_plot\\3.0 (RF + RND)\\json\\"
# DATA_DIR_SOL = "C:\\Users\\soula\\OneDrive\\Desktop\\light1_plot\\4.0\\json\\"
# EVENTS_FILE = "C:\\Users\\soula\\OneDrive\\Desktop\\Programming\\CS525\\360Torrent\\data\\light1_workload\\events.json"
# events_fs = open(EVENTS_FILE, 'r')
# events_data = json.load(events_fs)


DATA_DIR_BASELINE = "C:\\Users\\soula\\OneDrive\\Desktop\\heavy2_plot\\1.0 (RF + RND)\\json\\"
DATA_DIR_SOL = "C:\\Users\\soula\\OneDrive\\Desktop\\heavy2_plot\\1.0\\json\\"
EVENTS_FILE = "C:\\Users\\soula\\OneDrive\\Desktop\\Programming\\CS525\\360Torrent\\data\\heavy2_workload\\events.json"
events_fs = open(EVENTS_FILE, 'r')
events_data = json.load(events_fs)


# PLot number of download failures per client
# Latency per download per client

files = os.listdir(DATA_DIR_BASELINE)
files2 = os.listdir(DATA_DIR_SOL)
# files2 = files

regions_to_vms = { 
            "W": [f"vm{i:02d}" for i in [1,2,3,4,5]],
            "N": [f"vm{i:02d}" for i in [6,7,8,9,10]] ,
            "C": [f"vm{i:02d}" for i in [11,12,13,14,15]],
            "F": [f"vm{i:02d}" for i in [16,17,18,19,20]]
            }
def vm_to_region(vm): 
    res = [ r for r, arr in regions_to_vms.items() if vm in arr]
    return res[0]

axes = []

for i, (region, _ ) in enumerate(regions_to_vms.items()):
    fig, ax = plt.subplots(1, 1)
    ax.set_title(f"Download (s) of Each Video in Region {region} Over Successive Requests")
    ax.set_xlabel(f"Download Count in {region}")
    ax.set_ylabel("Download Latency (s)")
    ax.set_ylim(0,200)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    axes.append(ax)


def recover_timestamp(vmname, video):
    # Given the trace, vmname, and video name
    # recover the time it was downloaded at
    for d in events_data:
        if d["user"] == int(vmname[2:]):
            if not d["event"]["content"] == None:
                if d["event"]["content"]["name"] == video:
                    return d["event"]["time"]


# Each video has its own color, assuming 20 videos is enough
cmap = plt.get_cmap('tab20')  # 'tab20' gives 20 distinct colors
colors = [cmap(i) for i in range(20)]

show_video_range = range(0,12)

diff_latencies_per_region = []

for system, dir, dirfiles in [("Baseline", DATA_DIR_BASELINE, files), ("Solution", DATA_DIR_SOL, files2)]:
    # Each element will be a map of videoN: [] latencies in that region
    latencies_per_region = {"W": {}, "F": {}, "C":{}, "N":{}}

    for fo in dirfiles:
        with open(dir+fo, "r", encoding="utf-8") as fs:
            data = json.load(fs)
            vmname = fo[:4]
            for d in data:
                file_latencies_in_region = latencies_per_region[vm_to_region(vmname)] # Get  "W": {}
                videoname = d["file_name"]

                if videoname in file_latencies_in_region: # if "W": {"video0":[(1,1)]}
                    # For each video downloaded in the region, store, when it was downloaded, for how long, and by whom
                    latencies_per_region[vm_to_region(vmname)][videoname].append(
                        (recover_timestamp(vmname,videoname), d["total_download_time_sec"], vmname)
                        )
                else: # if "W": " video1: [...]", but no video0
                    latencies_per_region[vm_to_region(vmname)][videoname] = [(
                        (recover_timestamp(vmname,videoname), d["total_download_time_sec"], vmname) 
                        )]

        for region, videos in latencies_per_region.items():
            for vid, times in videos.items():
                latencies_per_region[region][vid]  = sorted(latencies_per_region[region][vid], key=lambda x: x[0])

    for ax_i, (region, _) in enumerate(regions_to_vms.items()):
        for name, vid_data in latencies_per_region[region].items():
            timestamps = []
            latencys = []
            nth_download = []
            vms = []
            # print(f" {len(vid_data)=} for region {name}")

            vid_outlier = False
            for i, (timestamp, latency, vm) in enumerate(vid_data):
                if latency > 150: vid_outlier = True
                timestamps.append(timestamp)
                latencys.append(latency)
                nth_download.append(i)
                vms.append(vm)

            if not vid_outlier:
                vidnum = int(name[5:])
                if vidnum in show_video_range:
                    color = colors[vidnum]

                    if system == "Baseline":
                        axes[ax_i].scatter(nth_download, latencys, color=color)
                        axes[ax_i].plot(nth_download, latencys, color=color, linestyle="-", label=name)
                    else:
                        axes[ax_i].scatter(nth_download, latencys, color=color)
                        axes[ax_i].plot(nth_download, latencys, color=color, linestyle="--", label='__nolegend__')

    diff_latencies_per_region.append(latencies_per_region)

for ax in axes:
    handles, labels = ax.get_legend_handles_labels()
    # Sort legend items alphabetically (or however you like)
    sorted_items = sorted(zip(labels, handles), key=lambda x: int(x[0][5:]))  # sort by label
    labels, handles = zip(*sorted_items)
    
    video_legend = ax.legend(handles, labels, loc="upper right")

    style_legend = [
        Line2D([0], [0], color='black', linestyle='-', label='Baseline'),
        Line2D([0], [0], color='black', linestyle='--', label='Solution')
    ]
    ax.legend(handles=style_legend, loc="upper left")
    ax.add_artist(video_legend)

plt.show()



axes = []

for i, (region, _ ) in enumerate(regions_to_vms.items()):
    fig, ax = plt.subplots(1, 1)
    ax.set_title(f"Improvement of Solution over Baseline in Region {region} Over Successive Requests")
    ax.set_xlabel(f"Download Count in {region}")
    ax.set_ylabel("Latency Improvement (s)")
    ax.set_ylim(-100,100)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    axes.append(ax)

show_video_range = range(0,20)
for ax_i, (region, _) in enumerate(regions_to_vms.items()):
        
        for (bname, bvid_data), (sname, svid_data) in zip(diff_latencies_per_region[0][region].items(), diff_latencies_per_region[1][region].items()):

            vid_outlier = False

            nth_download = []
            diffs = []

            for (i, (_ , blatency, _)), (j, (_, slatency, _)) in zip(enumerate(bvid_data), enumerate(svid_data)):
                # if blatency or slatency > 150: vid_outlier = True
                diffs.append(blatency - slatency) # So more positive is better
                nth_download.append(i)

            print(diffs)
            # if not vid_outlier:
            vidnum = int(bname[5:])
            if vidnum in show_video_range:
                color = colors[vidnum]

                axes[ax_i].scatter(nth_download, diffs, color=color)
                axes[ax_i].plot(nth_download, diffs, color=color, linestyle="-", label=bname)

for ax in axes:
    ax.legend()

plt.show()