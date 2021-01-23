#!/usr/bin/python

"""
Configure ssh service
"""

from subprocess import run
import os
import sys

# Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

ENV_USER = os.getenv("SUDO_USER", "coder")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")

# Export environment for ssh sessions
#run("printenv > $HOME/.ssh/environment", shell=True)
with open(ENV_HOME + "/.ssh/environment", 'w') as fp:
    for env in os.environ:
        if env == "LS_COLORS":
            continue
        # ignore most variables that get set by kubernetes if enableServiceLinks is not disabled
        # https://github.com/kubernetes/kubernetes/pull/68754
        if "SERVICE_PORT" in env.upper():
            continue
        if "SERVICE_HOST" in env.upper():
            continue
        if "PORT" in env.upper() and "TCP" in env.upper():
            continue
        fp.write(env + "=" + str(os.environ[env]) + "\n")

### Generate SSH Key (for ssh access, also remote kernel access)
# Generate a key pair without a passphrase (having the key should be enough) that can be used to ssh into the container
# Add the public key to authorized_keys so someone with the public key can use it to ssh into the container
SSH_KEY_NAME = "id_ed25519" # use default name instead of workspace_key
# TODO add container and user information as a coment via -C
if not os.path.isfile(ENV_HOME + "/.ssh/"+SSH_KEY_NAME):
    log.info("Creating new SSH Key ("+ SSH_KEY_NAME + ")")
    # create ssh key if it does not exist yet
    run("ssh-keygen -f {home}/.ssh/{key_name} -t ed25519 -q -N \"\" > /dev/null".format(home=ENV_HOME, key_name=SSH_KEY_NAME), shell=True)

# Copy public key to resources, otherwise nginx is not able to serve it
run("/bin/cp -rf " + ENV_HOME + "/.ssh/id_ed25519.pub /resources/public-key.pub", shell=True)

# Make sure that knonw hosts and authorized keys exist
run("touch " + ENV_HOME + "/.ssh/authorized_keys", shell=True)
run("touch " + ENV_HOME + "/.ssh/known_hosts", shell=True)

# echo "" >> ~/.ssh/authorized_keys will prepend a new line before the key is added to the file
run("echo "" >> " + ENV_HOME + "/.ssh/authorized_keys", shell=True)
# only add to authrized key if it does not exist yet within the file
run('grep -qxF "$(cat {home}/.ssh/{key_name}.pub)" {home}/.ssh/authorized_keys || cat {home}/.ssh/{key_name}.pub >> {home}/.ssh/authorized_keys'.format(home=ENV_HOME, key_name=SSH_KEY_NAME), shell=True)

# Add identity to ssh agent -> e.g. can be used for git authorization
run("eval \"$(ssh-agent -s)\" && ssh-add " + ENV_HOME + "/.ssh/"+SSH_KEY_NAME + " > /dev/null", shell=True)

# Fix permissions
# https://superuser.com/questions/215504/permissions-on-private-key-in-ssh-folder
# https://gist.github.com/grenade/6318301
# https://help.ubuntu.com/community/SSH/OpenSSH/Keys

run(f"chmod 700 {ENV_HOME}/.ssh/", shell=True)
run(f"chmod 600 {ENV_HOME}/.ssh/" + SSH_KEY_NAME, shell=True)
run(f"chmod 644 {ENV_HOME}/.ssh/" + SSH_KEY_NAME + ".pub", shell=True)

# TODO Config backup does not work when setting these:
#run(f"chmod 644 {ENV_HOME}/.ssh/authorized_keys", shell=True)
#run(f"chmod 644 {ENV_HOME}/.ssh/known_hosts", shell=True)
#run(f"chmod 644 {ENV_HOME}/.ssh/config", shell=True)
#run(f"chmod 700 {ENV_HOME}/.ssh/", shell=True)
#run(f"chmod -R 600 {ENV_HOME}/.ssh/", shell=True)
#run(f"chmod 644 {ENV_HOME}/.ssh/authorized_keys", shell=True)
#run(f"chmod 644 {ENV_HOME}/.ssh/known_hosts", shell=True)
#run(f"chmod 644 {ENV_HOME}/.ssh/config", shell=True)
#run(f"chmod 644 {ENV_HOME}/.ssh/" + SSH_KEY_NAME + ".pub", shell=True)
###