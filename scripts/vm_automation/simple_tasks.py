import os

USER = os.environ["UI_USER"]
PASS = os.environ["UI_PASS"]


# Not going to add this to VM on startup, we really only need to load this module for when we're testing
# Automatically gets unloaded on VM poweroff
def load_sch_netem(c):
    result = c.sudo(f"modprobe sch_netem", password=PASS)  # Load netem
    print(result.stdout)
    result = c.run(f"lsmod | grep sch_netem")  # Verify loaded
    print(result.stdout)

def test_sudo_command(c):
    result = c.sudo(f"mkdir /home/{USER}/testsudo", password=PASS)
    print(result.stdout)

def install_kernel_modules_extra(c):
    result = c.sudo("yum install -y kernel-modules-extra-$(uname -r)", password=PASS)
    print(result.stdout)

def remove_network_delay(c):
    c.sudo("tc qdisc del dev ens33 root", password=PASS)
