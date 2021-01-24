#!/usr/bin/python

"""
Configure and run tools
"""

import subprocess
import os
import sys
import yaml

### Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

log.info("Start Workspace")

### Read system envs
ENV_USER = os.getenv("USER", "coder")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")

### Clean up envs
workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
data_dir = os.path.normpath(ENV_DATA_PATH)

### Set application envs
code_server_env = os.environ.copy()
code_server_env['PASSWORD'] =  os.getenv("WORKSPACE_AUTH_PASSWORD", "alliance")
code_server_env['BIND_ADDR'] =  os.getenv("WORKSPACE_BIND_ADDR", "0.0.0.0:8300")
code_server_env['USER_DATA_DIR'] =  os.getenv("WORKSPACE_USER_DATA_DIR", ENV_WORKSPACE_HOME)

# Doesn't work for supervisor, but if it does, better
supervisor_env = os.environ.copy()
supervisor_env['ENV_WORKSPACE_HOME'] = os.getenv("WORKSPACE_HOME", "/workspace")
supervisor_env['ENV_RESOURCES_PATH'] = os.getenv("RESOURCES_PATH", "/resources")
supervisor_env['ENV_PASSWORD'] =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")

# For supervisor
os.environ['WORKSPACE_AUTH_PASSWORD'] = os.getenv("WORKSPACE_AUTH_PASSWORD", "alliance")
workspace_password = os.environ['WORKSPACE_AUTH_PASSWORD']
log.info(f"user '{ENV_USER}' password is: '{workspace_password}'")

### Run setup scripts
# restore config on startup - if CONFIG_BACKUP_ENABLED - it needs to run before other configuration 
subprocess.run("sudo --preserve-env python3 /scripts/backup_restore_config.py restore", shell=True)

log.info("Configure user")
subprocess.run("sudo --preserve-env python3 /scripts/configure_user.py", shell=True)

log.info("Configure ssh service")
subprocess.run("sudo --preserve-env python3 /scripts/configure_ssh.py", shell=True)

log.info("Configure caddy service")
subprocess.run("sudo --preserve-env python3 /scripts/configure_caddy.py", shell=True)

log.info("Configure filebrowser service")
subprocess.run("sudo --preserve-env python3 /scripts/configure_filebrowser.py", shell=True)

startup_custom_script = os.path.join(workspace_dir, "on_startup.sh")
if os.path.exists(startup_custom_script):
    log.info("Run on_startup.sh user script from workspace folder")
    # run startup script from workspace folder - can be used to run installation routines on workspace updates
    subprocess.run("/bin/bash " + startup_custom_script, shell=True)

# backup config directly on startup (e.g. ssh key)
subprocess.run("sudo --preserve-env python3 /scripts/backup_restore_config.py backup", shell=True)

# start backup restore config process
subprocess.run("sudo --preserve-env python3 /scripts/backup_restore_config.py schedule", shell=True)

### Fix permissions before creating envs and starting
log.info(f"fixing permissions for '{ENV_USER}'")
subprocess.run(['sudo', '--preserve-env', 'chown', '-R', f'{ENV_USER}:users', workspace_dir])
subprocess.run(['sudo', '--preserve-env', 'chown', '-R', f'{ENV_USER}:users', data_dir])

### Create conda environments
create_envs = ['/opt/conda/bin/conda', 'run','-n', 'base', 'python', '-u', '/scripts/setup_workspace.py']
subprocess.run(create_envs)

### Preserve docker environment variables and run supervisor process - main container process
log.info("Start supervisor")
# Print environment
log.info("Environment:")
root_env = ['sudo', '--preserve-env', 'env']
# Execute applications
subprocess.run(root_env)
command = ['sudo', '--preserve-env','supervisord', '-n', '-c', '/etc/supervisor/supervisord.conf']
subprocess.run(command)