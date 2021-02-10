#!/usr/bin/python

"""
Configure filebrowser service
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
#fb_port = cli_env.get("FB_PORT")
#fb_base_url = cli_env.get("FB_BASE_URL")
#fb_root_dir = cli_env.get("FB_ROOT_DIR")
fb_port = cli_user.get("filebrowser").get("port")
fb_base_url = cli_user.get("filebrowser").get("base_url")
fb_root_dir = cli_user.get("filebrowser").get("root_dir")

### Get user settings
user_name = cli_user.get("name")
user_group = cli_user.get("group")
user_password = cli_user.get("password")
user_home = cli_user.get("dirs").get("home").get("path")

### Clean up envs
application = "filebrowser"
proxy_base_url = func.clean_url(proxy_base_url)
host_base_url = func.clean_url(caddy_virtual_base_url)
fb_base_url = func.clean_url(fb_base_url)

### Set final base url
system_base_url = urljoin(host_base_url, proxy_base_url)
full_base_url = urljoin(system_base_url, fb_base_url)
log.info(f"{application} base URL: '{full_base_url}'")

### Set config and data paths
config_dir = os.path.join(user_home, ".config", application)
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

db_path = os.path.join(user_home, f"{application}.db")

### Generate password hash
password = user_password.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
log.info(f"{application} password: '{user_password}'")
log.info(f"{application} hashed password: '{hashed_password}'")

### Create config template
config_file = {
    "port": fb_port,
    "baseURL": full_base_url,
    "address": "",
    "log": "stdout",
    "database": db_path,
    "root": fb_root_dir,
    "username": user_name,
    "password": hashed_password
}    
    
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