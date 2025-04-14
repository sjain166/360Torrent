


# import zipfile
# import json
# import numpy as np
# import matplotlib.pyplot as plt
# import os

# def extract_vm_data(zip_path, vm_name):
#     with zipfile.ZipFile(zip_path, 'r') as z:
#         if vm_name not in z.namelist():
#             return {}
#         with z.open(vm_name) as f:
#             data = json.load(f)

#     video_times = {}
#     for event in data:
#         video = event.get("file_name")
#         if video is not None:
#             video_times[video] = event.get("total_download_time_sec", np.nan)
#     return video_times

# baseline_zip = "/Users/sidpro/Downloads/rf-seq-1.0.zip"
# sol_zip = "/Users/sidpro/Downloads/sol-3.0.zip"

# # Create output directory for PNGs
# os.makedirs("vm_plots", exist_ok=True)

# # Loop over vm02 to vm20
# for i in range(2, 21):
#     vm_name = f"json/vm{str(i).zfill(2)}.json"
#     print(vm_name)

#     baseline_data = extract_vm_data(baseline_zip, vm_name)
#     sol_data = extract_vm_data(sol_zip, vm_name)

#     videos = sorted(set(baseline_data.keys()).union(sol_data.keys()))
#     baseline_times = [baseline_data.get(v, np.nan) for v in videos]
#     sol_times = [sol_data.get(v, np.nan) for v in videos]

#     if not videos:
#         continue

#     x = np.arange(len(videos))
#     width = 0.35

#     fig, ax = plt.subplots(figsize=(12, 6))
#     ax.bar(x - width/2, baseline_times, width, label='Baseline')
#     ax.bar(x + width/2, sol_times, width, label='Sol')

#     for idx, video in enumerate(videos):
#         if np.isnan(baseline_times[idx]):
#             ax.text(x[idx] - width/2, 0, "Missing", ha='center', va='bottom', color='red')
#         if np.isnan(sol_times[idx]):
#             ax.text(x[idx] + width/2, 0, "Missing", ha='center', va='bottom', color='red')

#     ax.set_ylabel("Download Time (s)")
#     ax.set_title(f"Download Time Comparison - {vm_name}")
#     ax.set_xticks(x)
#     ax.set_xticklabels(videos, rotation=45, ha='right')
#     ax.legend()

#     plt.tight_layout()
#     # plt.show()
#     plt.savefig(f"vm_plots/{vm_name.replace('.json', '')}.png")  # 🔥 Save plot
#     # splt.close()  # Prevent displaying all plots

import zipfile
import json
import numpy as np
import matplotlib.pyplot as plt
import os

# def extract_vm_data(zip_path, vm_name):
#     with zipfile.ZipFile(zip_path, 'r') as z:
#         if vm_name not in z.namelist():
#             return {}
#         with z.open(vm_name) as f:
#             data = json.load(f)

#     video_times = {}
#     for event in data:
#         video = event.get("file_name")
#         if video is not None:
#             video_times[video] = event.get("total_download_time_sec", np.nan)
#     return video_times

def extract_vm_data(zip_path, vm_name):
    with zipfile.ZipFile(zip_path, 'r') as z:
        if vm_name not in z.namelist():
            return {}, {}
        with z.open(vm_name) as f:
            data = json.load(f)

    video_times = {}
    video_peers = {}

    for event in data:
        video = event.get("file_name")
        if not video:
            continue

        video_times[video] = event.get("total_download_time_sec", np.nan)

        # Collect unique peers from all chunks
        peers = set()
        for chunk in event.get("chunks", []):
            peer_str = chunk.get("peers_tried", "")
            chunk_peers = [p.strip() for p in peer_str.split(",") if p.strip()]
            peers.update(chunk_peers)

        video_peers[video] = ", ".join(sorted(peers)) if peers else "N/A"

    return video_times, video_peers

baseline_zip = "/Users/sidpro/Downloads/lockman/baseline.zip"
sol_zip = "/Users/sidpro/Downloads/lockman/optimized.zip"

os.makedirs("vm_plots", exist_ok=True)

for i in range(2, 21):
    vm_name = f"json/vm{str(i).zfill(2)}.json"
    print(f"Processing {vm_name}")

    baseline_data, baseline_peers = extract_vm_data(baseline_zip, vm_name)
    sol_data, sol_peers = extract_vm_data(sol_zip, vm_name)

    videos = sorted(set(baseline_data.keys()).union(sol_data.keys()))
    baseline_times = [baseline_data.get(v, np.nan) for v in videos]
    sol_times = [sol_data.get(v, np.nan) for v in videos]

    if not videos:
        continue

    y = np.arange(len(videos))
    height = 0.35

    fig, ax = plt.subplots(figsize=(10, max(6, len(videos) * 0.5)))  # auto height
    ax.barh(y - height/2, baseline_times, height, label='baseline-rf-seq',
            color=['red' if t == -1 else 'C0' for t in baseline_times])
    ax.barh(y + height/2, sol_times, height, label='optimized-gf-rnd',
            color=['red' if t == -1 else 'C1' for t in sol_times])

    # Annotate missing
    for idx, video in enumerate(videos):
        if np.isnan(baseline_times[idx]):
            ax.text(0, y[idx] - height/2, "Missing", va='center', color='black')
        if np.isnan(sol_times[idx]):
            ax.text(0, y[idx] + height/2, "Missing", va='center', color='black')

    # Annotate peers
    for idx, video in enumerate(videos):
        if not np.isnan(baseline_times[idx]):
            ax.text(baseline_times[idx] + 0.5, y[idx] - height/2, baseline_peers.get(video, ""), 
                    va='center', fontsize=8)
        if not np.isnan(sol_times[idx]):
            ax.text(sol_times[idx] + 0.5, y[idx] + height/2, sol_peers.get(video, ""), 
                    va='center', fontsize=8)

    ax.set_xlabel("Download Time (s)")
    ax.set_yticks(y)
    ax.set_yticklabels(videos)
    ax.set_title(f"Download Time Comparison - {vm_name}")
    ax.legend()
    plt.tight_layout()
    
    vm_id = vm_name.split("/")[-1].replace(".json", "")
    plt.savefig(f"vm_plots/{vm_id}.png")
    plt.close()