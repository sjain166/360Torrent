import subprocess
import time

# Define your VM hosts (hostnames or IPs)
VM_HOSTS_EXCEPT_11 = [
    "sp25-cs525-1203.cs.illinois.edu",
    "sp25-cs525-1216.cs.illinois.edu",
    "sp25-cs525-1217.cs.illinois.edu",
    "sp25-cs525-1206.cs.illinois.edu",
    "sp25-cs525-1207.cs.illinois.edu",
    "sp25-cs525-1214.cs.illinois.edu",
    "sp25-cs525-1215.cs.illinois.edu",
    "sp25-cs525-1212.cs.illinois.edu",
    "sp25-cs525-1213.cs.illinois.edu",
    "sp25-cs525-1204.cs.illinois.edu",
    "sp25-cs525-1205.cs.illinois.edu",
    "sp25-cs525-1208.cs.illinois.edu",
    "sp25-cs525-1209.cs.illinois.edu",
    "sp25-cs525-1210.cs.illinois.edu",
    "sp25-cs525-1218.cs.illinois.edu",
    "sp25-cs525-1219.cs.illinois.edu",
    "sp25-cs525-1220.cs.illinois.edu",
]

VM_HOSTS_11 = ["sp25-cs525-1211.cs.illinois.edu"]

COMMANDS = [
    "2",
    "Pacific_Rim"
]


# Username for ssh
USERNAME = "sj99"

# Tmux session name
SESSION_NAME = "peer_session"

def send_command_to_vm(host, command):
    tmux_cmd = (
        f"tmux send-keys -t {SESSION_NAME} '{command}' C-m"
    )
    full_cmd = f"ssh {USERNAME}@{host} \"{tmux_cmd}\""
    print(f"[INFO] Sending to {host}:\n  {command}")
    subprocess.run(full_cmd, shell=True)

def ensure_tmux_session_exists(host):
    check_cmd = f"ssh {USERNAME}@{host} 'tmux has-session -t {SESSION_NAME} 2>/dev/null || tmux new-session -d -s {SESSION_NAME}'"
    subprocess.run(check_cmd, shell=True)

def main():
    # command = input("💬 Enter the command to run on all VMs via tmux: ")

    for command in COMMANDS:

        for host in VM_HOSTS_EXCEPT_11:
            ensure_tmux_session_exists(host)
            send_command_to_vm(host, command)
            time.sleep(2)

        time.sleep(150)

        for host in VM_HOSTS_11:
            ensure_tmux_session_exists(host)
            send_command_to_vm(host, command)
            time.sleep(2)
        
        print("\n✅ Command sent to all VMs in tmux session:", SESSION_NAME)

if __name__ == "__main__":
    main()