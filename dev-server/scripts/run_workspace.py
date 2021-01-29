#!/usr/bin/python

"""
Configure and run tools
"""

import os
import pwd
import sys
import yaml
from subprocess import run, call, Popen, PIPE

### Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

log.info("Start Workspace")

### Set supervisor envs
supervisor_env = os.environ.copy()
supervisor_env['USER'] = supervisor_env.get("WORKSPACE_USER")
supervisor_env['HOME'] = os.path.join("/home", supervisor_env.get("WORKSPACE_USER"))

### Start supervisor
log.info("Start supervisor")
# Print environment
#log.info("Environment:")
#run(['env'], env=supervisor_env)

# Execute
run(['supervisord', '-n', '-c', '/etc/supervisor/supervisord.conf'])

#/etc/environment