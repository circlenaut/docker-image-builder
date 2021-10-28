#!/usr/bin/python

"""
Configure and run tools
"""

import argparse
import json
import logging
import pathlib
import os
import sys
from subprocess import run

import coloredlogs
import yaml

SCRIPTS_PATH = os.getenv("SCRIPTS_PATH", "/scripts"),
sys.path.append(SCRIPTS_PATH)
from functions_ import (
    capture_cmd_stdout as _capture_cmd_stdout,
)


### Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

### Enable argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--opts', type=json.loads, help='Set script arguments')

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

### load arguments
cli_opts = args.opts

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

### Set supervisor envs
supervisor_env = os.environ.copy()
supervisor_env['USER'] = supervisor_env.get("API_USER")
supervisor_env['HOME'] = pathlib.Path("/home").joinpath(supervisor_env.get("API_USER"))

### Start supervisor
log.info("Start supervisor")
# Print environment
log.debug("Environment:")
log.debug(_capture_cmd_stdout('env', supervisor_env))

# Execute
run(['supervisord', '-n', '-c', '/etc/supervisor/supervisord.conf'])
