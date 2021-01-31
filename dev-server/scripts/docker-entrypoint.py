#!/usr/bin/python

"""
Main Workspace Run Script
"""

import os
import sys
import logging
import json
import math
import scripts.functions as func
from subprocess   import run, call

### Enable logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)

log = logging.getLogger(__name__)
log.info("Starting...")

### Read or set docker default envs
docker_env = {
    'WORKSPACE_USER': os.getenv("WORKSPACE_USER", "coder"),
    'WORKSPACE_GROUP': os.getenv("WORKSPACE_GROUP", "users"),
    'WORKSPACE_USER_PASSWORD': os.getenv("WORKSPACE_AUTH_PASSWORD", "password"),
    'RESOURCES_PATH': os.getenv("RESOURCES_PATH", "/resources"),
    'WORKSPACE_HOME': os.getenv("WORKSPACE_HOME", "/workspace"),
    'LOG_VERBOSITY': os.getenv("LOG_VERBOSITY", "INFO"),
    'APPS_PATH': os.getenv("APPS_PATH", "/apps"),
    'DATA_PATH': os.getenv("DATA_PATH", "/data"),
    'PROXY_BASE_URL': os.getenv("PROXY_BASE_URL", "/"),
    'ZSH_PROMPT': os.getenv("ZSH_PROMPT", "none"),
    'ZSH_THEME': os.getenv("ZSH_THEME", "spaceship"), 
    'ZSH_PLUGINS': os.getenv("ZSH_PLUGINS", "all"),   
    'CADDY_VIRTUAL_PORT': os.getenv("VIRTUAL_PORT", "80"),
    'CADDY_VIRTUAL_HOST': os.getenv("VIRTUAL_HOST", ""),
    'CADDY_VIRTUAL_BIND_NET': os.getenv("VIRTUAL_BIND_NET", "proxy"),
    'CADDY_VIRTUAL_PROTO': os.getenv("VIRTUAL_PROTO", "http"),
    'CADDY_VIRTUAL_BASE_URL': os.getenv("VIRTUAL_BASE_URL", "/"),
    'CADDY_PROXY_ENCODINGS_GZIP': os.getenv("PROXY_ENCODINGS_GZIP", "true"),
    'CADDY_PROXY_ENCODINGS_ZSTD': os.getenv("PROXY_ENCODINGS_ZSTD", "true"),
    'CADDY_PROXY_TEMPLATES': os.getenv("PROXY_TEMPLATES", "true"),
    'CADDY_LETSENCRYPT_EMAIL': os.getenv("LETSENCRYPT_EMAIL", "admin@example.com"),
    'CADDY_LETSENCRYPT_ENDPOINT': os.getenv("LETSENCRYPT_ENDPOINT", "prod"),
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

### Write docker envs to system environment
#for env, value in docker_env.items():
#    func.set_env_variable(env, value)

### Clean up envs
# Set verbosity level. log.info occasinally throws EOF errors with high verbosity
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

system_env = os.environ.copy()
log.debug("System Environments:")
log.debug(func.capture_cmd_stdout('env', system_env))

log.debug("Docker Environments:")
log.debug(func.capture_cmd_stdout('env', docker_env))

### Run user config restoration
action = "restore"
log.info(f"backup script: '{action}'")
run(['sudo', '--preserve-env', 'python3', '/scripts/backup_restore_config.py', '--opts', opts_json, action])

workspace_env = func.merge_two_dicts(system_env, docker_env)
log.debug("Workspace Environment") 
log.debug(func.capture_cmd_stdout('env', workspace_env))

workspace_env_json = json.dumps(workspace_env)

### configure user
log.info(f"configuring user")
run(
    ['python3', f"/scripts/configure_user.py", 
    '--opts', opts_json,
    '--env', workspace_env_json], 
    env=workspace_env
)

### Set workspace user and home
user = docker_env.get("WORKSPACE_USER")
home = os.path.join("/home", user)
workspace_env['USER'] = user
workspace_env['HOME'] = home
workspace_env['WORKSPACE_USER_HOME'] = home

### Start workspace
sys.exit(
    run(
        ['python3', '/scripts/run_workspace.py', '--opts', opts_json],
        env=workspace_env
    )
)
