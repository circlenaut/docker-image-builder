#!/usr/bin/python

#@TODO
# - this is a placeholder

"""
Configure custom app service
"""

import os
import sys
import json
import bcrypt
import logging
import argparse
from urllib.parse import quote, urljoin
from subprocess   import run, call
import functions as func

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

### Load arguments
cli_opts = args.opts

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

ENV_APPS_PATH = os.getenv("APPS_PATH", "/apps")
ENV_APP_USER =  os.getenv("APP_USER", "admin")
ENV_APP_PASSWORD =  os.getenv("APP_PASSWORD", "password")
ENV_APP_ROOT_DIR = os.getenv("APP_ROOT_DIR", "/apps/app")
ENV_APP_BIND_ADDR = os.getenv("APP_BIND_ADDR", "0.0.0.0:8080")
ENV_APP_BASE_URL = os.getenv("VSCODE_BASE_URL", "/app")

### Clean up envs
application = "app"
proxy_base_url = func.clean_url(ENV_PROXY_BASE_URL)
host_base_url = func.clean_url(ENV_CADDY_VIRTUAL_BASE_URL)
app_base_url = func.clean_url(ENV_APP_BASE_URL )

### Set final base url
system_base_url = urljoin(host_base_url, proxy_base_url)
full_base_url = urljoin(system_base_url, app_base_url)
log.info(f"{application} base URL: '{full_base_url}'")

### Set config and data paths
config_dir = os.path.join(ENV_HOME, ".config", application)
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
apps_dir = os.path.normpath(ENV_APPS_PATH)
data_dir = os.path.normpath(ENV_DATA_PATH)
app_dir = os.path.normpath(ENV_APP_ROOT_DIR)

if not os.path.exists(app_dir): 
    os.makedirs(app_dir)
    log.warning(f"fixing permissions for '{ENV_USER}' on '{app_dir}'")
    func.recursive_chown(apps_dir, ENV_USER)

### Generate password hash
password = ENV_APP_PASSWORD.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
log.info(f"{application} password: '{ENV_APP_PASSWORD}'")
log.info(f"{application} hashed password: '{hashed_password}'")
os.environ['HASHED_PASSWORD'] = hashed_password

### Create config template
config_file = {
    "admin": ENV_APP_USER,
    "logging": {},
    "name": application,
    "host": "localhost",
    "port": ENV_APP_BIND_ADDR.split(":",1)[1],
    "proto": "http",
    "base_url": full_base_url,
}

### Write config file
config_path = os.path.join(config_dir, "settings.json")
config_json = json.dumps(config_file, indent = 4)

with open(config_path, "w") as f: 
    f.write(config_json)

log.debug(f"{application} config: '{config_path}'")
#log.debug(func.cat_file(config_path))
#log.debug(config_json)
log.debug(func.capture_cmd_stdout(f'cat {config_path}', os.environ.copy()))

### Create symlink to workspace
link_path = os.path.join(workspace_dir, os.path.basename(app_dir))
if os.path.exists(app_dir) and not os.path.exists(link_path):
    log.info(f"symlinking '{app_dir}'' to '{link_path}'")
    os.symlink(app_dir, link_path)