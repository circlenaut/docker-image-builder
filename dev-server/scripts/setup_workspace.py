#!/usr/bin/python

"""
Configure and run development environments
"""

import subprocess
import contextlib
import os
import sys
import json
import logging
import daiquiri
import conda.cli.python_api as Conda
from conda_parser import parse_environment

### Enable Logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

#daiquiri.setup(level=logging.INFO)

#logger = daiquiri.getLogger(__name__)
#logger.info("It works and log to stderr by default with color!")

ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")
ENV_CONDA_ENV_PATH = os.getenv("CONDA_ENV_PATH")

conda_envs_path = "/opt/conda/envs"
log.info(f"fixing permissions for: '{ENV_DATA_PATH}'")
#fix_data_perms = 
subprocess.run(['sudo', 'chown', '-R','coder:users', ENV_DATA_PATH])

log.info(f"fixing permissions for: '{conda_envs_path}'")
#fix_env_perms = ['sudo', 'chown', '-R','coder:users', conda_envs_path]
subprocess.run(['sudo', 'chown', '-R','coder:users', conda_envs_path])

def get_conda_envs():
    proc = subprocess.run(["conda", "info", "--json", "--envs"],
               text=True, capture_output=True)
    paths = json.loads(proc.stdout).get("envs")
    names = list()
    for e in paths:
        name = os.path.basename(e)
        names.append(name)
    return names
    #return json.loads(proc.stdout)

def conda_list(environment):
    proc = subprocess.run(["conda", "list", "--json", "--name", environment],
               text=True, capture_output=True)
    return json.loads(proc.stdout)


def conda_install(environment, *package):
    proc = subprocess.run(["conda", "install", "--quiet", "--name", environment] + packages,
               text=True, capture_output=True)
    return json.loads(proc.stdout)

def conda_create(environment_file):
    create_env = ['conda', 'env','create', '--file', environment_file]
    #proc = subprocess.Popen(create_env,
    #            stdout=subprocess.PIPE,
    #            stderr=subprocess.STDOUT,
    #            universal_newlines=True,
    #            )
  
    #proc = subprocess.Popen(['stdbuf', '-o0'] + create_env,
    #            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        
    #for line in iter(proc.stdout.readline, b''):
    #    log.info('{}'.format(line.rstrip()))
    proc = subprocess.run(create_env,
               text=True, capture_output=True)
    #log.info(proc)
    return proc.stdout

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
            log.info(f"environment exists: '{name}'")
        else:
            if conda_env.get("error") == None:
                log.info(f"reading '{ENV_CONDA_ENV_PATH}' and setting up environment: '{name}'")
                log.info("\n" + body)
                create_env = ['conda', 'env','create', '-f', conda_env_path]
                #log.info(subprocess.run(create_env))
                proc = conda_create(conda_env_path)
                log.info(proc)
            else:
                log.info(f"Invalid file: '{conda_env_path}'" + "\n" + body)
                log.info(conda_env)
    else:
        log.info(f"error: file doesn't exist '{conda_env_path}'")
else:
    log.info("No environments to create")

env_names = get_conda_envs()

env_dirs = os.listdir(ENV_DATA_PATH)
for d in env_dirs:
    d_path = os.path.join(ENV_DATA_PATH, d)
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
                    log.info(f"environment exists: '{name}'")
                    continue
                proc = conda_create(conda_env_path)
                log.info(proc)
                #log.info(conda_create(conda_env_path))
                #create_env = ['conda', 'env','create', '-f', conda_env_path]
                #log.info(subprocess.run(create_env))
                #log.info(
                #(stdout_str, stderr_str, return_code_int) = Conda.run_command(
                #    Conda.Commands.CREATE,
                #    '--file', conda_env_path,
                #    use_exception_handler=True, stdout=sys.stdout, stderr=sys.stderr
                #))

#envs = get_conda_envs().get("envs")

#env_names = list()
#for e in envs:
#    name = os.path.basename(e)
#    env_names.append(name)

#log.info(env_names)