#!/usr/bin/python

"""
Main Workspace Run Script
"""

import os
import sys
import logging
import coloredlogs
import json
import math
import glob
import yaml
import yamale
import scripts.functions as func
from copy import copy
from subprocess   import run, call

### Enable logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)

log = logging.getLogger(__name__)
log.info("Starting...")

### Read YAML config file
#configs = list()
configs_list = dict()
#yaml_exts = ["yaml", "yml"]
config_path = str()

# Load config files with alternative extensions
#for ext in yaml_exts:
#    path = f'/scripts/config.{ext}'
#    if os.path.exists(path):
#        configs.append(path)

# Check if multiple config files exist and load the user defined one or system/user overwritten one
if os.path.exists('/scripts/config.yaml'):
    config_path = '/scripts/config.yaml'
    # Validate file
    schema = yamale.make_schema('/scripts/schema.yaml')
    data = yamale.make_data(config_path)
    valid_config = func.yaml_valid(schema, data, "INFO")
elif os.path.exists('/scripts/config.yml'):
    config_path = '/scripts/config.yml'
    # Validate file
    schema = yamale.make_schema('/scripts/schema.yaml')
    data = yamale.make_data(config_path)
    valid_config = func.yaml_valid(schema, data, "INFO")
elif os.path.exists('/scripts/config.yml') and os.path.exists('/scripts/config.yaml'):
    config_path = '/scripts/config.yml'
    log.warning("both config.yaml and config.yml exists, using config.yml")
    if os.path.exists('/scripts/config.yaml'): os.remove('/scripts/config.yaml')
    # Validate file
    schema = yamale.make_schema('/scripts/schema.yaml')
    data = yamale.make_data(config_path)
    valid_config = func.yaml_valid(schema, data, "INFO") 
else:
    log.debug("No yaml config files available to load")


# Load config as yaml object
if os.path.exists(config_path):
    if valid_config:
        log.info(f"Loading config file: '{config_path}'")
        with open(config_path, "r") as f:
            configs_list = yaml.load(f, Loader=yaml.FullLoader)
        log.debug(configs_list)
else:
    log.debug(f"Config does not exist: '{config_path}'")


### Read or set docker default envs
docker_env = {
    'LOG_VERBOSITY': os.getenv("LOG_VERBOSITY", "INFO"),
    'CONFIG_BACKUP_ENABLED': os.getenv("CONFIG_BACKUP_ENABLED", "true"),
    'WORKSPACE_USER': os.getenv("WORKSPACE_AUTH_USER", "coder"),
    'WORKSPACE_GROUP': os.getenv("WORKSPACE_AUTH_GROUP", "users"),
    'WORKSPACE_USER_SHELL': os.getenv("WORKSPACE_USER_SHELL", "zsh"),
    'WORKSPACE_USER_PASSWORD': os.getenv("WORKSPACE_AUTH_PASSWORD", "password"),
    'RESOURCES_PATH': os.getenv("RESOURCES_PATH", "/resources"),
    'WORKSPACE_HOME': os.getenv("WORKSPACE_HOME", "/workspace"),
    'APPS_PATH': os.getenv("APPS_PATH", "/apps"),
    'DATA_PATH': os.getenv("DATA_PATH", "/data"),
    'PROXY_BASE_URL': os.getenv("PROXY_BASE_URL", "/"),
    'ZSH_PROMPT': os.getenv("ZSH_PROMPT", "none"),
    'ZSH_THEME': os.getenv("ZSH_THEME", "spaceship"),
    'ZSH_PLUGINS': os.getenv("ZSH_PLUGINS", "all"),
    'CONDA_ENV_PATH': os.getenv("CONDA_ENV_PATH", ""), 
    'CADDY_VIRTUAL_PORT': os.getenv("VIRTUAL_PORT", "80"),
    'CADDY_VIRTUAL_HOST': os.getenv("VIRTUAL_HOST", ""),
    'CADDY_VIRTUAL_BIND_NET': os.getenv("VIRTUAL_BIND_NET", "proxy"),
    'CADDY_VIRTUAL_PROTO': os.getenv("VIRTUAL_PROTO", "http"),
    'CADDY_VIRTUAL_BASE_URL': os.getenv("VIRTUAL_BASE_URL", "/"),
    'CADDY_PROXY_ENCODINGS_GZIP': os.getenv("PROXY_ENCODINGS_GZIP", "true"),
    'CADDY_PROXY_ENCODINGS_ZSTD': os.getenv("PROXY_ENCODINGS_ZSTD", "true"),
    'CADDY_PROXY_TEMPLATES': os.getenv("PROXY_TEMPLATES", "true"),
    'CADDY_LETSENCRYPT_EMAIL': os.getenv("LETSENCRYPT_EMAIL", "admin@example.com"),
    'CADDY_LETSENCRYPT_ENDPOINT': os.getenv("LETSENCRYPT_ENDPOINT", "dev"),
    'CADDY_HTTP_PORT': os.getenv("HTTP_PORT", "80"),
    'CADDY_HTTPS_ENABLE': os.getenv("HTTPS_ENABLE", "true"),
    'CADDY_HTTPS_PORT': os.getenv("HTTPS_PORT", "443"),
    'CADDY_AUTO_HTTPS': os.getenv("AUTO_HTTPS", "true"),
    'CADDY_WORKSPACE_SSL_ENABLED': os.getenv("WORKSPACE_SSL_ENABLED", "false"),
    'FB_PORT': os.getenv("FB_PORT", "8055"),
    'FB_BASE_URL': os.getenv("FB_BASE_URL", "/data"),
    'FB_ROOT_DIR': os.getenv("FB_ROOT_DIR", "/workspace"),
    'VSCODE_BIND_ADDR': os.getenv("VSCODE_BIND_ADDR", "0.0.0.0:8300"),
    'VSCODE_BASE_URL': os.getenv("VSCODE_BASE_URL", "/code"),
    'APP_BIND_ADDR': os.getenv("APP_BIND_ADDR", "0.0.0.0:8080"),
    'APP_BASE_URL': os.getenv("APP_BASE_URL", "/app"),
    'APP_ROOT_DIR': os.getenv("APP_ROOT_DIR", "/apps/app"),
    'APP_USER': os.getenv("APP_USER", "admin"),
    'APP_PASSWORD': os.getenv("APP_PASSWORD", "password")
}

### Set verbosity level. log.info occasinally throws EOF errors with high verbosity
if docker_env.get("LOG_VERBOSITY") in [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL"
]:
    verbosity = docker_env.get("LOG_VERBOSITY")
else:
    log.info("invalid verbosity: '{}".format(docker_env.get("LOG_VERBOSITY")))
    verbosity = "INFO"

### opts_json cli options
opts = {
    "verbosity": verbosity
}

log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

### Reconcile docker env var with corresponding config setting
system_configs = dict()
# copy and save user configs
users_config_copy = copy(configs_list["users"])

# if system not configured in yaml, then set to docker envs
if configs_list.get("system") == None:
    log.info(f"System not defined in yaml config file. Importing settings from docker env.")
    for env, value in docker_env.items():
        log.debug(f"setting: '{env.lower()}' --> '{value}'")
        system_configs[env.lower()] = value
    # copy into system key
    configs_list["system"] = copy(system_configs)
    # copy users back
    configs_list["users"] = copy(users_config_copy)

# reconcile if env appears in both
else:
    for env, value in docker_env.items():
        for config, setting in configs_list.get("system").items():
            if config == env.lower():
                if setting == value:
                    log.debug(f"yaml config same as docker environment value: '{config}' --> '{setting}'")
                    system_configs[config] = value
                else:
                    log.warning(f"using config setting instead of docker environment value - {config}: '{value}'--> '{setting}'")
                    system_configs[config] = setting
        if not env.lower() in list(configs_list.get("system").keys()):
            log.debug(f"not set in yaml config, setting: '{env.lower()}' --> '{value}'")
            system_configs[env.lower()] = value
    # copy into system key
    configs_list["system"] = copy(system_configs)
    # copy users back
    configs_list["users"] = copy(users_config_copy)
    
### Reset verbosity level according to yaml file. log.info occasinally throws EOF errors with high verbosity
if configs_list.get("system").get("log_verbosity") in [
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL"
]:
    verbosity = configs_list.get("system").get("log_verbosity")
else:
    log.info("invalid verbosity: '{}".format(configs_list.get("system").get("log_verbosity")))
    verbosity = "INFO"

### opts_json cli options
opts = {
    "verbosity": verbosity
}

log.setLevel(verbosity)

default_user = [{
    'name': configs_list.get("system").get("workspace_user"), 
    'group': configs_list.get("system").get("workspace_group"), 
    'uid': "1000", 
    'gid': "100", 
    'shell': configs_list.get("system").get("workspace_user_shell"), 
    'password': configs_list.get("system").get("workspace_user_password"), 
    'directories': [
        {
            'name': 'home', 
            'path': os.path.join("/home", configs_list.get("system").get("workspace_user")), 
            'mode': '755'
        }, 
        {
            'name': 'resources', 
            'path': configs_list.get("system").get("resources_path"), 
            'mode': '755'
        }, 
        {
            'name': 'workspace', 
            'path': configs_list.get("system").get("workspace_home"), 
            'mode': '755'
        }, 
        {
            'name': 'data', 
            'path': configs_list.get("system").get("data_path"), 
            'mode': '755'
        }, 
        {
            'name': 'apps', 
            'path': configs_list.get("system").get("apps_path"), 
            'mode': '755'
        }, 
        {
            'name': 'app', 
            'path': configs_list.get("system").get("app_root_dir"), 
            'mode': '755'
        }], 
    'backup_paths': [
        f'/home/{configs_list.get("system").get("workspace_user")}/.config',
        f'/home/{configs_list.get("system").get("workspace_user")}/.ssh',
        f'/home/{configs_list.get("system").get("workspace_user")}/.zshrc',
        f'/home/{configs_list.get("system").get("workspace_user")}/.bashrc',
        f'/home/{configs_list.get("system").get("workspace_user")}/.profile',
        f'/home/{configs_list.get("system").get("workspace_user")}/.condarc',
        f'/home/{configs_list.get("system").get("workspace_user")}/.oh-my-zsh',
        f'/home/{configs_list.get("system").get("workspace_user")}/.gitconfig',
        f'/home/{configs_list.get("system").get("workspace_user")}/filebrowser.db',
        f'/home/{configs_list.get("system").get("workspace_user")}/.local',
        f'/home/{configs_list.get("system").get("workspace_user")}/.conda',
        f'/home/{configs_list.get("system").get("workspace_user")}/.vscode',
        f'/home/{configs_list.get("system").get("workspace_user")}/.jupyter'
    ], 
    'conda': {
        'env': ''
    }, 
    'zsh': {
        'set_prompt': configs_list.get("system").get("zsh_prompt"), 
        'set_theme': configs_list.get("system").get("zsh_theme"), 
        'set_plugins': configs_list.get("system").get("zsh_plugins"), 
        'prompt': [
            'https://github.com/sindresorhus/pure'
        ], 
        'theme': [
            'https://github.com/romkatv/powerlevel10k', 
            'https://github.com/denysdovhan/spaceship-prompt', 
            'https://github.com/sobolevn/sobole-zsh-theme'
        ], 
        'plugins': [
            'git', 
            'k', 
            'extract', 
            'cp', 
            'yarn', 
            'npm', 
            'supervisor', 
            'rsync', 
            'command-not-found', 
            'autojump', 
            'colored-man-pages', 
            'git-flow', 
            'git-extras', 
            'python', 
            'zsh-autosuggestions', 
            'history-substring-search', 
            'zsh-completions', 
            'ssh-agent', 
            'https://github.com/zsh-users/zsh-autosuggestions', 
            'https://github.com/zsh-users/zsh-completions', 
            'https://github.com/zsh-users/zsh-syntax-highlighting', 
            'https://github.com/zsh-users/zsh-history-substring-search', 
            'https://github.com/supercrabtree/k'
        ]},
    'ssh': {
        'pub_keys': [''],
        'configs': [{
            'hostname': '', 
            'port': '', 
            'user': '',
            'pub_key_auth': '',
            'id_only': '',
            'id_file_path': ''
        }]
    },
    'filebrowser': {
        'port': configs_list.get("system").get("fb_port"), 
        'base_url': configs_list.get("system").get("fb_base_url"), 
        'root_dir': configs_list.get("system").get("fb_root_dir")
    }, 
    'vscode': {
        'bind_addr': configs_list.get("system").get("vscode_bind_addr"), 
        'base_url': configs_list.get("system").get("vscode_base_url"), 
        'extensions': [
            'ms-python.python', 
            'almenon.arepl', 
            'batisteo.vscode-django', 
            'bierner.color-info', 
            'bierner.markdown-footnotes', 
            'bierner.markdown-mermaid', 
            'bierner.markdown-preview-github-styles', 
            'CoenraadS.bracket-pair-colorizer-2', 
            'DavidAnson.vscode-markdownlint', 
            'donjayamanne.githistory', 
            'donjayamanne.python-extension-pack', 
            'eamodio.gitlens', 
            'hbenl.vscode-test-explorer', 
            'henriiik.docker-linter', 
            'kamikillerto.vscode-colorize', 
            'kisstkondoros.vscode-gutter-preview', 
            'littlefoxteam.vscode-python-test-adapter', 
            'magicstack.MagicPython', 
            'ms-azuretools.vscode-docker', 
            'ms-toolsai.jupyter', 
            'naumovs.color-highlight', 
            'shd101wyy.markdown-preview-enhanced', 
            'streetsidesoftware.code-spell-checker', 
            'tht13.html-preview-vscode', 
            'tht13.python', 
            'tushortz.python-extended-snippets', 
            'wholroyd.jinja', 
            'yzhang.markdown-all-in-one'
            ]
    }, 
    'app': {
        'bind_addr': configs_list.get("system").get("app_bind_addr"), 
        'base_url': configs_list.get("system").get("app_base_url"), 
        'root_dir': configs_list.get("system").get("app_root_dir"), 
        'user': configs_list.get("system").get("app_user"), 
        'password': configs_list.get("system").get("app_password")
    }
}]

def set_user_config(user_config, default_user, level):
    log.setLevel(level)
    log.info(user_config.get("yaml_config_value"))
    log.info(user_config.get("docker_env_value"))
    if user_config.get("yaml_config_value") == None:
        log.info("no setting found for '{}', setting: '{}'".format(user_config.get("yaml_config_name"), user_config.get("docker_env_value")))
        if user_config.get("dict_path") == 2:
            configs_list.get(user_config.get("dict_path")[0])[user_config.get("dict_path")[1]] = user_config.get("docker_env_value")
    elif user_config.get("yaml_config_value") == user_config.get("docker_env_value"):
        log.debug("yaml config same as docker environment value: {} --> '{}'".format(user_config.get("docker_env_name"), user_config.get("docker_env_value")))
    else:
        log.warning("using user config setting instead of docker environment value - {}: '{}'--> '{}'".format(user_config.get("docker_env_name"), user_config.get("docker_env_value"), user_config.get("yaml_config_value")))

user_configs = [
    {
        "yaml_config_name": "name",
        "docker_env_name": "workspace_user",
        "yaml_config_value": configs_list.get("users")[0].get("name"),
        "docker_env_value": configs_list.get("system").get("workspace_user"),
        "dict_path": ["users", "name"]
    },
    {
        "yaml_config_name": "group",
        "docker_env_name": "workspace_group",
        "yaml_config_value": configs_list.get("users")[0].get("group"),
        "docker_env_value": configs_list.get("system").get("workspace_group"),
        "dict_path": ["users", "group"]
    },
    {
        "yaml_config_name": "shell",
        "docker_env_name": "workspace_user_shell",
        "yaml_config_value": configs_list.get("users")[0].get("shell"),
        "docker_env_value": configs_list.get("system").get("workspace_user_shell"),
        "dict_path": ["users", "shell"]
    },
    {
        "yaml_config_name": "password",
        "docker_env_name": "workspace_user_password",
        "yaml_config_value": configs_list.get("users")[0].get("password"),
        "docker_env_value": configs_list.get("system").get("workspace_user_password"),
        "dict_path": ["users", "shell"]
    },
]

### Set user config
if configs_list.get("users") == None:
    log.info(f"Users not defined in yaml config file. Going with single user mode and importing settings from docker env or setting from default")
    configs_list["users"] = default_user
    # Show to console
    default_user_json = json.dumps(default_user, indent = 4)
elif len(configs_list.get("users")) == 0:
    log.info("User's list empty, populate and restart container")
    sys.exit()   
elif len(configs_list.get("users")) == 1:
    log.info("Building a single user environment")
    # what's the point of this? overwrite workspace envs with corresponding user envs? Maybe not good to touch and better keep docker envs concistent with this dict. Don't overwrite with user settings. Also simpler
    #for uc in user_configs:
        #set_user_config(uc, default_user, verbosity)

    user_count = 0
    for u in configs_list.get("users"):
        log.debug(f"working on user count: '{user_count}'")
        for default_config, default_setting in default_user[0].items():
            for config, setting in u.items():
                if config == default_config:
                    if setting == default_setting:
                        log.debug(f"yaml config setting same as default: '{config}' --> '{setting}'")
                    else:
                        log.debug(f"yaml config setting differs from default - {config}: '{default_setting}'--> '{setting}'")    
                if config == "name":
                    user = setting
                    home = os.path.join("/home", user)
                if config == "password":
                    password = setting
            if not default_config in list(u.keys()):
                log.info(f"not set in yaml config, setting from default settings: '{default_config}' --> '{default_setting}'")
                configs_list.get("users")[user_count][default_config] = default_setting
        user_count+=1
        
    log.info(f"setting workspace user to: '{user}'")

elif len(configs_list.get("users")) > 1:
    log.info("More than 2 users defined, haven't build this functionality yet. Remove extra users and restart container.")
    sys.exit()

# Dump into JSON for passage into scripts
configs_list_json = json.dumps(configs_list)
### Write docker envs to system environment
#for env, value in docker_env.items():
#    func.set_env_variable(env, value)

### Clean up envs

# opts_json arguments to json
opts_json = json.dumps(opts)

### Dynamiruny set MAX_NUM_THREADS
ENV_MAX_NUM_THREADS = os.getenv("MAX_NUM_THREADS", None)
if ENV_MAX_NUM_THREADS:
    # Determine the number of availabel CPU resources, but limit to a max number
    if ENV_MAX_NUM_THREADS.lower() == "auto":
        ENV_MAX_NUM_THREADS = str(math.ceil(os.cpu_count()))
        try:
            # read out docker information - if docker limits cpu quota
            cpu_count = math.ceil(
                int(
                    os.popen("cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us")
                    .read()
                    .replace("\n", "")
                )
                / 100000
            )
            if cpu_count > 0 and cpu_count < os.cpu_count():
                ENV_MAX_NUM_THREADS = str(cpu_count)
        except:
            pass
        if (
            not ENV_MAX_NUM_THREADS
            or not ENV_MAX_NUM_THREADS.isnumeric()
            or ENV_MAX_NUM_THREADS == "0"
        ):
            ENV_MAX_NUM_THREADS = "4"

        if int(ENV_MAX_NUM_THREADS) > 8:
            # there should be atleast one thread less compared to cores
            ENV_MAX_NUM_THREADS = str(int(ENV_MAX_NUM_THREADS) - 1)

        # set a maximum of 32, in most cases too many threads are adding too much overhead
        if int(ENV_MAX_NUM_THREADS) > 32:
            ENV_MAX_NUM_THREADS = "32"

    # only set if it is not None or empty
    # OMP_NUM_THREADS: Suggested value: vCPUs / 2 in which vCPUs is the number of virtual CPUs.
    set_env_variable(
        "OMP_NUM_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True
    )  # OpenMP
    set_env_variable(
        "OPENBLAS_NUM_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True
    )  # OpenBLAS
    set_env_variable("MKL_NUM_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True)  # MKL
    set_env_variable(
        "VECLIB_MAXIMUM_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True
    )  # Accelerate
    set_env_variable(
        "NUMEXPR_NUM_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True
    )  # Numexpr
    set_env_variable(
        "NUMEXPR_MAX_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True
    )  # Numexpr - maximum
    set_env_variable(
        "NUMBA_NUM_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True
    )  # Numba
    set_env_variable(
        "SPARK_WORKER_CORES", ENV_MAX_NUM_THREADS, ignore_if_set=True
    )  # Spark Worker
    set_env_variable(
        "BLIS_NUM_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True
    )  # Blis
    set_env_variable("TBB_NUM_THREADS", ENV_MAX_NUM_THREADS, ignore_if_set=True)  # TBB
    # GOTO_NUM_THREADS

### Set container environment
# Get system env and display
system_env = os.environ.copy()
log.debug("System Environments:")
log.debug(func.capture_cmd_stdout('env', system_env))

# Display docker env
log.debug("Docker Environments:")
log.debug(func.capture_cmd_stdout('env', docker_env))

# Merge system, docker env as workspace env and display
workspace_env = func.merge_two_dicts(system_env, docker_env)
log.debug("Workspace Environment") 
log.debug(func.capture_cmd_stdout('env', workspace_env))

# Format workspace env as json for passage into scripts
workspace_env_json = json.dumps(workspace_env)

### Configure user
log.info(f"configuring user")
run(
    ['python', f"/scripts/configure_user.py", 
        '--opts', opts_json,
        '--env', workspace_env_json,
        '--configs', configs_list_json
    ], 
    env=workspace_env
)

### Set workspace user and home
workspace_env['USER'] = user
workspace_env['HOME'] = home
workspace_env['WORKSPACE_USER'] = user
workspace_env['WORKSPACE_USER_HOME'] = home
workspace_env['WORKSPACE_USER_PASSWORD'] = password

### Start workspace
sys.exit(
    run(
        ['python', '/scripts/run_workspace.py', 
            '--opts', opts_json],
        env=workspace_env
    )
)
