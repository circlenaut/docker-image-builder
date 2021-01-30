#!/usr/bin/python

"""
Configure and run cron scripts
"""

import os
import sys
import argparse
from subprocess import run

# Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

### Enable argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--opts', type=json.loads, help='Set script arguments')
parser.add_argument('--settings', type=json.loads, help='Load script settings')

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

### Load arguments
cli_opts = args.opts

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)

#### Conifg Backup 
# backup config directly on startup (e.g. ssh key)
action = "backup"
log.info(f"backup script: '{action}'")
run(['sudo', '--preserve-env', 'python3', '/scripts/backup_restore_config.py', action])

# start backup restore config process
action = "schedule"
log.info(f"backup script: '{action}'")
run(['sudo', '--preserve-env', 'python3', '/scripts/backup_restore_config.py', action])