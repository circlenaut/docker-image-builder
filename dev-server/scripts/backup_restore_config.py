#!/usr/bin/python

# System libraries
from __future__ import absolute_import, division, print_function

import argparse
import logging
import coloredlogs
import os
import random
#import subprocess
import sys
import time
import json
from subprocess import run
from crontab import CronTab, CronSlices

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
parser.add_argument('--mode', type=str, default="backup", help='Either backup or restore the workspace configuration.',
                    choices=["backup", "restore", "schedule"])

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

### Load arguments
cli_opts = args.opts
cli_env = args.env
cli_user = args.user

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)
        
### Get envs
config_backup_enabled = cli_env.get("CONFIG_BACKUP_ENABLED")

### Get user config and data paths
user_name = cli_user.get("name")
user_group = cli_user.get("group")
user_home = cli_user.get("dirs").get("home").get("path")

workspace_dir = cli_user.get("dirs").get("workspace").get("path")
resources_dir = cli_user.get("dirs").get("resources").get("path")
data_dir = cli_user.get("dirs").get("data").get("path")
apps_dir = cli_user.get("dirs").get("apps").get("path")
app_dir = cli_user.get("dirs").get("app").get("path")

### Set backup folder location
config_backup_folder = workspace_dir + "/.workspace/backup/"

### Restore action
if args.mode == "restore":
    if config_backup_enabled is None or config_backup_enabled.lower() == "false" or config_backup_enabled.lower() == "off":
        log.warning("Configuration Backup is not activated. Restore process will not be started.")
        sys.exit()

    log.info("Running config backup restore.")

    if not os.path.exists(config_backup_folder) or len(os.listdir(config_backup_folder)) == 0:
        log.warning("Nothing to restore. Config backup folder is empty.")
        sys.exit()
    

    rsync_restore_cmd = ['rsync', '-a', '-r', '-t', '-z', '-E', '-X', '-A', config_backup_folder, user_home]
    log.debug("Run rsync restore: " + ' '.join(rsync_restore_cmd))

    run(rsync_restore_cmd, env=cli_env)

### Backup action
elif args.mode == "backup":
    if not os.path.exists(config_backup_folder):
        os.makedirs(config_backup_folder)
    
    log.info("Starting configuration backup.")
    
    rsync_backup = ['rsync', '-a', '-r', '-t', '-z', '-E', '-X', '-A', '--max-size=100m']

    backup_selection = cli_user.get("backup_paths")

    backup_suffix = [config_backup_folder]
    
    for p in backup_selection:
        if os.path.exists(p):
            log.info(f"backing up directory: '{p}'")
            rsync_backup_cmd = rsync_backup + [p] + backup_suffix
            log.debug("Run rsync backup: " + ' '.join(rsync_backup_cmd))
            run(rsync_backup_cmd, env=cli_env)
        else:
            log.warning(f"directory does not exist: '{p}'")

### Schedule action
elif args.mode == "schedule":
    default_cron = "0 * * * *"  # every hour

    if config_backup_enabled is None or config_backup_enabled.lower() == "false" or config_backup_enabled.lower() == "off":
        log.warning("Configuration Backup is not activated.")
        sys.exit()

    if not os.path.exists(config_backup_folder):
        os.makedirs(config_backup_folder)

    cron_schedule = default_cron
    # env variable can also be a cron scheadule
    if CronSlices.is_valid(config_backup_enabled):
        cron_schedule = config_backup_enabled
    
    # Cron does not provide enviornment variables, source them manually
    environment_file = os.path.join(resources_dir, "environment.sh")
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
