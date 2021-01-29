#!/usr/bin/python

"""
Configure caddy service
"""

import os
import sys
import json
import bcrypt
import logging
from urllib.parse import quote, urljoin
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

#@TODO: Turn this into a dictionary/function
### Read system envs
ENV_HOSTNAME = os.getenv("HOSTNAME", "localhost")
ENV_USER = os.getenv("WORKSPACE_USER", "coder")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_APPS_PATH = os.getenv("APPS_PATH", "/apps")
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
ENV_FB_PORT = os.getenv("FB_PORT", "8055")
ENV_FB_BASE_URL = os.getenv("FB_BASE_URL", "/data")
ENV_FB_ROOT_DIR = os.getenv("FB_ROOT_DIR", "/workspace")
ENV_VSCODE_BIND_ADDR = os.getenv("VSCODE_BIND_ADDR", "0.0.0.0:8300")
ENV_VSCODE_BASE_URL = os.getenv("VSCODE_BASE_URL", "/code")
ENV_APP_PORT = os.getenv("APP_PORT", "8080")
ENV_APP_BASE_URL = os.getenv("APP_BASE_URL", "/app")
ENV_APP_ROOT_DIR = os.getenv("APP_ROOT_DIR", "/apps/app")

### Clean up envs
application = "caddy"
proxy_base_url = clean_url(ENV_PROXY_BASE_URL)
host_fqdn = ENV_CADDY_VIRTUAL_HOST # @TODO: Not reading from env
host_port = ENV_CADDY_VIRTUAL_PORT
host_ip = "0.0.0.0"
host_proto = ENV_CADDY_VIRTUAL_PROTO
host_base_url = clean_url(ENV_CADDY_VIRTUAL_BASE_URL)
auto_https = True if ENV_CADDY_AUTO_HTTPS == "true" else False
enable_gzip = True if ENV_CADDY_PROXY_ENCODINGS_GZIP == "true" else False
enable_zstd = True if ENV_CADDY_PROXY_ENCODINGS_ZSTD == "true" else False
enable_templates = True if ENV_CADDY_PROXY_TEMPLATES == "true" else False

### Set config and data paths
config_dir = os.path.join(ENV_HOME, ".config", application)
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

storage = os.path.join(config_dir, "storage")
if not os.path.exists(storage): 
    os.mkdir(storage)

workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
apps_dir = os.path.normpath(ENV_APPS_PATH)
data_dir = os.path.normpath(ENV_DATA_PATH)
app_dir = os.path.normpath(ENV_APP_ROOT_DIR)

letsencrypt_staging = "https://acme-staging-v02.api.letsencrypt.org/directory"
letsencrypt_production = "https://acme-v02.api.letsencrypt.org/directory"
endpoint = letsencrypt_staging if ENV_CADDY_LETSENCRYPT_ENDPOINT == "dev" else letsencrypt_production

### Run checks
if not host_proto in ['http', 'https']:
    log.info(f"{application}: protocol '{proto}' is not valid! Exiting.")
    sys.exit()

### Define application settings
servers = dict()
servers["automatic_https"]: auto_https
servers['default'] = dict()
domains = dict()
domains[host_fqdn] = ""

vscode_settings = {
    "name": "vscode",
    "host": "localhost",
    "port": ENV_VSCODE_BIND_ADDR.split(":",1)[1],
    "proto": "http",
    "base_url": clean_url(ENV_VSCODE_BASE_URL),
    "enable_gzip": True,
    "enable_gzip": True,
    "enable_templates": True,
}

filebrowser_settings = {
    "name": "filebrowser",
    "host": "localhost",
    "port": ENV_FB_PORT,
    "proto": "http",
    "base_url": clean_url(ENV_FB_BASE_URL),
    "enable_gzip": True,
    "enable_gzip": True,
    "enable_templates": True,
}

app_settings = {
    "name": "app",
    "host": "localhost",
    "port": ENV_APP_PORT,
    "proto": "http",
    "base_url": clean_url(ENV_APP_BASE_URL),
    "enable_gzip": True,
    "enable_gzip": True,
    "enable_templates": True,
}

### Create sub-config templates
service_settings = [vscode_settings, filebrowser_settings, app_settings]

subroutes = list()
for service in service_settings:
    service_base_url = urljoin(host_base_url, service.get("base_url"))
    full_base_url = urljoin(proxy_base_url, service_base_url)
    log.info("{name} base url: '{url}'".format(name=service.get("name"), url=full_base_url))

    encodings = dict()
    if service.get("enable_gzip") or service.get("enable_zstd"):
        encodings = {
            "handle": [{
                "encodings": {},
                "handler": "encode"
            }]
        }
        if service.get("enable_gzip"):
            encodings["handle"][0]["encodings"]['gzip'] = dict()
        if service.get("enable_zstd"):
            encodings["handle"][0]["encodings"]['zstd']= dict()

    templates = dict()
    if service.get("enable_templates"):
        templates = {
            "handle": [{
                "handler": "templates"
            }]
        }

    subroute = {
                "handler": "subroute",
                "routes": [{
                    "handle": [{
                            "handler": "static_response",
                            "headers": {
                                "Location": [
                                f"{full_base_url}/"
                                ]
                            },
                            "status_code": 302
                        }
                    ],
                    "match": [{
                            "path": [
                                f"{full_base_url}"
                            ]
                        }
                    ]
                },
                {
                    "handle": [{
                            "handler": "subroute",
                            "routes": [{
                                "handle": [{
                                    "handler": "rewrite",
                                    "strip_path_prefix": f"{full_base_url}"
                                }]
                            },
                            {
                            "handle": [{
                                "handler": "reverse_proxy",
                                "upstreams": [{
                                "dial": "{}:{}".format(service.get("host"), service.get("port"))
                                }]
                            }]
                            },
                            encodings,
                            templates
                            ]
                        }],
                    "match": [{
                        "path": [
                            f"{full_base_url}/*"
                        ]
                    }]
                }]
            }
    subroutes.append(subroute)


if host_fqdn != None:
    if host_fqdn == "":
        match = []
    else:
        match = {            
            "host": [host_fqdn]
        }
    route = {
        "match": match,
        "handle": subroutes,
        "terminal": True
    }
if servers['default'].get('routes') == None:
    servers['default']['listen'] = [f"{host_ip}:{host_port}"]
    servers['default']['routes'] = [route]
    servers['default']['logs'] = {
        "logger_names": {
            host_fqdn: "common",
        }
    }
else:
    servers['default']['routes'].append(route)

### Create config template
config_file = {
    "admin": {
        "disabled": False,
        "listen": '',
        "enforce_origin": False,
        "origins": [''],
        "config": {
            "persist": False
        }
    },
    "logging": {
		"logs": {
            "default": {
                "exclude": [
                    "http.log.access.json",
                    "http.log.access.common",
                    "http.log.access.common_and_json"
                ]
            },
			"common": {
				"writer": {
                    "output": "stdout"
                },
                "encoder": {
                    "format": "single_field",
                    "field": "common_log"
                },
				"level": "",
				"sampling": {
					"interval": 0,
					"first": 0,
					"thereafter": 0
				},
				"include": ["http.log.access.common"],
			}
		}
    },
    "storage": {
        "module": "file_system",
	    "root": storage
    },
    "apps": {
        "http": {
            "http_port": int(ENV_CADDY_HTTP_PORT),
            "https_port": int(ENV_CADDY_HTTPS_PORT),
            "servers": servers
        },
        "tls": {
            "automation": {
                "policies": [{
                    "subjects": list(domains.keys()),
                    "issuers": [
                        {
                        "module": "acme",
                        "ca": endpoint,
                        "email": ENV_CADDY_LETSENCRYPT_EMAIL
                        },
                        {
                        "module": "internal",
                        "ca": "",
                        "lifetime": 0,
                        "sign_with_root": False
                        }
                    ],
                    "key_type": ""
                }]
            }
        }
    }
}

### Write config file
config_path = os.path.join(config_dir, "settings.json")
config_json = json.dumps(config_file, indent = 4)

with open(config_path, "w") as f: 
    f.write(config_json)

log.info(f"setting permissions on '{config_dir}' to '{ENV_USER}'")
run(['sudo', '--preserve-env', 'chown', '-R', f'{ENV_USER}:users', config_dir])

log.info(f"{application} config: '{config_path}'")
log.info(call(["cat", config_path]))