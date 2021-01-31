#!/usr/bin/python

# System libraries
from __future__ import absolute_import, division, print_function

import argparse
import logging
import os
import random
import subprocess
import sys
import time
import json
from crontab import CronTab, CronSlices

# Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

### Enable argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--opts', type=json.loads, help='Set script arguments')
parser.add_argument('mode', type=str, default="backup", help='Either backup or restore the workspace configuration.',
                    choices=["backup", "restore", "schedule"])

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

### Load arguments
cli_opts = args.opts

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)

### Read system envs
WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
RESOURCE_FOLDER = os.getenv("RESOURCES_PATH", "/resources")
DATA_PATH = os.getenv("DATA_PATH", "/data")
ENV_USER = os.getenv("SUDO_USER", "coder")
USER_HOME = os.path.join("/home", ENV_USER)
CONFIG_BACKUP_ENABLED = os.getenv('CONFIG_BACKUP_ENABLED')
CONFIG_BACKUP_FOLDER = WORKSPACE_HOME + "/.workspace/backup/"

if args.mode == "restore":
    if CONFIG_BACKUP_ENABLED is None or CONFIG_BACKUP_ENABLED.lower() == "false" or CONFIG_BACKUP_ENABLED.lower() == "off":
        log.warning("Configuration Backup is not activated. Restore process will not be started.")
        sys.exit()

    log.info("Running config backup restore.")

    if not os.path.exists(CONFIG_BACKUP_FOLDER) or len(os.listdir(CONFIG_BACKUP_FOLDER)) == 0:
        log.warning("Nothing to restore. Config backup folder is empty.")
        sys.exit()
    
    rsync_restore =  "rsync -a -r -t -z -E -X -A " + CONFIG_BACKUP_FOLDER + " " + USER_HOME
    log.debug("Run rsync restore: " + rsync_restore)
    subprocess.run(rsync_restore, shell=True)
elif args.mode == "backup":
    if not os.path.exists(CONFIG_BACKUP_FOLDER):
        os.makedirs(CONFIG_BACKUP_FOLDER)
    
    log.info("Starting configuration backup.")
    backup_selection = "--include='/.config' \
                        --include='/.oh-my-zsh' \
                        --include='/.config/Code/' --include='/.config/Code/User/' --include='/.config/Code/User/settings.json' \
                        --include='/.gitconfig' \
                        --include='/filebrowser.db' \
                        --include='/.local/' --include='/.local/share/' --include='/.local/share/jupyter/' --include='/.local/share/jupyter/kernels/***' \
                        --include='/.jupyter/***' \
                        --include='/.vscode/***'"
    
    rsync_backup =  "rsync -a -r -t -z -E -X -A --delete-excluded --max-size=100m \
                        " + backup_selection + " \
                        --exclude='/.ssh/environment' --include='/.ssh/***' \
                        --exclude='*' " + USER_HOME + "/ " + CONFIG_BACKUP_FOLDER
    log.debug("Run rsync backup: " + rsync_backup)
    subprocess.run(rsync_backup, shell=True)

elif args.mode == "schedule":
    DEFAULT_CRON = "0 * * * *"  # every hour

    if CONFIG_BACKUP_ENABLED is None or CONFIG_BACKUP_ENABLED.lower() == "false" or CONFIG_BACKUP_ENABLED.lower() == "off":
        log.warning("Configuration Backup is not activated.")
        sys.exit()

    if not os.path.exists(CONFIG_BACKUP_FOLDER):
        os.makedirs(CONFIG_BACKUP_FOLDER)

    cron_schedule = DEFAULT_CRON
    # env variable can also be a cron scheadule
    if CronSlices.is_valid(CONFIG_BACKUP_ENABLED):
        cron_schedule = CONFIG_BACKUP_ENABLED
    
    # Cron does not provide enviornment variables, source them manually
    environment_file = os.path.join(RESOURCE_FOLDER, "environment.sh")
    with open(environment_file, 'w') as fp:
        for env in os.environ:
            if env != "LS_COLORS":
                fp.write("export " + env + "=\"" + os.environ[env] + "\"\n")

    os.chmod(environment_file, 0o777)

    script_file_path = os.path.realpath(__file__)
    command = ". " + environment_file + "; " + sys.executable + " '" + script_file_path + "' backup> /proc/1/fd/1 2>/proc/1/fd/2"
    cron = CronTab(user=True)

    # remove all other backup tasks
    cron.remove_all(command=command)

    job = cron.new(command=command)
    if CronSlices.is_valid(cron_schedule):
        log.info("Scheduling cron config backup task with with cron: " + cron_schedule)
        job.setall(cron_schedule)
        job.enable()
        cron.write()
    else:
        log.error("Failed to schedule config backup. Cron is not valid.")

    log.info("Running cron jobs:")
    for job in cron:
        log.info(job)
