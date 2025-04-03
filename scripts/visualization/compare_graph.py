


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

def extract_vm_data(zip_path, vm_name):
    with zipfile.ZipFile(zip_path, 'r') as z:
        if vm_name not in z.namelist():
            return {}
        with z.open(vm_name) as f:
            data = json.load(f)

    video_times = {}
    for event in data:
        video = event.get("file_name")
        if video is not None:
            video_times[video] = event.get("total_download_time_sec", np.nan)
    return video_times

baseline_zip = "/Users/sidpro/Downloads/rf-seq-2.0.zip"
sol_zip = "/Users/sidpro/Downloads/sol-4.0.zip"

os.makedirs("vm_plots", exist_ok=True)

for i in range(2, 21):
    vm_name = f"json/vm{str(i).zfill(2)}.json"
    print(f"Processing {vm_name}")

    baseline_data = extract_vm_data(baseline_zip, vm_name)
    sol_data = extract_vm_data(sol_zip, vm_name)

    videos = sorted(set(baseline_data.keys()).union(sol_data.keys()))
    baseline_times = [baseline_data.get(v, np.nan) for v in videos]
    sol_times = [sol_data.get(v, np.nan) for v in videos]

    if not videos:
        continue

    x = np.arange(len(videos))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))

    # Set bar colors — red if value is -1, else default
    baseline_colors = ['red' if t == -1 else 'C0' for t in baseline_times]
    sol_colors = ['red' if t == -1 else 'C1' for t in sol_times]

    ax.bar(x - width/2, baseline_times, width, label='Baseline', color=baseline_colors)
    ax.bar(x + width/2, sol_times, width, label='Sol', color=sol_colors)

    for idx, video in enumerate(videos):
        if np.isnan(baseline_times[idx]):
            ax.text(x[idx] - width/2, 0, "Missing", ha='center', va='bottom', color='black')
        if np.isnan(sol_times[idx]):
            ax.text(x[idx] + width/2, 0, "Missing", ha='center', va='bottom', color='black')

    ax.set_ylabel("Download Time (s)")
    ax.set_title(f"Download Time Comparison - {vm_name}")
    ax.set_xticks(x)
    ax.set_xticklabels(videos, rotation=45, ha='right')
    ax.legend()

    plt.tight_layout()
    
    vm_id = vm_name.split("/")[-1].replace(".json", "")
    plt.savefig(f"vm_plots/{vm_id}.png")
    plt.close()