1. VPN to campus WiFi
2. Manually start up target VMs at [this link](https://vc.cs.illinois.edu/ui/app/vm;nav=h/urn:vmomi:VirtualMachine:vm-26453:d64189ca-33ea-416e-9afe-6ebe373be01c/summary)
3. Set range() in TARGET_VMS to match the VMs you want to run tasks on


# Running tests with worker.py

 - Make sure you run the simple_task to install kernelmodsextra on each VM. I've already installed it on 15-20.

 - always run load_sch_netem before running any commands that use tc

 - Set the range of VMs you want to test on when defining TARGET_VMS

 - Map VMs to regions
 - Map latencies to regions in a graph

 - When you're done, make sure to run simple_task clear_delays
 - Or run the standalone clear_delays script