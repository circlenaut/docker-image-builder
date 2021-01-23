#!/usr/bin/python

"""
Configure filebrowser service
"""

from subprocess import run
import os
import shutil
import sys
import json
import docker
import bcrypt
from pathlib import Path
from urllib.parse import quote, urljoin
from copy import copy

### Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

### Set  envs
ENV_HOSTNAME = os.getenv("HOSTNAME", "localhost")
#ENV_USER = os.getenv("USER", "coder")
ENV_USER = os.getenv("SUDO_USER", "coder")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_FB_PORT = os.getenv("FB_PORT", "8055")
ENV_FB_BASE_URL = os.getenv("FB_BASE_URL", "/data")
ENV_FB_ROOT_DIR = os.getenv("FB_ROOT_DIR", "/workspace")
ENV_VIRTUAL_BASE_URL = os.getenv("VIRTUAL_BASE_URL", "/")
ENV_PASSWORD =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")

#clients = docker.from_env()
#host_container = clients.containers.get(ENV_HOSTNAME)
#host = host_container.name

### Set base url
application = "filebrowser"
port = int(ENV_FB_PORT)
host_base_url = ENV_VIRTUAL_BASE_URL.rstrip("/").strip()
base_url = ENV_FB_BASE_URL.rstrip("/").strip()
# always quote base url
host_base_url = quote(host_base_url, safe="/%")
base_url = quote(base_url, safe="/%")

full_base_url = urljoin(host_base_url, base_url)
log.info(f"{application} base URL: '{full_base_url}'")

### Set paths
config_dir = os.path.join("/etc", application)
if not os.path.exists(config_dir):
    os.mkdir(config_dir)

workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
data_dir = os.path.normpath(ENV_DATA_PATH)
db_path = os.path.join(ENV_HOME, f"{application}.db")

### Generate password hash
password = ENV_PASSWORD.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
log.info(f"{application} password: '{ENV_PASSWORD}'")
log.info(f"{application} hashed password: '{hashed_password}'")
os.environ['HASHED_PASSWORD'] = hashed_password

### Generate filebrowser config
config_file = {
    "port": port,
    "baseURL": full_base_url,
    "address": "",
    "log": "stdout",
    "database": db_path,
    "root": workspace_dir,
    "username": ENV_USER,
    "password": hashed_password
}    
    
### Write config file
config_path = os.path.join(config_dir, f"{application}.json")
config_json = json.dumps(config_file, indent = 4)

with open(config_path, "w") as f: 
    f.write(config_json)

log.info(f"{application} config: '{config_path}'")
log.info(run(["cat", config_path]))