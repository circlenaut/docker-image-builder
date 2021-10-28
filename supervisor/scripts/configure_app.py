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
import coloredlogs
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
parser.add_argument('--env', type=json.loads, help='Set script environment')
parser.add_argument('--user', type=json.loads, help='Load user settings')
parser.add_argument('--settings', type=json.loads, help='Load script settings')

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

### Load arguments
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
app_bind_addr = cli_user.get("app").get("bind_addr")
app_base_url = cli_user.get("app").get("base_url")
app_root_dir = cli_user.get("app").get("root_dir")
app_username = cli_user.get("app").get("user")
app_password = cli_user.get("app").get("password")

### Get user settings
user_name = cli_user.get("name")
user_group = cli_user.get("group")
user_password = cli_user.get("password")
user_home = cli_user.get("dirs").get("home").get("path")

### Clean up envs
application = "vscode"
proxy_base_url = func.clean_url(proxy_base_url)
host_base_url = func.clean_url(caddy_virtual_base_url)
app_base_url = func.clean_url(app_base_url)

### Set final base url
system_base_url = urljoin(host_base_url, proxy_base_url)
full_base_url = urljoin(system_base_url, app_base_url)
log.info(f"{application} base URL: '{full_base_url}'")

### Clean up envs
application = "app"

### Set final base url
system_base_url = urljoin(host_base_url, proxy_base_url)
full_base_url = urljoin(system_base_url, app_base_url)
log.info(f"{application} base URL: '{full_base_url}'")

### Set config and data paths
config_dir = os.path.join(user_home, ".config", application)
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

workspace_dir = os.path.normpath(cli_user.get("dirs").get("workspace").get("path"))
data_dir = os.path.normpath(cli_user.get("dirs").get("data").get("path"))
apps_dir = os.path.normpath(cli_user.get("dirs").get("apps").get("path"))
app_dir = os.path.normpath(cli_user.get("dirs").get("app").get("path"))

if not os.path.exists(app_dir): 
    os.makedirs(app_dir)
    log.warning(f"fixing permissions for '{user_name}' on '{app_dir}'")
    func.recursive_chown(apps_dir, user_name, user_group)

### Generate password hash
if not app_username == None:
    if not app_password == None: 
        password = app_password.encode()
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
        log.info(f"{application} password: '{app_password}'")
        log.info(f"{application} hashed password: '{hashed_password}'")
    else:
        log.warning(f"{application} password not set for : '{app_username}'")
else:
    log.warning(f"{application} user not set")

### Create config template
config_file = {
    "admin": app_username,
    "logging": {},
    "name": application,
    "host": "localhost",
    "port": app_bind_addr.split(":",1)[1],
    "proto": "http",
    "base_url": full_base_url,
}

### Write config file
config_path = os.path.join(config_dir, "settings.json")
config_json = json.dumps(config_file, indent = 4)

with open(config_path, "w") as f: 
    f.write(config_json)

# fix permissions
log.info(f"setting permissions on '{config_dir}' to '{user_name}:{user_group}'")
func.recursive_chown(config_dir, user_name, user_group)

# Create symlink to workspace
link_path = os.path.join(workspace_dir, os.path.basename(app_dir))
if os.path.exists(app_dir) and not os.path.exists(link_path):
    log.info(f"symlinking '{app_dir}'' to '{link_path}'")
    os.symlink(app_dir, link_path)

### Display final config
log.debug(f"{application} config: '{config_path}'")
log.debug(func.capture_cmd_stdout(f'cat {config_path}', cli_env))