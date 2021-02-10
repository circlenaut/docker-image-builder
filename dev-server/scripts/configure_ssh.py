#!/usr/bin/python

"""
Configure user ssh service
"""

import os
import sys
import logging
import coloredlogs
import argparse
import json
from subprocess import run
import functions as func

# Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

### Enable argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--opts', type=json.loads, help='Set script arguments')
parser.add_argument('--env', type=json.loads, help='Set script environment')
parser.add_argument('--user', type=json.loads, help='Load user settings')
parser.add_argument('--settings', type=json.loads, help='Load script settings')

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

### Load arguments
cli_opts = args.opts
cli_env = args.env
cli_user = args.user
cli_settings = args.settings

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

# Get user settings
user_name = cli_user.get("name")
user_group = cli_user.get("group")
user_home = cli_user.get("dirs").get("home").get("path")
pub_keys = cli_user.get("ssh").get("pub_keys")
configs = cli_user.get("ssh").get("configs")

# Set root user
root_user = "root"
root_group = "root"

### Set global envs
os.environ['USER'] = user_name
os.environ['HOME'] = user_home

### Setup config file
config_file = os.path.join(user_home, ".ssh", "config")

cfg_opts = {
    'hostname': 'Hostname',
    'port': 'Port',
    'user': 'User',
    'pub_key_auth': 'PubkeyAuthentication',
    'id_only': 'IdentitiesOnly',
    'id_file_path': 'IdentityFile'
}
if configs != None:
    for cfg in configs:
        if cfg.get("hostname") != None or not cfg.get("hostname").isspace():
            with open(config_file, "a") as f: 
                f.write("Host {}".format(cfg.get("hostname")) + "\n")
            for o, a in cfg_opts.items():
                if cfg.get(o) != None:
                    with open(config_file, "a") as f1: 
                        f1.write("    {opt} {val}".format(opt=a, val=cfg.get(o)) + "\n")
            with open(config_file, "a") as f1: 
                f1.write("\n")        
    func.chmod(config_file, "644")

# Display final config
log.debug(f"ssh config: '{config_file}'")
log.debug(func.capture_cmd_stdout(f'cat {config_file}', cli_env))

# Export environment for ssh sessions
#run("printenv > $HOME/.ssh/environment", shell=True)
with open(user_home + "/.ssh/environment", 'w') as fp:
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
if not os.path.isfile(user_home + "/.ssh/"+SSH_KEY_NAME):
    log.info("Creating new SSH Key ("+ SSH_KEY_NAME + ")")
    # create ssh key if it does not exist yet
    run("ssh-keygen -f {home}/.ssh/{key_name} -t ed25519 -q -N \"\" > /dev/null".format(home=user_home, key_name=SSH_KEY_NAME), shell=True)

# Copy public key to resources, otherwise nginx is not able to serve it
run("/bin/cp -rf " + user_home + "/.ssh/id_ed25519.pub /resources/public-key.pub", shell=True)

# Make sure that knonw hosts and authorized keys exist
run("touch " + user_home + "/.ssh/authorized_keys", shell=True)
run("touch " + user_home + "/.ssh/known_hosts", shell=True)

# echo "" >> ~/.ssh/authorized_keys will prepend a new line before the key is added to the file
run("echo "" >> " + user_home + "/.ssh/authorized_keys", shell=True)
# only add to authrized key if it does not exist yet within the file
run('grep -qxF "$(cat {home}/.ssh/{key_name}.pub)" {home}/.ssh/authorized_keys || cat {home}/.ssh/{key_name}.pub >> {home}/.ssh/authorized_keys'.format(home=user_home, key_name=SSH_KEY_NAME), shell=True)

# Authorize user's public keys
pub_key_auth_file = os.path.join(user_home, ".ssh", "authorized_keys")
for key in pub_keys:
    log.info(f"authorizing key: '{key}'")
    with open(pub_key_auth_file, "a") as f: 
        f.write(key + "\n")
# fix permissions
func.chmod(pub_key_auth_file, "600")

# Add identity to ssh agent -> e.g. can be used for git authorization
run("eval \"$(ssh-agent -s)\" && ssh-add " + user_home + "/.ssh/"+SSH_KEY_NAME + " > /dev/null", shell=True)

# Fix permissions
# https://superuser.com/questions/215504/permissions-on-private-key-in-ssh-folder
# https://gist.github.com/grenade/6318301
# https://help.ubuntu.com/community/SSH/OpenSSH/Keys

run(f"chmod 700 {user_home}/.ssh/", shell=True)
run(f"chmod 600 {user_home}/.ssh/" + SSH_KEY_NAME, shell=True)
run(f"chmod 644 {user_home}/.ssh/" + SSH_KEY_NAME + ".pub", shell=True)

# TODO Config backup does not work when setting these:
#run(f"chmod 644 {user_home}/.ssh/authorized_keys", shell=True)
#run(f"chmod 644 {user_home}/.ssh/known_hosts", shell=True)
#run(f"chmod 644 {user_home}/.ssh/config", shell=True)
#run(f"chmod 700 {user_home}/.ssh/", shell=True)
#run(f"chmod -R 600 {user_home}/.ssh/", shell=True)
#run(f"chmod 644 {user_home}/.ssh/authorized_keys", shell=True)
#run(f"chmod 644 {user_home}/.ssh/known_hosts", shell=True)
#run(f"chmod 644 {user_home}/.ssh/config", shell=True)
#run(f"chmod 644 {user_home}/.ssh/" + SSH_KEY_NAME + ".pub", shell=True)
###