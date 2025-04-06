import numpy as np
import matplotlib.pyplot as plt

import os
import json

DATA_DIR_BASELINE = "C:\\Users\\soula\\OneDrive\\Desktop\\3.0 (RF + RND)\\json\\"
DATA_DIR_SOL = "C:\\Users\\soula\\OneDrive\\Desktop\\4.0\\json\\"



# PLot number of download failures per client
# Latency per download per client

files = os.listdir(DATA_DIR_BASELINE)
files2 = os.listdir(DATA_DIR_SOL)
# files2 = files

for fb, fo in zip(files, files2):

    # Create the bar chart

    download_latency = [ [], [] ]
    video_names_b = []
    failed_videos = [ [], []]

    with open(DATA_DIR_BASELINE+fb, "r", encoding="utf-8") as fs:
        data = json.load(fs)
        vmname = fb
        for d in data:
            video_names_b.append(d["file_name"])
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

    video_names_o = []
    with open(DATA_DIR_SOL+fo, "r", encoding="utf-8") as fs:
        data = json.load(fs)
        vmname = fo
        for d in data:
            video_names_o.append(d["file_name"]) # BOTH SHOULD HAVE THE SAME VIDEO NAMES
            dtime = d["total_download_time_sec"]
            # Note if each chunk download has -1 then that means download failed
            dchunks = d["chunks"]
            n_chunks_failed = 0
            # If at least one chunk failed, then our download failed
            download_failed  = False
            for chunk in dchunks:
                download_failed = download_failed or (chunk["download_time"] == -1)
            if download_failed:
                failed_videos[1].append(d["file_name"])
                download_latency[1].append(500)
            else: 
                download_latency[1].append(dtime)   

    colors = [ [], [] ]

    x = np.arange(len(video_names_b))
    width = 0.25
    multiplier = 0

    # fig, ax = plt.subplots(layout='constrained')

    for n, l in zip(video_names_b, download_latency[0]):
        if n in failed_videos[0]:
            colors[0].append("darkgreen")
        else:
            colors[0].append("green")

    for n, l in zip(video_names_o, download_latency[1]):
        if n in failed_videos[1]:
            colors[1].append("darkblue")
        else:
            colors[1].append("blue")

    # # Show the plot
    # plt.show()

    # Create figure and axis
    fig, ax = plt.subplots(2, 1, figsize=(8, 6))

    ax[0].bar(video_names_b, download_latency[0], color=colors[0])  # Plot with custom colors
    # Labels and title
    ax[0].set_xlabel("Videos")
    ax[0].set_ylabel("Latencies (s)")
    ax[0].set_ylim((0,200))
    ax[0].set_title(f" VM{vmname} BASE")

    ax[1].bar(video_names_o, download_latency[1], color=colors[1])  # Plot with custom colors
    ax[1].set_xlabel("Videos")
    ax[1].set_ylabel("Latencies (s)")
    ax[1].set_ylim((0, 200))
    ax[1].set_title(f" VM{vmname} SOL")

    plt.show()

    # bar_width = 0.4

    # print(video_names_b)
    # print(video_names_o)

    # list1 = video_names_b
    # list2 = video_names_o
    # diff_indices = [i for i in range(min(len(list1), len(list2))) if list1[i] != list2[i]]

    # video_names_o = video_names_b.insert

    # print(download_latency)
    # # Plot both bar sets, offsetting the second one
    # ax.bar(x - bar_width / 2, download_latency[0], width=bar_width, color=colors[0], label="BASE")
    # ax.bar(x + bar_width / 2, download_latency[1], width=bar_width, color=colors[1], label="SOL")

    # # Labels, title, and legend
    # ax.set_xlabel("Videos")
    # ax.set_ylabel("Latencies (s)")
    # ax.set_title(f"VM{vmname} Latency Comparison")
    # ax.set_xticks(x)
    # ax.set_xticklabels(video_names_b)
    # ax.legend()


# for fb, fo in zip(files, files2):
