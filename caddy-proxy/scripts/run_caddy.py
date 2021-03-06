#!/usr/bin/python

"""
Configure and run tools
"""

# @TODO
# x if virtual_host is not defined in any client, then default server is activated and bound to :443(default port)
# - Add reverse proxy attributes as env options in clients
# x Add check for if external ip/bind ip is set/valid
# x warn if container is part of multiple networks, skip if conflic arrises or bind only to the proxy net
# x Test multiple bind against another external ip
# - Check if missing any options from Jwilder
    #NETWORK_ACCESS=internal
    #SSL_POLICY
    #HTTPS_METHOD=redirect
    #HSTS=off

import subprocess
import os
import shutil
import sys
import json
import docker
import coloredlogs
import logging
from copy import copy
from urllib.parse import quote, urljoin

### Global Vars
global hosts_file
hosts_file = "/etc/hosts"

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

log.info("Starting Proxy")
ENV_DATA_PATH = os.path.normpath(os.getenv("DATA_PATH", "/apps"))

if ENV_DATA_PATH != "/apps":
    if not os.path.exists(ENV_DATA_PATH):
        data_dir = shutil.copytree("/apps", ENV_DATA_PATH)
        log.info(f"Data directory created: '{data_dir}'")
    else:
        log.warning(f"Data directory exists!: '{ENV_DATA_PATH}'")

ENV_LOG_VERBOSITY = os.getenv("LOG_VERBOSITY", "INFO")
ENV_HOSTNAME = os.getenv("HOSTNAME", "localhost")
ENV_USER = os.getenv("USER", "caddy")
ENV_BIND_IPS = os.getenv("BIND_IPS", "127.0.0.1").split(",")
ENV_SSL_ISSUER = os.getenv("SSL_ISSUER", "acme")
ENV_LETSENCRYPT_EMAIL = os.getenv("LETSENCRYPT_EMAIL", "admin@example.com")
ENV_LETSENCRYPT_ENDPOINT = os.getenv("LETSENCRYPT_ENDPOINT", "prod")
ENV_HTTP_PORT = os.getenv("HTTP_PORT", "80")
ENV_HTTPS_ENABLE = os.getenv("HTTPS_ENABLE", "true")
ENV_AUTO_HTTPS = os.getenv("AUTO_HTTPS", "true")
ENV_HTTPS_PORT = os.getenv("HTTPS_PORT", "443")
ENV_BASE_URL = os.getenv("BASE_URL", "/")

### Set verbosity level. log.info occasinally throws EOF errors with high verbosity
if ENV_LOG_VERBOSITY in [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL"
]:
    verbosity = ENV_LOG_VERBOSITY
else:
    log.error("invalid verbosity: '{}".format(ENV_LOG_VERBOSITY))
    verbosity = "INFO"

# Set log level
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)


host_bind_ips = list()
for i in ENV_BIND_IPS:
    i.replace(" ", "")
    host_bind_ips.append(i)
log.info(f"Bind IPs: '{host_bind_ips}'")

host_base_url = ENV_BASE_URL.rstrip("/").strip()
# always quote base url
host_base_url = quote(host_base_url, safe="/%")

clients = docker.from_env()
host_container = clients.containers.get(ENV_HOSTNAME)
hostname = host_container.name
client_ip_addrs = dict()

auto_https = True if ENV_AUTO_HTTPS == "true" else False

networks = dict()
host_ext_addrs = dict()
ext_ports = list()
ext_ips = list()
ext_protos = list()
for full_port, properties in host_container.attrs.get('NetworkSettings').get('Ports').items():
    #log.debug("{}-{}".format(full_port, properties))
    port, proto = full_port.split('/', 1)
    #log.debug(f"test {port}")
    #log.debug(f"type {type(port)}")
    host_ext_addrs[port] = dict()
    host_ext_addrs[port]['proto'] = proto
    ext_ports.append(port)
    ext_protos.append(proto)
    host_ext_addrs[port]['ext_ips'] = list()
    for attrs in properties:
        for a in attrs.items():
            if a[0] == 'HostIp':
                host_ext_addrs[port]['ext_ips'].append(a[1])
                ext_ips.append(a[1])
for net, properties in host_container.attrs.get('NetworkSettings').get('Networks').items():
    #log.debug("{}-{}".format(net, properties))
    for attr, value in properties.items():
        if attr == 'NetworkID':
            networks[net] = value

log.info(f"Ext Addrs '{host_ext_addrs}'")

for host_ext_port in [ENV_HTTP_PORT, ENV_HTTPS_PORT]:
    if host_ext_addrs.get(host_ext_port) == None:
        log.warning(f"'{host_container.name}' port '{host_ext_port}' is not a valid external port! Quiting.")
        quit()

proxy_clients = dict()
client_binds = dict()
client_nets = dict()
bind_map = dict()
for docker_net, net_id in networks.items():
    for c in clients.networks.get(net_id).containers:
        append_dict = dict()
        append_dict['client_nets'] = list(c.attrs.get('NetworkSettings').get('Networks').keys())
        
        if c.name == hostname:
            continue
        elif c.status == 'running':
            log.info(f"Checking Client: '{c.name}'")
            client_ip = c.attrs.get('NetworkSettings').get('Networks').get(docker_net).get('IPAddress')
            client_ip_addrs[c.name] = client_ip
            net_name = clients.networks.get(net_id).name.split("_", 1)[1]
            log.info(f"{c.name} - Net name: {net_name}")
            client_num_networks = len(c.attrs.get('NetworkSettings').get('Networks'))
            log.info(f"{c.name} - Num of nets: '{client_num_networks}'")
            for e in c.attrs.get('Config').get('Env'):
                if e != None:
                    var = e.split("=")[0]
                    value = e.split("=")[1]
                    #log.debug("{} - {}".format(var, value))
                    if var == 'VIRTUAL_HOST':
                        append_dict['virtual_host'] = value
                        #log.debug(f"Virtual Host: '{value}'")
                    elif var == 'VIRTUAL_BIND_IP':
                        if client_num_networks > 1:
                            if bind_map.get(net_name) == None:
                                # Containers with same bind_map need to be in the same network
                                bind_map[net_name] = value
                                append_dict['virtual_bind_ip'] = value
                            if bind_map.get(net_name) != value:
                                log.error(f"{c.name} - Bind '{value}' not part of '{net_name}' network!")
                                continue
                            elif bind_map.get(net_name) == value:
                                virtual_bind_exists = False
                                for i in c.attrs.get('Config').get('Env'):
                                    if i != None:
                                        sub_var = i.split("=")[0]
                                        sub_value = i.split("=")[1]
                                        if sub_var == 'VIRTUAL_BIND_NET':
                                            virtual_bind_exists = True
                                            if net_name == sub_value:
                                                if client_binds.get(value) == None:
                                                    client_binds[value] = dict()
                                                    host_ip = host_container.attrs.get('NetworkSettings').get('Networks').get(docker_net).get('IPAddress')
                                                    client_binds[value]['proxy_host'] = host_ip
                                                    client_binds[value]['clients'] = [c.name]
                                                else:
                                                    client_binds[value]['clients'].append(c.name)
                                                append_dict['virtual_bind_ip'] = value
                                                log.info(f"{c.name} - binding to: '{value}'")
                                if not virtual_bind_exists:
                                    log.warning(f"{c.name} - Must define VIRTUAL_BIND_NET")
                            else:
                                log.warning(f"{c.name} - Bind Map Exists: '{bind_map}'")
                        else:
                            if bind_map.get(net_name) == None:
                                # Containers with same bind_map need to be in the same network
                                bind_map[net_name] = value
                            append_dict['virtual_bind_ip'] = value
                            if client_binds.get(value) == None:
                                client_binds[value] = dict()
                                host_ip = host_container.attrs.get('NetworkSettings').get('Networks').get(docker_net).get('IPAddress')
                                client_binds[value]['proxy_host'] = host_ip
                                client_binds[value]['clients'] = [c.name]
                            else:
                                client_binds[value]['clients'].append(c.name)
                            log.info(f"{c.name} - Binding to: '{value}'")

                    elif var == 'VIRTUAL_BIND_NET':
                        append_dict['virtual_bind_net'] = value
                        log.info(f"{c.name} - Port: '{value}'")
                    elif var == 'VIRTUAL_PORT':
                        append_dict['virtual_port'] = value
                        log.info(f"{c.name} - Port: '{value}'")
                    elif var == 'VIRTUAL_PROTO':
                        append_dict['virtual_proto'] = value
                        log.info(f"{c.name} - Protocol: '{value}'")
                    elif var == 'VIRTUAL_BASE_URL':
                        append_dict['virtual_base_url'] = value
                        log.info(f"{c.name} - Base URL: '{value}'")
                    elif var == 'PROXY_ENCODINGS_GZIP':
                        # @TODO: Add value check?
                        append_dict['proxy_encodings_gzip'] = value
                        log.info(f"{c.name} - GZIP: '{value}'")
                    elif var == 'PROXY_ENCODINGS_ZSTD':
                        append_dict['proxy_encodings_zstd'] = value
                        log.info(f"{c.name} - ZSTD: '{value}'")
                    elif var == 'PROXY_TEMPLATES':
                        append_dict['proxy_templates'] = value
                        log.info(f"{c.name} - Templates: '{value}'")
         
            client_nets[c.name] = dict()
            for net, properties in c.attrs.get('NetworkSettings').get('Networks').items():
                try:
                    host_ip = host_container.attrs.get('NetworkSettings').get('Networks').get(net).get('IPAddress')
                except AttributeError:
                    log.error(f"Error getting ip for: '{c.name}'")
                    continue                 
                client_nets[c.name][net] = dict()
                client_nets[c.name][net]['name'] = net_name
                for attr, value in properties.items():
                    #log.debug(f"test: '{net}' - '{attr}' - '{value}'")
                    if attr == 'IPAddress':
                        client_nets[c.name][net]['proxy_host'] = host_ip
                        client_nets[c.name][net]['ip'] = value
                    if attr == 'NetworkID':
                        client_nets[c.name][net]['id'] = value
                        #client_ips.append(value)
            #append_dict['client_ips'] = client_ips
            #log.info(f"IPs: '{client_ips}'")
            #log.info(f"Nets: '{client_nets[c.name]}'")
            ### Docker DNS overrides hosts file 
            #for i in client_ips:
            #    with open(hosts_file, "a") as f: 
            #        f.write("{} {}\n".format(i, fqdn))
            proxy_clients[c.name] = copy(append_dict)

#        log.debug(c.attrs.keys())
#        log.debug(c.attrs.items())
#        log.debug(c.attrs.get('HostnamePath'))
#        log.debug(c.attrs.get('Args'))
#        log.debug(c.attrs.get('Name'))
#        log.debug(c.attrs.get('HostConfig'))
#        log.debug(c.stats)
    #container = client.containers.get(c)
    #for key, value in container.attrs.get('NetworkSettings').get('Networks').items():
    #log.debug(e.split(": ", maxsplit=1))

#for i in client_ip_addrs:
#    with open(hosts_file, "a") as f: 
#        f.write("{} {}\n".format(i, ENV_HOSTNAME))
log.info(f"Proxy clients: '{list(proxy_clients.keys())}'")

letsencrypt_staging = "https://acme-staging-v02.api.letsencrypt.org/directory"
letsencrypt_production = "https://acme-v02.api.letsencrypt.org/directory"
endpoint = letsencrypt_staging if ENV_LETSENCRYPT_ENDPOINT == "dev" else letsencrypt_production

caddy_data = os.path.join(ENV_DATA_PATH, "caddy")
log.info(f"Data Directory: '{caddy_data}'")
storage = os.path.join(caddy_data, "storage")
if not os.path.exists(storage): os.makedirs(storage)

servers = dict()
servers["automatic_https"]: auto_https
servers['default'] = dict()
domains = dict()
bind_exists = False
for client, envs in proxy_clients.items():
    log.info(f"{client} - Checking proxy")
    values = dict()
    # Default Values
    fqdn = "localhost"
    port = "80"
    bind_ip = "0.0.0.0"
    #nets = str()
    proto = "http"
    base_url = ""
    enable_gzip = False
    enable_zstd = False
    enable_templates = False
    for env, value in envs.items():
        if env == 'virtual_host':
            fqdn = value
            domains[fqdn] = ""
            values['fqdn'] = value
        elif env == 'virtual_port':
            port = value
            values['port'] = value
        elif env == 'virtual_bind_ip':
            bind_exists = True
            bind_ip = value
            values['bind_ip'] = value
        elif env == 'virtual_bind_net':
            bind_net = value
            values['bind_net'] = value
        elif env == 'client_nets':
            values['nets'] = value
            nets = value
        elif env == 'virtual_proto':
            proto = value
            values['proto'] = value
        elif env == 'virtual_base_url':
            base_url = value.rstrip("/").strip()
            # always quote base url
            base_url = quote(base_url, safe="/%")
            values['base_url'] = value
        elif env == 'proxy_encodings_gzip':
            enable_gzip = True
            values['gzip'] = value
        elif env == 'proxy_encodings_zstd':
            enable_zstd = True
            values['zstd'] = value
        elif env == 'proxy_templates':
            enable_templates = True
            values['templates'] = value
    #log.debug(f"'{client}' - Env Vars: '{list(values.items())}'")
    full_base_url = urljoin(host_base_url, base_url)
    log.info(f"{client} - App base URL: '{full_base_url}'")
    
    if not bind_ip in host_ext_addrs.get(ENV_HTTP_PORT).get('ext_ips') \
    or not bind_ip in host_ext_addrs.get(ENV_HTTPS_PORT).get('ext_ips'):
        log.warning(f"{client} - bind ip '{bind_ip}' is not a valid external ip! Skipping.")
        continue

    if not proto in ['http', 'https']:
        log.warning(f"{client} - protocol '{proto}' is not valid! Skipping.")
        continue

    encodings = dict()
    if enable_gzip or enable_zstd:
        encodings = {
            "handle": [{
                "encodings": {},
                "handler": "encode"
            }]
        }
        if enable_gzip:
            encodings["handle"][0]["encodings"]['gzip'] = dict()
        if enable_zstd:
            encodings["handle"][0]["encodings"]['zstd']= dict()

    templates = dict()
    if enable_templates:
        templates = {
            "handle": [{
                "handler": "templates"
            }]
        }
        
    if values.get('fqdn') != None:
        route = {
            "match": [{
                "host": [
                    fqdn
                ]
            }],
            "handle": [{
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
                                "dial": "{}:{}".format(client, port)
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
            }],
            "terminal": True
        }
        # Only clients with VIRTUAL_BIND_IP will be proxied
        #log.info(f"{client} - Bind exists: {bind_exists}")
        #log.info(f"{client} - Bind ip: {bind_ip}")
        #log.info(f"{client} - binds: {client_binds.get(bind_ip)}")
        if bind_exists and bind_ip != "0.0.0.0":
            if client_binds.get(bind_ip) != None:
                log.info(f"{client} - Binds: {client_binds}")
                proxy_ip = client_binds.get(bind_ip).get('proxy_host')
                listen = f"{proxy_ip}:{ENV_HTTPS_PORT}"
                log.info(f"{client} - Host Listen: '{listen}'")
                if servers.get(bind_ip) == None:
                    servers[bind_ip] = dict()
                    servers[bind_ip]['listen'] = [listen]
                    servers[bind_ip]['routes'] = [route]
                else:
                    servers[bind_ip]['routes'].append(route)
            else:
                log.warning(f"{client} - VIRTUAL_BIND_IP not defined. Skipping.  ")
        # If none have virtual binds, then all VIRTUAL_HOSTS will be proxied via default
        else:     
            if servers['default'].get('routes') == None:
                servers['default']['listen'] = [f"0.0.0.0:{ENV_HTTPS_PORT}"]
                servers['default']['routes'] = [route]
                servers['default']['routes'] = [route]
            else:
                servers['default']['routes'].append(route)
    else:
        log.error("FQDN not defined")

caddy_file = {
    "admin": {
        "disabled": False,
        "listen": '',
        "enforce_origin": False,
        "origins": [''],
        "config": {
            "persist": False
        }
    },
    "logging": {},
    "storage": {
        "module": "file_system",
	    "root": storage
    },
    "apps": {
        "http": {
            "http_port": int(ENV_HTTP_PORT),
            "https_port": int(ENV_HTTPS_PORT),
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
                        "email": ENV_LETSENCRYPT_EMAIL
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

log.info(f"Container IPs: '{client_ip_addrs}'")
log.info(f"Networks: '{networks}'")
log.info(f"Caddy Base URL: '{host_base_url}'")

caddyfile_path = "/apps/caddy/caddy.json"
caddy_json = json.dumps(caddy_file, indent = 4)
# Create Caddyfile
with open(caddyfile_path, "w") as caddyfile: 
    caddyfile.write(caddy_json)

log.debug("Caddy Config:")
log.debug(subprocess.call(["cat", caddyfile_path]))

#command = ['code-server', '--host', '0.0.0.0', '--auth', 'password', '--port', '8300']
#subprocess.check_call(command, env=code_server_env)

### Preserve docker environment variables and run supervisor process - main container process
log.info("Start supervisor")
### Fix Permissions
log.debug(F"Making '{ENV_USER}' owner of '{caddy_data}'")
caddy_permission = ['sudo', '--preserve-env', 'chown', '-R', f"{ENV_USER}:{ENV_USER}", caddy_data]
subprocess.call(caddy_permission)
## Print environment
log.debug("Environment:")
root_env = ['sudo', '--preserve-env', 'env']
subprocess.call(root_env)
command = ['sudo', '--preserve-env','supervisord', '-n', '-c', '/etc/supervisor/supervisord.conf']
subprocess.call(command)