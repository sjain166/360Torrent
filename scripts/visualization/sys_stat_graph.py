# import pandas as pd
# import matplotlib.pyplot as plt
# import os

# # Path to your dstat CSV file
# file_path = "../../tests/sys_logs/vm17/dstat_20250414_134146.csv"

# # Skip metadata until the correct header row
# with open(file_path) as f:
#     for i, line in enumerate(f):
#         if line.startswith('"total usage:usr"') or "usr" in line and "idl" in line:
#             header_row = i
#             break

# # Read CSV from detected header
# df = pd.read_csv(file_path, skiprows=header_row)
# df.columns = df.columns.str.replace('"', '').str.strip()

# # Create unified plot
# plt.figure(figsize=(14, 7))

# # Plot CPU metrics
# plt.plot(df["total usage:usr"], label="User CPU %")
# plt.plot(df["total usage:sys"], label="System CPU %")
# plt.plot(df["total usage:idl"], label="Idle CPU %")

# # Plot Network metrics
# plt.plot(df["net/total:recv"], label="Net Received (KB/s)")
# plt.plot(df["net/total:send"], label="Net Sent (KB/s)")

# # Plot Disk I/O metrics
# plt.plot(df["dsk/total:read"], label="Disk Read (KB/s)")
# plt.plot(df["dsk/total:writ"], label="Disk Write (KB/s)")

# plt.title("System Resource Utilization Over Time")
# plt.xlabel("Time (in samples)")
# plt.ylabel("Utilization / Throughput")
# plt.legend(loc="upper right")
# plt.grid(True)
# plt.tight_layout()
# plt.show()


import pandas as pd
import matplotlib.pyplot as plt
import os

plt.figure(figsize=(16, 8))

# Iterate over vm02 to vm19
for vm_id in range(2, 20):
    vm_name = f"vm{vm_id:02d}"
    file_path = f"../../tests/sys_logs/{vm_name}/sys_logs.csv"

    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue

    # Detect correct header row
    with open(file_path) as f:
        for i, line in enumerate(f):
            if line.startswith('"total usage:usr"') or ("usr" in line and "idl" in line):
                header_row = i
                break

    # Read data
    df = pd.read_csv(file_path, skiprows=header_row)
    df.columns = df.columns.str.replace('"', '').str.strip()

    # Optional: smoothen short noisy time series (if needed)
    label_prefix = f"{vm_name}"

    try:
        # CPU
        # plt.plot(df["total usage:usr"], label=f"{label_prefix} CPU usr")
        # plt.plot(df["total usage:sys"], label=f"{label_prefix} CPU sys")
        # plt.plot(df["total usage:idl"], label=f"{label_prefix} CPU idl")

        # Network
        # plt.plot(df["net/total:recv"], label=f"{label_prefix} Net recv")
        plt.plot(df["net/total:send"], label=f"{label_prefix} Net send")

        # Disk
        #plt.plot(df["dsk/total:read"], label=f"{label_prefix} Disk read")
        #plt.plot(df["dsk/total:writ"], label=f"{label_prefix} Disk write")
    except KeyError as e:
        print(f"Missing column in {vm_name}: {e}")
        continue

plt.title("System Resource Utilization Over Time (All VMs)")
plt.xlabel("Time (in samples)")
plt.ylabel("Utilization / Throughput")
plt.legend(fontsize='small', loc='upper right', ncol=2)
plt.grid(True)
plt.tight_layout()
plt.show()