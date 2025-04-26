# import subprocess
# import time

# # Define your VM hosts (hostnames or IPs)

# VM_HOSTS = [
#     "sp25-cs525-1203.cs.illinois.edu",
#     "sp25-cs525-1216.cs.illinois.edu",
#     "sp25-cs525-1217.cs.illinois.edu",
#     "sp25-cs525-1206.cs.illinois.edu",
#     "sp25-cs525-1207.cs.illinois.edu",
#     "sp25-cs525-1212.cs.illinois.edu",
#     "sp25-cs525-1213.cs.illinois.edu",
#     "sp25-cs525-1204.cs.illinois.edu",
#     "sp25-cs525-1205.cs.illinois.edu",
#     "sp25-cs525-1208.cs.illinois.edu",
#     "sp25-cs525-1209.cs.illinois.edu",
#     "sp25-cs525-1210.cs.illinois.edu",
#     "sp25-cs525-1218.cs.illinois.edu",
#     "sp25-cs525-1219.cs.illinois.edu",
#     "sp25-cs525-1220.cs.illinois.edu",
#     "sp25-cs525-1214.cs.illinois.edu",
#     "sp25-cs525-1215.cs.illinois.edu",
#     "sp25-cs525-1211.cs.illinois.edu"
# ]


# # VM_HOSTS_11 = ["sp25-cs525-1211.cs.illinois.edu"]

# COMMANDS = [
#     "2",
#     "video0"
# ]


# # Username for ssh
# USERNAME = "sj99"

# # Tmux session name
# SESSION_NAME = "peer_session"

# def send_command_to_vm(host, command):
#     tmux_cmd = (
#         f"tmux send-keys -t {SESSION_NAME} '{command}' C-m"
#     )
#     full_cmd = f"ssh {USERNAME}@{host} \"{tmux_cmd}\""
#     print(f"[INFO] Sending to {host}:\n  {command}")
#     subprocess.run(full_cmd, shell=True)

# def ensure_tmux_session_exists(host):
#     check_cmd = f"ssh {USERNAME}@{host} 'tmux has-session -t {SESSION_NAME} 2>/dev/null || tmux new-session -d -s {SESSION_NAME}'"
#     subprocess.run(check_cmd, shell=True)

# def main():
#     # command = input("💬 Enter the command to run on all VMs via tmux: ")

#     for command in COMMANDS:

#         for host in VM_HOSTS:
#             ensure_tmux_session_exists(host)
#             send_command_to_vm(host, command)
#             time.sleep(2)
        
#         print("\n✅ Command sent to all VMs in tmux session:", SESSION_NAME)

# if __name__ == "__main__":
#     main()


import json
import time
import subprocess

# ---- CONFIGURATION ----
EVENT_FILE = "user_events.json"
SESSION_NAME = "peer_session"
USERNAME = "sj99"

USER_TO_VM = {
    1: "sp25-cs525-1201.cs.illinois.edu",
    2: "sp25-cs525-1202.cs.illinois.edu",
    3: "sp25-cs525-1203.cs.illinois.edu",
    4: "sp25-cs525-1204.cs.illinois.edu",
    5: "sp25-cs525-1205.cs.illinois.edu",
    6: "sp25-cs525-1206.cs.illinois.edu",
    7: "sp25-cs525-1207.cs.illinois.edu",
    8: "sp25-cs525-1208.cs.illinois.edu",
    9: "sp25-cs525-1209.cs.illinois.edu",
    10: "sp25-cs525-1210.cs.illinois.edu",
    11: "sp25-cs525-1211.cs.illinois.edu",
    12: "sp25-cs525-1212.cs.illinois.edu",
    13: "sp25-cs525-1213.cs.illinois.edu",
    14: "sp25-cs525-1214.cs.illinois.edu",
    15: "sp25-cs525-1215.cs.illinois.edu",
    16: "sp25-cs525-1216.cs.illinois.edu",
    17: "sp25-cs525-1217.cs.illinois.edu",
    18: "sp25-cs525-1218.cs.illinois.edu",
    19: "sp25-cs525-1219.cs.illinois.edu",
    20: "sp25-cs525-1220.cs.illinois.edu",
}

# ---- UTILITIES ----
def send_command_to_vm(host, command, i, total):
    tmux_cmd = f'tmux send-keys -t {SESSION_NAME} "{command}" C-m'
    ssh_cmd = f'ssh {USERNAME}@{host} "{tmux_cmd}"'
    print(f"[{i}/{total} - INFO] Sending to {host}: {command}")
    subprocess.run(ssh_cmd, shell=True)

def event_to_commands(event_type, file_name):
    if event_type == "upload":
        return ["3", file_name]
    elif event_type == "request":
        return ["2", file_name]
    elif event_type == "leave":
        return ["4"]
    elif event_type == "join":
        return ["__START__"]
    return []


# Start the Respective VMs
def start_peer_on_vm(host, i, total):
    print(f"[{i}/{total} - BOOT] Starting peer on {host}")
    cmd = f"""ssh {USERNAME}@{host} "tmux kill-session -t {SESSION_NAME} || true && tmux new-session -d -s {SESSION_NAME} 'cd /home/sj99/360Torrent && source myenv/bin/activate && python3 -m peer.peer SEQ >> /home/sj99/360Torrent/tests/peer.log 2>&1'" """
    subprocess.run(cmd, shell=True)

# ---- MAIN SIMULATION DRIVER ----
def run_event_schedule():
    start = time.time()
    EVENT_FILE = "/Users/sidpro/Desktop/WorkPlace/UIUC/Spring-25/CS 525/Final Project/360Torrent/data/final/med1_workload/events.json"
    with open(EVENT_FILE) as f:
        events = json.load(f)

    print("Total Events : " , len(events))

    for i in range(len(events)):
        event = events[i]
        user_id = event["user"]
        event_data = event["event"]
        event_type = event_data["type"]

        vm_host = USER_TO_VM[user_id]
        file_name = ''
       
        if event_type != 'join' and event_type != 'leave':
            file_name = event_data["content"]["name"]

        commands = event_to_commands(event_type, file_name)

        for cmd in commands:
            if cmd == "__START__":
                start_peer_on_vm(vm_host, i, len(events))
            else :
                send_command_to_vm(vm_host, cmd, i, len(events))
                
        if event_type == "join" or event_type == "upload":
            time.sleep(2)

        # Sleep before next event
        if i + 1 < len(events):
            current_time = event_data["time"]
            next_time = events[i + 1]["event"]["time"]
            sleep_duration_ms = next_time - current_time
            time.sleep(sleep_duration_ms / 1000)

    print("\n✅ All scheduled events executed.")
    print("The Execution Started at : ", start)

# ---- EXECUTION ----
if __name__ == "__main__":
    run_event_schedule()