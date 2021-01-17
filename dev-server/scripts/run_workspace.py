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

### For direct subprocess call
code_server_env = os.environ.copy()
code_server_env['PASSWORD'] =  os.getenv("WORKSPACE_AUTH_PASSWORD", "alliance")
code_server_env['BIND_ADDR'] =  os.getenv("WORKSPACE_BIND_ADDR", "0.0.0.0:8300")
code_server_env['USER_DATA_DIR'] =  os.getenv("WORKSPACE_USER_DATA_DIR", ENV_WORKSPACE_HOME)

# Doesn't work for supervisor, but if it does, better
supervisor_env = os.environ.copy()
supervisor_env['ENV_WORKSPACE_HOME'] = os.getenv("WORKSPACE_HOME", "/workspace")
supervisor_env['ENV_RESOURCES_PATH'] = os.getenv("RESOURCES_PATH", "/resources")
supervisor_env['ENV_PASSWORD'] =  os.getenv("WORKSPACE_AUTH_PASSWORD", "alliance")

# For supervisor
os.environ['WORKSPACE_AUTH_PASSWORD'] = os.getenv("WORKSPACE_AUTH_PASSWORD", "alliance")
log.info("Code-server password is: '" + os.environ['WORKSPACE_AUTH_PASSWORD'] +"'")


# restore config on startup - if CONFIG_BACKUP_ENABLED - it needs to run before other configuration 
##subprocess.call("python " + ENV_RESOURCES_PATH + "/scripts/backup_restore_config.py restore", shell=True)

##log.info("Configure ssh service")
##subprocess.call("python " + ENV_RESOURCES_PATH + "/scripts/configure_ssh.py", shell=True)

log.info("Configure nginx service")
subprocess.call("python3 /scripts/configure_nginx.py", shell=True)


startup_custom_script = os.path.join(ENV_WORKSPACE_HOME, "on_startup.sh")

if os.path.exists(startup_custom_script):
    log.info("Run on_startup.sh user script from workspace folder")
    # run startup script from workspace folder - can be used to run installation routines on workspace updates
    subprocess.call("/bin/bash " + startup_custom_script, shell=True)

#command = ['code-server', '--host', '0.0.0.0', '--auth', 'password', '--port', '8300']
#subprocess.check_call(command, env=code_server_env)

### Preserve docker environment variables and run supervisor process - main container process
log.info("Start supervisor")
## Print environment
log.info("Environment:")
root_env = ['sudo', '--preserve-env', 'env']
subprocess.call(root_env)
command = ['sudo', '--preserve-env','supervisord', '-n', '-c', '/etc/supervisor/supervisord.conf']
subprocess.call(command)