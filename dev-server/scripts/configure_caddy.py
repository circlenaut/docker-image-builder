#!/usr/bin/python

"""
Configure caddy service
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
caddy_virtual_port = cli_env.get("CADDY_VIRTUAL_PORT")
caddy_virtual_host = cli_env.get("CADDY_VIRTUAL_HOST")
caddy_virtual_proto = cli_env.get("CADDY_VIRTUAL_PROTO")
caddy_virtual_base_url = cli_env.get("CADDY_VIRTUAL_BASE_URL")
caddy_proxy_encodings_gzip = cli_env.get("CADDY_PROXY_ENCODINGS_GZIP")
caddy_proxy_encodings_zstd = cli_env.get("CADDY_PROXY_ENCODINGS_ZSTD")
caddy_proxy_templates = cli_env.get("CADDY_PROXY_TEMPLATES")
caddy_letsencrypt_email = cli_env.get("CADDY_LETSENCRYPT_EMAIL")
caddy_letsencrypt_endpoint = cli_env.get("CADDY_LETSENCRYPT_ENDPOINT")
caddy_http_port = cli_env.get("CADDY_HTTP_PORT")
caddy_https_port = cli_env.get("CADDY_HTTPS_PORT")
caddy_auto_https = cli_env.get("CADDY_AUTO_HTTPS")
fb_port = cli_user.get("filebrowser").get("port")
fb_base_url = cli_user.get("filebrowser").get("base_url")
vscode_bind_addr = cli_user.get("vscode").get("bind_addr")
vscode_base_url = cli_user.get("vscode").get("base_url")
app_bind_addr = cli_user.get("app").get("bind_addr")
app_base_url = cli_user.get("app").get("base_url")

### Get user settings
user_name = cli_user.get("name")
user_group = cli_user.get("group")
user_home = cli_user.get("dirs").get("home").get("path")

### Clean up envs
application = "caddy"
proxy_base_url = func.clean_url(proxy_base_url)
host_fqdn = caddy_virtual_host # @TODO: Not reading from env
host_port = caddy_virtual_port
host_ip = "0.0.0.0"
host_proto = caddy_virtual_proto
host_base_url = func.clean_url(caddy_virtual_base_url)
auto_https = True if caddy_auto_https == "true" else False
enable_gzip = True if caddy_proxy_encodings_gzip == "true" else False
enable_zstd = True if caddy_proxy_encodings_zstd == "true" else False
enable_templates = True if caddy_proxy_templates == "true" else False

### Set config and data paths
config_dir = os.path.join(user_home, ".config", application)
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

storage = os.path.join(config_dir, "storage")
if not os.path.exists(storage): 
    os.mkdir(storage)

### Set certificate endpoint
letsencrypt_staging = "https://acme-staging-v02.api.letsencrypt.org/directory"
letsencrypt_production = "https://acme-v02.api.letsencrypt.org/directory"
if caddy_letsencrypt_endpoint == "dev":
    endpoint = letsencrypt_staging
elif caddy_letsencrypt_endpoint == "prod":
    endpoint = letsencrypt_production
elif caddy_letsencrypt_endpoint == "internal":
    #@TODO: Get internal certs working
    endpoint = letsencrypt_production = "set this up"
else:
    log.info(f"invalid letsencrypt endpoint: '{caddy_letsencrypt_endpoint}'")

### Run protocol check
if not host_proto in ['http', 'https']:
    log.critical(f"{application}: protocol '{proto}' is not valid! Exiting.")
    sys.exit()

### Define application route settings
servers = dict()
servers["automatic_https"]: auto_https
servers['default'] = dict()
domains = dict()
domains[host_fqdn] = ""

vscode_settings = {
    "name": "vscode",
    "host": "localhost",
    "port": vscode_bind_addr.split(":",1)[1],
    "proto": "http",
    "base_url": func.clean_url(vscode_base_url),
    "enable_gzip": True,
    "enable_gzip": True,
    "enable_templates": True,
}

filebrowser_settings = {
    "name": "filebrowser",
    "host": "localhost",
    "port": fb_port,
    "proto": "http",
    "base_url": func.clean_url(fb_base_url),
    "enable_gzip": True,
    "enable_gzip": True,
    "enable_templates": True,
}

app_settings = {
    "name": "app",
    "host": "localhost",
    "port": app_bind_addr.split(":",1)[1],
    "proto": "http",
    "base_url": func.clean_url(app_base_url),
    "enable_gzip": True,
    "enable_gzip": True,
    "enable_templates": True,
}

### Create application sub-config templates
service_settings = [vscode_settings, filebrowser_settings, app_settings]

subroutes = list()
for service in service_settings:
    service_base_url = urljoin(host_base_url, service.get("base_url"))
    full_base_url = urljoin(proxy_base_url, service_base_url) if service_base_url != "/" else ""
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
        match = [{          
            "host": [host_fqdn]
        }]
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
            "http_port": int(caddy_http_port),
            "https_port": int(caddy_https_port),
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
                        "email": caddy_letsencrypt_email
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

# fix permissions
log.info(f"setting permissions on '{config_dir}' to '{user_name}:{user_group}'")
func.recursive_chown(config_dir, user_name, user_group)

### Display final config
log.debug(f"{application} config: '{config_path}'")
log.debug(func.capture_cmd_stdout(f'cat {config_path}', cli_env))