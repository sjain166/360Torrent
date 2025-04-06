import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

import os
import json

DATA_DIR_BASELINE = "C:\\Users\\soula\\OneDrive\\Desktop\\3.0 (RF + RND)\\json\\"
DATA_DIR_SOL = "C:\\Users\\soula\\OneDrive\\Desktop\\4.0\\json\\"



# PLot number of download failures per client
# Latency per download per client

files = os.listdir(DATA_DIR_BASELINE)
files2 = os.listdir(DATA_DIR_SOL)
# files2 = files
REGION = "W"

regions_to_vms = { 
            "W": [f"vm{i:02d}" for i in [1,2,3,4,5]],
            "N": [f"vm{i:02d}" for i in [6,7,8,9,10]] ,
            "C": [f"vm{i:02d}" for i in [11,12,13,14,15]],
            "F": [f"vm{i:02d}" for i in [16,17,18,19,20]]
            }
def vm_to_region(vm): 
    res = [ r for r, arr in regions_to_vms.items() if vm in arr]
    return res[0]


EVENTS_FILE = "C:\\Users\\soula\\OneDrive\\Desktop\\Programming\\CS525\\360Torrent\\data\\light1_workload\\events.json"
events_fs = open(EVENTS_FILE, 'r')
events_data = json.load(events_fs)

axes = []

for i, (region, _ ) in enumerate(regions_to_vms.items()):
    fig, ax = plt.subplots(1, 1)
    ax.set_title(f"Download latencies of each video in region {region} over successive requests")
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
                for i, (timestamp, latency, vm) in enumerate(vid_data):
                    timestamps.append(timestamp)
                    latencys.append(latency)
                    nth_download.append(i)
                    vms.append(vm)
                
                color="blue"
                if system=="Baseline": color="green"
                axes[ax_i].scatter(nth_download, latencys, color=color)
                axes[ax_i].plot(nth_download, latencys, color=color)


plt.show()