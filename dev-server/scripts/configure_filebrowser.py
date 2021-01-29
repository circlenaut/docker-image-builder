#!/usr/bin/python

"""
Configure filebrowser service
"""

import os
import sys
import json
import bcrypt
import logging
import argparse
from urllib.parse import quote, urljoin
from subprocess   import run
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

args, unknown = parser.parse_known_args()
if unknown:
    log.info("Unknown arguments " + str(unknown))

#@TODO: Turn this into a dictionary/function
### Read system envs
ENV_USER = os.getenv("WORKSPACE_USER", "coder")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")
ENV_WORKSPACE_AUTH_PASSWORD =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")
ENV_PROXY_BASE_URL = os.getenv("PROXY_BASE_URL", "/")
ENV_CADDY_VIRTUAL_BASE_URL = os.getenv("VIRTUAL_BASE_URL", "/")

ENV_FB_PORT = os.getenv("FB_PORT", "8055")
ENV_FB_BASE_URL = os.getenv("FB_BASE_URL", "/data")
ENV_FB_ROOT_DIR = os.getenv("FB_ROOT_DIR", "/workspace")

### Clean up envs
application = "filebrowser"
fb_port = int(ENV_FB_PORT)
proxy_base_url = func.clean_url(ENV_PROXY_BASE_URL)
host_base_url = func.clean_url(ENV_CADDY_VIRTUAL_BASE_URL)
fb_base_url = func.clean_url(ENV_FB_BASE_URL)

### Set final base url
system_base_url = urljoin(host_base_url, proxy_base_url)
full_base_url = urljoin(system_base_url, fb_base_url)
log.info(f"{application} base URL: '{full_base_url}'")

### Set config and data paths
config_dir = os.path.join(ENV_HOME, ".config", application)
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
data_dir = os.path.normpath(ENV_DATA_PATH)
db_path = os.path.join(ENV_HOME, f"{application}.db")

### Generate password hash
password = ENV_WORKSPACE_AUTH_PASSWORD.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
log.info(f"{application} password: '{ENV_WORKSPACE_AUTH_PASSWORD}'")
log.info(f"{application} hashed password: '{hashed_password}'")
os.environ['HASHED_PASSWORD'] = hashed_password

### Create config template
config_file = {
    "port": fb_port,
    "baseURL": full_base_url,
    "address": "",
    "log": "stdout",
    "database": db_path,
    "root": workspace_dir,
    "username": ENV_USER,
    "password": hashed_password
}    
    
### Write config file
config_path = os.path.join(config_dir, "settings.json")
config_json = json.dumps(config_file, indent = 4)

with open(config_path, "w") as f: 
    f.write(config_json)

log.info(f"{application} config: '{config_path}'")
log.info(run(["cat", config_path]))