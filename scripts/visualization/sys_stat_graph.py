import pandas as pd
import matplotlib.pyplot as plt
import os

# Path to your dstat CSV file
file_path = "../../tests/sys_logs/vm05/dstat_20250414_094645.csv"

# Skip metadata until the correct header row
with open(file_path) as f:
    for i, line in enumerate(f):
        if line.startswith('"total usage:usr"') or "usr" in line and "idl" in line:
            header_row = i
            break

# Read CSV from detected header
df = pd.read_csv(file_path, skiprows=header_row)
df.columns = df.columns.str.replace('"', '').str.strip()

# Create unified plot
plt.figure(figsize=(14, 7))

# Plot CPU metrics
plt.plot(df["total usage:usr"], label="User CPU %")
plt.plot(df["total usage:sys"], label="System CPU %")
plt.plot(df["total usage:idl"], label="Idle CPU %")

# Plot Network metrics
plt.plot(df["net/total:recv"], label="Net Received (KB/s)")
plt.plot(df["net/total:send"], label="Net Sent (KB/s)")

# Plot Disk I/O metrics
plt.plot(df["dsk/total:read"], label="Disk Read (KB/s)")
plt.plot(df["dsk/total:writ"], label="Disk Write (KB/s)")

plt.title("System Resource Utilization Over Time")
plt.xlabel("Time (in samples)")
plt.ylabel("Utilization / Throughput")
plt.legend(loc="upper right")
plt.grid(True)
plt.tight_layout()
plt.show()