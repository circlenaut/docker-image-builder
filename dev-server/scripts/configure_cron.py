#!/usr/bin/python

"""
Configure and run cron scripts
"""

import os
import sys
from subprocess import run

# Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

#### Conifg Backup 

# backup config directly on startup (e.g. ssh key)
action = "backup"
log.info(f"backup script: '{action}'")
run(['sudo', '--preserve-env', 'python3', '/scripts/backup_restore_config.py', action])

# start backup restore config process
action = "schedule"
log.info(f"backup script: '{action}'")
run(['sudo', '--preserve-env', 'python3', '/scripts/backup_restore_config.py', action])