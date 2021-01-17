#!/usr/bin/python

"""
Configure and start nginx service
"""

from subprocess import call
import os
import sys
from urllib.parse import quote, unquote

### Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")

### Basic Auth
ENV_NAME_SERVICE_USER = "WORKSPACE_AUTH_USER"
ENV_NAME_SERVICE_PASSWORD = "WORKSPACE_AUTH_PASSWORD"
ENV_SERVICE_USER = None
ENV_SERVICE_PASSWORD = None

if ENV_NAME_SERVICE_USER in os.environ:
    ENV_SERVICE_USER = os.environ[ENV_NAME_SERVICE_USER]
if ENV_NAME_SERVICE_PASSWORD in os.environ:
    ENV_SERVICE_PASSWORD = os.environ[ENV_NAME_SERVICE_PASSWORD]

NGINX_FILE = "/etc/nginx/nginx.conf"

# Replace base url placeholders with actual base url -> should 
decoded_base_url = unquote(os.getenv("WORKSPACE_BASE_URL", "").rstrip('/'))
call("sudo sed -i 's@{WORKSPACE_BASE_URL_DECODED}@" + decoded_base_url + "@g' " + NGINX_FILE, shell=True)
# Set url escaped url
encoded_base_url = quote(decoded_base_url, safe="/%")
call("sudo sed -i 's@{WORKSPACE_BASE_URL_ENCODED}@" + encoded_base_url + "@g' " + NGINX_FILE, shell=True)

call("sudo sed -i 's@{SHARED_LINKS_ENABLED}@" + os.getenv("SHARED_LINKS_ENABLED", "false").lower().strip() + "@g' " + NGINX_FILE, shell=True)


### PREPARE BASIC AUTH
if ENV_SERVICE_USER and ENV_SERVICE_PASSWORD:

    call("sudo sed -i 's/#auth_basic /auth_basic /g' " + NGINX_FILE, shell=True)
    call("sudo sed -i 's/#auth_basic_user_file/auth_basic_user_file/g' " + NGINX_FILE, shell=True)

    # create basic auth user
    call("echo '" + ENV_SERVICE_PASSWORD + "' | sudo htpasswd -b -i -c /etc/nginx/.htpasswd '"\
            + ENV_SERVICE_USER +"'", shell=True)