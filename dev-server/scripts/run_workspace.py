#!/usr/bin/python

"""
Configure and run tools
"""

import os
import pwd
import sys
import argparse
import yaml
import json
import logging
import coloredlogs
import functions as func
from subprocess import run, call, Popen, PIPE

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

log.info("Start Workspace")

### Set supervisor envs
supervisor_env = os.environ.copy()
supervisor_env['USER'] = supervisor_env.get("WORKSPACE_USER")
supervisor_env['HOME'] = os.path.join("/home", supervisor_env.get("WORKSPACE_USER"))

### Start supervisor
log.info("Start supervisor")
# Print environment
log.debug("Environment:")
log.debug(func.capture_cmd_stdout('env', supervisor_env))

# Execute
run(['supervisord', '-n', '-c', '/etc/supervisor/supervisord.conf'])