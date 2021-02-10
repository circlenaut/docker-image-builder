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
import conda.cli.python_api as Conda
import datetime
from subprocess import run, call
from conda_parser import parse_environment
import functions as func

def get_conda_envs():
    proc = run(["conda", "info", "--json", "--envs"],
               text=True, capture_output=True)
    paths = json.loads(proc.stdout).get("envs")
    names = list()
    for e in paths:
        name = os.path.basename(e)
        names.append(name)
    return names

def conda_list(environment):
    proc = run(["conda", "list", "--json", "--name", environment],
               text=True, capture_output=True)
    return json.loads(proc.stdout)


def conda_install(environment, *package):
    proc = run(["conda", "install", "--quiet", "--name", environment] + packages,
               text=True, capture_output=True)
    return json.loads(proc.stdout)

def conda_create(environment_file):
    create_env = ['conda', 'env','create', '--file', environment_file]
    proc = run(create_env,
               text=True, capture_output=True)
    return proc.stdout

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

### Get envs
conda_env_path = cli_env.get("CONDA_ENV_PATH")

### Get user settings
user_name = cli_user.get("name")

### Set config and data paths
workspace_dir = os.path.normpath(cli_user.get("dirs").get("workspace").get("path"))
data_dir = os.path.normpath(cli_user.get("dirs").get("data").get("path"))

### Process env files
existing_envs = get_conda_envs()
log.info(f"existing conda environments: '{existing_envs}")

if not conda_env_path == "":
    conda_env_path = os.path.normpath(conda_env_path)
    if os.path.isfile(conda_env_path):
        with open(conda_env_path) as f:
            body = f.read()

        #force_solve = bool(request.args.get("force_solve", False))
        force_solve = False
        filename = os.path.basename(conda_env_path)
        conda_env = parse_environment(filename, body, force_solve)
        name = conda_env.get("name")
        if name in existing_envs:
            log.warning(f"environment exists: '{name}'")
        else:
            if conda_env.get("error") == None:
                log.info(f"reading '{conda_env_path}' and setting up environment: '{name}'")
                log.info("\n" + body)
                create_env = ['conda', 'env','create', '-f', conda_env_path]
                proc = conda_create(conda_env_path)
                log.info(proc)
            else:
                log.error(f"Invalid file: '{conda_env_path}'" + "\n" + body)
                log.debug(call(["env"], env=conda_env))
    else:
        log.error(f"error: file doesn't exist '{conda_env_path}'")
else:
    log.warning("No environments to create")

env_names = get_conda_envs()

env_dirs = os.listdir(data_dir)
for d in env_dirs:
    d_path = os.path.join(data_dir, d)
    if os.path.isdir(d_path):
        files = os.listdir(d_path)
        for f in files:
            if f == 'environment.yml':
                conda_env_path = os.path.join(d_path, f)
                log.info(f"reading '{conda_env_path}'")
                with open(conda_env_path) as f_env:
                    body = f_env.read()
                log.info("\n" + body)
                #force_solve = bool(request.args.get("force_solve", False))
                force_solve = False
                conda_env = parse_environment(f, body, force_solve)
                name = conda_env.get("name")
                #if name in env_names
                log.info(f"setting up environment: '{name}'")
                if name in env_names:
                    log.warning(f"environment exists: '{name}'")
                    continue
                proc = conda_create(conda_env_path)
                log.info(proc)
                link_path = os.path.join(workspace_dir, d)
                log.info(f"symlinking '{d_path}'' to '{link_path}'")
                os.symlink(d_path, link_path)