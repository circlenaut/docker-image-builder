#!/usr/bin/python

"""
Configure and run cron scripts
"""

import os
import sys
import argparse
import json
import logging
import coloredlogs
from subprocess import run

### Enable logging
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

### Load argumentss
cli_opts = args.opts
cli_env = args.env
cli_user = args.user
cli_settings = args.settings

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

### Create json dumps for passage into scripts
cli_opts_json = json.dumps(cli_opts)
cli_env_json = json.dumps(cli_env)
cli_user_json = json.dumps(cli_user)

#### Conifg Backup 
# backup config directly on startup (e.g. ssh key)
action = "backup"
log.info(f"backup script: '{action}'")
run(
    ['python', '/scripts/backup_restore_config.py', 
        '--opts', cli_opts_json,
        '--env', cli_env_json,
        '--user', cli_user_json,
        '--mode', action],
        env=cli_env    
)

# start backup restore config process
action = "schedule"
log.info(f"backup script: '{action}'")
run(
    ['python', '/scripts/backup_restore_config.py', 
        '--opts', cli_opts_json,
        '--env', cli_env_json,
        '--user', cli_user_json,
        '--mode', action],
        env=cli_env
)