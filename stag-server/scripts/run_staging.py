#!/usr/bin/python

"""
Configure and run tools
"""

import subprocess
import os
import sys

### Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

log.info("Start Workspace")

ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")

### Preserve docker environment variables and run supervisor process - main container process
log.info("Start supervisor")
## Print environment
log.info("Environment:")
root_env = ['sudo', '--preserve-env', 'env']
subprocess.run(root_env)
command = ['sudo', '--preserve-env','supervisord', '-n', '-c', '/etc/supervisor/supervisord.conf']
subprocess.run(command)