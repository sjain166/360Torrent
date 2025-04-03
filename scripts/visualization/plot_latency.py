import numpy as np
import matplotlib.pyplot as plt

import os
import json

DATA_DIR_BASELINE = "C:\\Users\\soula\\OneDrive\\Desktop\\light_1_baseline\\1.0\\json\\"
DATA_DIR_SOL = "C:\\Users\\soula\\OneDrive\\Desktop\\light_1_sol\\1.0\\json\\"

# PLot number of download failures per client
# Latency per download per client

files = os.listdir(DATA_DIR_BASELINE)
# files2 = os.listdir(DATA_DIR_SOL)
files2 = files

for fb, fs in zip(files, files2):

    # Create the bar chart
    plt.figure(figsize=(8, 5))  # Set figure size

    download_latency = [ [], [] ]
    video_names = []
    failed_videos = [ [], []]

    with open(DATA_DIR_BASELINE+fb, "r", encoding="utf-8") as fs:
        data = json.load(fs)
        vmname = fb
        for d in data:
            video_names.append(d["file_name"])
            dtime = d["total_download_time_sec"]
            # Note if each chunk download has -1 then that means download failed
            dchunks = d["chunks"]
            n_chunks_failed = 0
            # If at least one chunk failed, then our download failed
            download_failed  = False
            for chunk in dchunks:
                download_failed = download_failed or (chunk["download_time"] == -1)
            if download_failed:
                failed_videos[0].append(d["file_name"])
                download_latency[0].append(500)
            else: 
                download_latency[0].append(dtime)

    # with open(DATA_DIR_BASELINE+fs, "r", encoding="utf-8") as fs:
    #     data = json.load(fs)
    #     vmname = fb
    #     for d in data:
    #         # video_names.append(d["file_name"]) # BOTH SHOULD HAVE THE SAME VIDEO NAMES
    #         dtime = d["total_download_time_sec"]
    #         # Note if each chunk download has -1 then that means download failed
    #         dchunks = d["chunks"]
    #         n_chunks_failed = 0
    #         # If at least one chunk failed, then our download failed
    #         download_failed  = False
    #         for chunk in dchunks:
    #             download_failed = download_failed or (chunk["download_time"] == -1)
    #         if download_failed:
    #             failed_videos[1].append(d["file_name"])
    #             download_latency[1].append(500)
    #         else: 
    #             download_latency[1].append(dtime)   

    colors = [ [], [] ]

    for n, l in zip(video_names, download_latency[0]):
        if n in failed_videos:
            colors[0].append("darkgreen")
        else:
            colors[0].append("green")

    # for n, l in zip(video_names, download_latency[1]):
    #     if n in failed_videos:
    #         colors[1].append("darkblue")
    #     else:
    #         colors[1].append("blue")


    

    plt.bar(video_names, download_latency[0], color=colors[0])  # Plot with custom colors
    # Labels and title
    plt.xlabel("Videos")
    plt.ylabel("Latencies (s)")
    plt.title(f" VM{vmname} BASE")

    # plt.bar(video_names, download_latency[1], color=colors[1])  # Plot with custom colors
    # plt.xlabel("Videos")
    # plt.ylabel("Latencies (s)")
    # plt.title(f" VM{vmname} SOL")

    # Show the plot
    plt.show()