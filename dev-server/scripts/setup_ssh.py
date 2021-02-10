#!/usr/bin/python

"""
Configure system ssh service
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
parser.add_argument('--users', type=json.loads, help='Load users settings')
parser.add_argument('--settings', type=json.loads, help='Load script settings')

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

### Load arguments
cli_opts = args.opts
cli_env = args.env
cli_users = args.users
cli_settings = args.settings

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

# Set root settings
root_user = "root"
root_group = "root"

### Set script name
application = "ssh config"

### Set config and data paths
config_dir = os.path.join("/etc", "ssh")
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

### Create config template
# set user access
allow_users = [root_user] + cli_users.get("users")
s = ' '
AllowUsers = s.join(allow_users)
log.info(f"users with ssh access: '{AllowUsers}'")

# match block
match_block = {
    "127.0.0.0/24": {
        "match": {
            "address": {
                "PasswordAuthentication": "yes",
                "PermitRootLogin": "yes"
            }
        }
    },
    "10.0.0.0/8": {
        "match": {
            "address": {
                "PasswordAuthentication": "yes",
                "PermitRootLogin": "no"
            }
        }
    },
    "172.0.0.0/8": {
        "match": {
            "address": {
                "PasswordAuthentication": "yes",
                "PermitRootLogin": "no"
            }
        }
    },
    "192.0.0.0/8": {
        "match": {
            "address": {
                "PasswordAuthentication": "yes",
                "PermitRootLogin": "no"
            }
        }
    },
    "120.31.58.0/24": {
        "match": {
            "address": {
                "PasswordAuthentication": "yes",
                "PermitRootLogin": "no"
            }
        }
    },
    "52.117.1.25": {
        "match": {
            "address": {
                "PasswordAuthentication": "yes",
                "PermitRootLogin": "no"
            }
        }
    }
}

# main config
config_file = {
    "SyslogFacility": "AUTH",
    "LogLevel": "INFO",
    "AllowUsers": AllowUsers,
    "AllowTcpForwarding": "yes",
    "PermitUserEnvironment": "yes",
    "ClientAliveInterval" : "60",
    "ClientAliveCountMax": "10",
    "PrintMotd": "no",
    "Banner": "none",
    "GatewayPorts": "clientspecified",
    "PasswordAuthentication": "no",
    "PubkeyAuthentication": "yes",
    "ChallengeResponseAuthentication": "no",
    "GSSAPIAuthentication": "no",
    "IgnoreRhosts": "yes",
    "HostbasedAuthentication": "no",
    "IgnoreUserKnownHosts": "no",
    "UsePAM": "no",
    "Subsystem": "sftp internal-sftp",
    "AllowAgentForwarding": "yes",
    "X11Forwarding": "yes",
    "X11UseLocalhost": "no",
    "X11DisplayOffset": "10",
    "StrictModes": "no",     
}

### Write config file
config_path = os.path.join(config_dir, "sshd_config")
config_mode = "644"
config_json = json.dumps(config_file, indent = 4)

# write main config
with open(config_path, "w") as f:
    for var, value in config_file.items():
        f.write(f"{var} {value}\n")

# write match block
with open(config_path, "a") as f:
    for value, config in match_block.items():
        for kind, values in config.get("match").items():
            f.write(f"Match {kind} {value}\n")
            for var, setting in values.items():
                f.write(f"    {var} {setting}\n")

# fix permissions
log.info(f"setting permissions on '{config_path}' to '{root_user}:{root_group}'")
func.chown(config_path, root_user, root_group)
log.info(f"setting mode of '{config_path}', to '{config_mode}'")
func.chmod(config_path, config_mode)

### Display final config
log.debug(f"{application} config: '{config_path}'")
log.debug(func.capture_cmd_stdout(f'cat {config_path}', cli_env))