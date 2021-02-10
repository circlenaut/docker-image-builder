#!/usr/bin/python

#@TODO
# - set force_solve as docker env

"""
Configure and run development environments
"""

import os
import sys
import json
import logging
import coloredlogs
import argparse
import contextlib
import datetime
from subprocess import run, call
import functions as func

def install_script(path):
    return_code = -1
    tracker = dict()
    tracker['file'] = os.path.basename(path)
    tracker['time'] = datetime.datetime.now().ctime()
    tracker['status'] = str()
    tracker['code'] = int()
    split = p.split(".", maxsplit=1)
    if len(split) == 2 and os.path.exists(path):
        if split[1] == "sh" and os.path.isfile(path):
            log.info(f"Installing script: '{path}'")
            return_code = shell_cmd.run_script(path)
        if return_code == 0:
            log.info("script installation: success")
            tracker['status'] = 'installed'
            tracker['code'] = return_code
        else:
            log.error("script installation: error")
            tracker['status'] = 'failed'
            tracker['code'] = return_code
    else:
        log.debug(f"Not a script: '{path}'")
        tracker = dict()
    return tracker

### Enable Logging
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

### Pull functions
shell_cmd = func.ShellCommand()

### Get user settings
user_name = cli_user.get("name")

### Set config and data paths
workspace_dir = os.path.normpath(cli_user.get("dirs").get("workspace").get("path"))
data_dir = os.path.normpath(cli_user.get("dirs").get("data").get("path"))

### Run custom user install scripts
install_tracker = dict()
install_tracker_json = dict()
install_dir = os.path.join(workspace_dir, "installers")
install_tracker_path = os.path.join(install_dir, "history")

log.critical(os.path.exists(install_tracker_path))
log.critical(func.is_json(install_tracker_path))
#log.critical(json.loads(install_tracker_path))

if os.path.exists(install_tracker_path) and func.is_json(install_tracker_path):
    log.debug(f"installation history exists at: '{install_tracker_path}'")
    install_tracker_file = func.read_file(install_tracker_path)
    install_tracker_json = json.loads(install_tracker_file)
if os.path.exists(install_dir):
    log.debug(f"installation dir exists: '{install_dir}'")
    installers = os.listdir(install_dir)
    for p in installers:
        installer_path = os.path.join(install_dir, p) 
        if os.path.isdir(installer_path) or not os.path.isfile(installer_path):
            continue
        if install_tracker.get(installer_path) == None:
            install_tracker[installer_path] = dict()
        previous = install_tracker_json.get(installer_path)
        log.critical(install_tracker_json)
        log.debug(f"previous install: '{previous}'")
        if previous == None:
            install_tracker[installer_path] = install_script(installer_path)
        elif previous.get("status") == 'failed':
            install_tracker[installer_path] = install_script(installer_path)
        elif previous.get("status") == 'installed':
            log.warning(f"script previously installed: '{installer_path}'")
            install_tracker[installer_path]['status'] = 'installed'
            continue
        else:
            log.error("unknown error")
            sys.exit()
    if len(install_tracker) == 0:
        log.info(f"no installation scripts found in '{install_dir}'")
    # Write config file
    installer_json = json.dumps(install_tracker, indent = 4)

    with open(install_tracker_path, "w") as f: 
        f.write(installer_json)
else:
    log.info(f"installer dir does not exist: '{install_dir}'")