#!/usr/bin/python

"""
Configure vscode service
"""

import os
import sys
import json
import bcrypt
import logging
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
parser.add_argument('--settings', type=json.loads, help='Load script settings')

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

# load arguments
cli_opts = args.opts
cli_settings = args.settings

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)

### Read system envs
ENV_USER = os.getenv("WORKSPACE_USER", "coder")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")
ENV_WORKSPACE_AUTH_PASSWORD =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")
ENV_PROXY_BASE_URL = os.getenv("PROXY_BASE_URL", "/")
ENV_CADDY_VIRTUAL_BASE_URL = os.getenv("VIRTUAL_BASE_URL", "/")

ENV_VSCODE_BIND_ADDR = os.getenv("VSCODE_BIND_ADDR", "0.0.0.0:8300")
ENV_VSCODE_BASE_URL = os.getenv("VSCODE_BASE_URL", "/code")

### Clean up envs
application = "vscode"
proxy_base_url = func.clean_url(ENV_PROXY_BASE_URL)
host_base_url = func.clean_url(ENV_CADDY_VIRTUAL_BASE_URL)
vscode_base_url = func.clean_url(ENV_VSCODE_BASE_URL)

### Set final base url
system_base_url = urljoin(host_base_url, proxy_base_url)
full_base_url = urljoin(system_base_url, vscode_base_url)
log.info(f"{application} base URL: '{full_base_url}'")

### Set config and data paths
config_dir = os.path.join(ENV_HOME, ".config", application, "User")
if not os.path.exists(config_dir): os.makedirs(config_dir)

workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
data_dir = os.path.normpath(ENV_DATA_PATH)

### Generate password hash
password = ENV_WORKSPACE_AUTH_PASSWORD.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
log.info(f"{application} password: '{ENV_WORKSPACE_AUTH_PASSWORD}'")
log.info(f"{application} hashed password: '{hashed_password}'")
os.environ['HASHED_PASSWORD'] = hashed_password

### Define application settings
application_settings = {
    "name": application,
    "host": "localhost",
    "port": ENV_VSCODE_BIND_ADDR.split(":",1)[1],
    "proto": "http",
    "base_url": func.clean_url(ENV_VSCODE_BASE_URL),
    "enable_gzip": True,
    "enable_gzip": True,
    "enable_templates": True,
}

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

# for testing
run(
    'code-server --install-extension ms-python.python',
    shell=True,
)

run(
    'code-server --install-extension almenon.arepl',
    shell=True,
)

### Install new vscode extensions
installed_extensions = get_installed_extensions()

### Install VScode extensions
for e in cli_settings.get("config").get("extensions"):
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

log.debug(f"{application} config: '{config_path}'")
#log.debug(call(["cat", config_path]))
#log.debug(func.cat_file(config_path))
#log.debug(config_json)
log.debug(func.capture_cmd_stdout(f'cat {config_path}', os.environ.copy()))