#!/usr/bin/python

#@TODO
# - this is a placeholder

"""
Configure custom app service
"""

import os
import shutil
import sys
import json
import docker
import bcrypt
import logging
from pathlib      import Path
from urllib.parse import quote, urljoin
from copy         import copy
from subprocess   import run, call

def clean_url(base_url):
    # set base url
    url = base_url.rstrip("/").strip()
    # always quote base url
    url = quote(base_url, safe="/%")
    return url

### Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

### Read system envs
ENV_HOSTNAME = os.getenv("HOSTNAME", "localhost")
ENV_USER = os.getenv("SUDO_USER", "coder")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_WORKSPACE_AUTH_PASSWORD =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")
ENV_PROXY_BASE_URL = os.getenv("PROXY_BASE_URL", "/")
ENV_CADDY_VIRTUAL_PORT = os.getenv("VIRTUAL_PORT", "80")
ENV_CADDY_VIRTUAL_HOST = os.getenv("VIRTUAL_HOST", "")
ENV_CADDY_VIRTUAL_BIND_NET = os.getenv("VIRTUAL_BIND_NET", "proxy")
ENV_CADDY_VIRTUAL_PROTO = os.getenv("VIRTUAL_PROTO", "http")
ENV_CADDY_VIRTUAL_BASE_URL = os.getenv("VIRTUAL_BASE_URL", "/")
ENV_CADDY_PROXY_ENCODINGS_GZIP = os.getenv("PROXY_ENCODINGS_GZIP", "true")
ENV_CADDY_PROXY_ENCODINGS_ZSTD = os.getenv("PROXY_ENCODINGS_ZSTD", "true")
ENV_CADDY_PROXY_TEMPLATES = os.getenv("PROXY_TEMPLATES", "true")
ENV_CADDY_LETSENCRYPT_EMAIL = os.getenv("LETSENCRYPT_EMAIL", "admin@example.com")
ENV_CADDY_LETSENCRYPT_ENDPOINT = os.getenv("LETSENCRYPT_ENDPOINT", "prod")
ENV_CADDY_HTTP_PORT = os.getenv("HTTP_PORT", "80")
ENV_CADDY_HTTPS_ENABLE = os.getenv("HTTPS_ENABLE", "true")
ENV_CADDY_HTTPS_PORT = os.getenv("HTTPS_PORT", "443")
ENV_CADDY_AUTO_HTTPS = os.getenv("AUTO_HTTPS", "true")
ENV_CADDY_WORKSPACE_SSL_ENABLED = os.getenv("WORKSPACE_SSL_ENABLED", "false")
ENV_APPS_PATH = os.getenv("APPS_PATH", "/apps")
ENV_APP_USER =  os.getenv("APP_USER", "admin")
ENV_APP_PASSWORD =  os.getenv("APP_PASSWORD", "password")
ENV_APP_ROOT_DIR = os.getenv("APP_ROOT_DIR", "/apps/app")
ENV_APP_BIND_ADDR = os.getenv("APP_BIND_ADDR", "0.0.0.0:8080")
ENV_APP_BASE_URL = os.getenv("VSCODE_BASE_URL", "/app")

### Clean up envs
application = "app"
proxy_base_url = clean_url(ENV_PROXY_BASE_URL)
host_fqdn = ENV_HOSTNAME
host_port = ENV_CADDY_VIRTUAL_PORT
host_bind_ip = "0.0.0.0"
host_proto = ENV_CADDY_VIRTUAL_PROTO
host_base_url = clean_url(ENV_CADDY_VIRTUAL_BASE_URL)
auto_https = True if ENV_CADDY_AUTO_HTTPS == "true" else False
enable_gzip = True if ENV_CADDY_PROXY_ENCODINGS_GZIP == "true" else False
enable_zstd = True if ENV_CADDY_PROXY_ENCODINGS_ZSTD == "true" else False
enable_templates = True if ENV_CADDY_PROXY_TEMPLATES == "true" else False

#@TODO: add this later to enable proxy's base url
#clients = docker.from_env()
#host_container = clients.containers.get(ENV_HOSTNAME)
#host = host_container.name

### Set config and data paths
config_dir = os.path.join("/etc", application)
storage = os.path.join(config_dir, "storage")
if not os.path.exists(config_dir): os.mkdir(config_dir)
if not os.path.exists(storage): os.mkdir(storage)

workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
apps_dir = os.path.normpath(ENV_APPS_PATH)
data_dir = os.path.normpath(ENV_DATA_PATH)
app_dir = os.path.normpath(ENV_APP_ROOT_DIR)

if not os.path.exists(app_dir): 
    os.makedirs(app_dir)
    log.info(f"fixing permissions for '{ENV_USER}' on '{app_dir}'")
    run(['sudo', '--preserve-env', 'chown', '-R', f'{ENV_USER}:users', apps_dir])

### Generate password hash
password = ENV_APP_PASSWORD.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
log.info(f"{application} password: '{ENV_APP_PASSWORD}'")
log.info(f"{application} hashed password: '{hashed_password}'")
os.environ['HASHED_PASSWORD'] = hashed_password

### Run checks
if not host_proto in ['http', 'https']:
    log.info(f"{application}: protocol '{proto}' is not valid! Exiting.")
    sys.exit()

servers = dict()
servers["automatic_https"]: auto_https
servers['default'] = dict()
domains = dict()
domains[host_fqdn] = ""

### Define application settings
application_settings = {
    "name": application,
    "host": "localhost",
    "port": ENV_APP_BIND_ADDR.split(":",1)[1],
    "proto": "http",
    "base_url": clean_url(ENV_APP_BASE_URL),
    "enable_gzip": True,
    "enable_gzip": True,
    "enable_templates": True,
}

### Create config template
config_file = {
    "admin": {},
    "logging": {},
    "apps": {}
}

#def get_pip_

### Write config file
config_path = os.path.join(config_dir, f"{application}.json")
config_json = json.dumps(config_file, indent = 4)

with open(config_path, "w") as f: 
    f.write(config_json)

log.info(f"{application} config:")
log.info(call(["cat", config_path]))

### Create symlink to workspace
log.info(workspace_dir)
link_path = os.path.join(workspace_dir, os.path.basename(app_dir))
if not os.path.exists(link_path):
    log.info(f"symlinking '{app_dir}'' to '{link_path}'")
    os.symlink(app_dir, link_path)