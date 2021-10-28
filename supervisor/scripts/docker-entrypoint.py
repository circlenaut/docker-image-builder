#!/usr/bin/python

"""
Docker Entrypoint
"""

import json
import logging
import math
import os
import pathlib
import sys
from copy import copy
from subprocess   import run, call
from typing import Dict, List

import coloredlogs
import yaml
import yamale

SCRIPTS_PATH = os.getenv("SCRIPTS_PATH", "/scripts")
sys.path.append(SCRIPTS_PATH)
from scripts.functions_ import (
    capture_cmd_stdout as _capture_cmd_stdout,
    merge_two_dicts as _merge_two_dicts,
    yaml_valid as _yaml_valid,
)


### Read or set docker default envs
DOCKER_ENV = {
    'LOG_VERBOSITY': os.getenv("LOG_VERBOSITY", "INFO"),
    'API_USER': os.getenv("API_AUTH_USER", "micro-api"),
    'API_GROUP': os.getenv("API_AUTH_GROUP", "users"),
    'API_USER_PASSWORD': os.getenv("API_AUTH_PASSWORD", "password"),
    'APPS_PATH': os.getenv("APPS_PATH", "/apps"),
    'DATA_PATH': os.getenv("DATA_PATH", "/data"),
    'APP_BIND_ADDR': os.getenv("APP_BIND_ADDR", "0.0.0.0:8080"),
    'APP_BASE_URL': os.getenv("APP_BASE_URL", "/app"),
    'APP_ROOT_DIR': os.getenv("APP_ROOT_DIR", "/apps/app"),
    'APP_USER': os.getenv("APP_USER", "admin"),
    'APP_PASSWORD': os.getenv("APP_PASSWORD", "password")
}


def load_config() -> Dict:
    config_path = pathlib.Path(
        os.getenv('API_CONFIG_FILE', './config.yaml')
    )
    if not config_path.exists():
        log.debug("No yaml config file available to load")
        return

    config_schema_path = pathlib.Path(
        os.getenv('API_CONFIG_FILE', './schema.yaml')
    )
    if not config_schema_path.exists():
        log.debug("No yaml config schema file available to load")
        return

    # Validate file
    schema = yamale.make_schema(config_schema_path.as_posix())
    data = yamale.make_data(config_path.as_posix())
    valid_config = _yaml_valid(schema, data, "INFO")
    if not valid_config:
        log.debug("Invalid configuration")
        return

    # Load config as yaml object
    log.info(f"Loading config file: '{config_path}'")
    config = None
    with open(config_path, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    log.debug(config)
    return config

def get_log_level(log_verbosity: str) -> str:
    if log_verbosity in [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL"
    ]:
        verbosity = log_verbosity
    else:
        log.info("invalid verbosity: '{}".format(env.get("LOG_VERBOSITY")))
        verbosity = "INFO"
    return verbosity


def reconcile_config(configs: Dict) -> Dict:
    if configs is None:
        configs = {}
        configs["system"] = {env.lower():value for env,value in DOCKER_ENV.items()}
        return configs

    ### Reconcile docker env var with corresponding config setting
    system_configs = dict()
    # copy and save user configs
    users_config_copy = copy(configs["users"])

    # if system not configured in yaml, then set to docker envs
    if configs.get("system") == None:
        log.info(f"System not defined in yaml config file. Importing settings from docker env.")
        for env, value in DOCKER_ENV.items():
            log.debug(f"setting: '{env.lower()}' --> '{value}'")
            system_configs[env.lower()] = value
        # copy into system key
        configs["system"] = copy(system_configs)
        # copy users back
        configs["users"] = copy(users_config_copy)

    # reconcile if env appears in both
    else:
        for env, value in DOCKER_ENV.items():
            for config, setting in configs.get("system").items():
                if config == env.lower():
                    if setting == value:
                        log.debug(f"yaml config same as docker environment value: '{config}' --> '{setting}'")
                        system_configs[config] = value
                    else:
                        log.warning(f"using config setting instead of docker environment value - {config}: '{value}'--> '{setting}'")
                        system_configs[config] = setting
            if not env.lower() in list(configs.get("system").keys()):
                log.debug(f"not set in yaml config, setting: '{env.lower()}' --> '{value}'")
                system_configs[env.lower()] = value
        # copy into system key
        configs["system"] = copy(system_configs)
        # copy users back
        configs["users"] = copy(users_config_copy)
    return configs


### Enable logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
log = logging.getLogger(__name__)
log.info("Starting...")

### Set verbosity level. log.info occasinally throws EOF errors with high verbosity
verbosity = get_log_level(DOCKER_ENV.get("LOG_VERBOSITY"))
log.setLevel(verbosity)

### opts_json cli options
opts = {
    "verbosity": verbosity
}

### Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

### Read YAML config file and reconcile env and file configs
configs = reconcile_config(configs=load_config())
    
### Reset verbosity level according to yaml file. log.info occasinally throws EOF errors with high verbosity
verbosity = get_log_level(configs.get("system").get("log_verbosity"))
log.setLevel(verbosity)

### Reset opts_json cli options
opts = {
    "verbosity": verbosity
}

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
log.debug(_capture_cmd_stdout('env', system_env))

# Display docker env
log.debug("Docker Environments:")
log.debug(_capture_cmd_stdout('env', DOCKER_ENV))

# Merge system, docker env as workspace env and display
API_env = _merge_two_dicts(system_env, DOCKER_ENV)
log.debug("Workspace Environment") 
log.debug(_capture_cmd_stdout('env', API_env))

### Set workspace user and home
user = configs.get('system').get('api_user')
password = configs.get('system').get('api_user_password')
API_env['USER'] = user
API_env['API_USER'] = user
API_env['API_USER_HOME'] = os.getenv("HOME")
API_env['API_USER_PASSWORD'] = password

### Start workspace
supervisor_entrypoint = pathlib.Path(SCRIPTS_PATH).joinpath('run_supervisor.py')
sys.exit(
    run(
        ['python', supervisor_entrypoint.as_posix(),
            '--opts', opts_json],
        env=API_env,
    )
)