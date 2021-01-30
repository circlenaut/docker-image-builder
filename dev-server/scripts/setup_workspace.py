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
import argparse
import contextlib
import conda.cli.python_api as Conda
from subprocess import run
from conda_parser import parse_environment

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
parser.add_argument('--settings', type=json.loads, help='Load script settings')

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

### Load arguments
cli_opts = args.opts

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)

#@TODO: Turn this into a dictionary/function
### Read system envs
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")
ENV_CONDA_ENV_PATH = os.getenv("CONDA_ENV_PATH")

### Clean up envs
workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
data_dir = os.path.normpath(ENV_DATA_PATH)

### Process env files
existing_envs = get_conda_envs()
log.info(f"existing conda environments: '{existing_envs}")

if not ENV_CONDA_ENV_PATH == None:
    conda_env_path = os.path.normpath(ENV_CONDA_ENV_PATH)
    if os.path.isfile(conda_env_path):
        with open(conda_env_path) as f:
            body = f.read()

        #force_solve = bool(request.args.get("force_solve", False))
        force_solve = False
        filename = os.path.basename(ENV_CONDA_ENV_PATH)
        conda_env = parse_environment(filename, body, force_solve)
        name = conda_env.get("name")
        if name in existing_envs:
            log.warning(f"environment exists: '{name}'")
        else:
            if conda_env.get("error") == None:
                log.info(f"reading '{ENV_CONDA_ENV_PATH}' and setting up environment: '{name}'")
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