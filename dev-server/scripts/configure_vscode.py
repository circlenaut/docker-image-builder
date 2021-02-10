#!/usr/bin/python

"""
Configure vscode service
"""

import os
import sys
import json
import bcrypt
import logging
import coloredlogs
import argparse
import json
from urllib.parse import quote, urljoin
from subprocess   import run, call, PIPE
import functions as func

def get_installed_extensions():
    extensions = list()
    cmd = ['code-server', '--list-extensions']

    result = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)

    output = result.stdout
    error = result.stderr
    return_code = result.returncode

    if return_code == 0:
        log.info('list extension command: success')
        extensions = output.split("\n")
    else:
        log.info('list extension command: error')
    return extensions

### Enable logging
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

### load arguments
cli_opts = args.opts
cli_env = args.env
cli_user = args.user
cli_settings = args.settings

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

### Get envs
proxy_base_url = cli_env.get("PROXY_BASE_URL")
caddy_virtual_base_url = cli_env.get("CADDY_VIRTUAL_BASE_URL")
#vscode_bind_addr = cli_env.get("VSCODE_BIND_ADDR")
#vscode_base_url = cli_env.get("VSCODE_BASE_URL")
vscode_bind_addr = cli_user.get("vscode").get("bind_addr")
vscode_base_url = cli_user.get("vscode").get("base_url")

### Get user settings
user_name = cli_user.get("name")
user_group = cli_user.get("group")
user_password = cli_user.get("password")
user_home = cli_user.get("dirs").get("home").get("path")

### Clean up envs
application = "vscode"
proxy_base_url = func.clean_url(proxy_base_url)
host_base_url = func.clean_url(caddy_virtual_base_url)
vscode_base_url = func.clean_url(vscode_base_url)

### Set final base url
system_base_url = urljoin(host_base_url, proxy_base_url)
full_base_url = urljoin(system_base_url, vscode_base_url)
log.info(f"{application} base URL: '{full_base_url}'")

### Set config and data paths
config_dir = os.path.join(user_home, ".config", application, "User")
if not os.path.exists(config_dir): os.makedirs(config_dir)

workspace_dir = os.path.normpath(cli_user.get("dirs").get("workspace").get("path"))
data_dir = os.path.normpath(cli_user.get("dirs").get("data").get("path"))

### Generate password hash
password = user_password.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
log.info(f"{application} password: '{user_password}'")
log.info(f"{application} hashed password: '{hashed_password}'")

### Create config template
theme = "Visual Studio Dark"
shell = "/usr/bin/zsh"
python_path = "/opt/conda/bin/python"

config_file = {
    "extensions.autoUpdate": False,
    "terminal.integrated.shell.linux": shell,
    "python.dataScience.useDefaultConfigForJupyter": False,
    "python.pythonPath": python_path,
    "files.exclude": {
        "**/.*": True
    },
    "python.jediEnabled": True,
    "terminal.integrated.inheritEnv": True,
    "workbench.colorTheme": theme
}

### Install VScode extensions
# Get currently installed extensions
installed_extensions = get_installed_extensions()

# Install new extensions if not already installed
for e in cli_user.get("vscode").get("extensions"):
    if e in installed_extensions:
        log.warning(f"vscode extension exists: '{e}'")
        continue
    else:
        log.info(f"vscode extension: '{e}'")
        run(['code-server', '--install-extension', e])

    # Removed: 
    #--install-extension RandomFractalsInc.vscode-data-preview \
    #--install-extension searKing.preview-vscode \
    #--install-extension SimonSiefke.svg-preview \
    #--install-extension Syler.ignore \
    #--install-extension VisualStudioExptTeam.vscodeintellicode \
    #--install-extension xpol.extra-markdown-plugins \

    # Docker commands
    #COPY --chown=$UNAME:$UNAME files/extensions/RandomFractalsInc.vscode-data-preview-2.2.0.vsix /tmp/RandomFractalsInc.vscode-data-preview-2.2.0.vsix
    #COPY --chown=$UNAME:$UNAME files/extensions/SimonSiefke.svg-preview-2.8.3.vsix /tmp/SimonSiefke.svg-preview-2.8.3.vsix
    #! code-server --install-extension /tmp/RandomFractalsInc.vscode-data-preview-2.2.0.vsix || true \
    #! code-server --install-extension /tmp/SimonSiefke.svg-preview-2.8.3.vsix || true

### Write config file
config_path = os.path.join(config_dir, "settings.json")
config_json = json.dumps(config_file, indent = 4)

with open(config_path, "w") as f: 
    f.write(config_json)

# fix permissions
log.info(f"setting permissions on '{config_dir}' to '{user_name}:{user_group}'")
func.recursive_chown(config_dir, user_name, user_group)

### Display final config
log.debug(f"{application} config: '{config_path}'")
log.debug(func.capture_cmd_stdout(f'cat {config_path}', cli_env))