import os

USER = os.environ["UI_USER"]
PASS = os.environ["UI_PASS"]


def test_sudo_command(c):
    result = c.sudo(f"mkdir /home/{USER}/testsudo", password=PASS)
    print(result.stdout)


def install_kernel_modules_extra(c):
    result = c.sudo("yum install -y kernel-modules-extra-$(uname -r)", password=PASS)
    print(result.stdout)
