#!/usr/bin/python

"""
Main Workspace Run Script
"""

# Enable logging
import logging
import math
import os
import sys
import subprocess
from subprocess import run
from urllib.parse import quote

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)

log = logging.getLogger(__name__)

log.info("Starting...")


def set_env_variable(env_variable: str, value: str, ignore_if_set: bool = False):
    if ignore_if_set and os.getenv(env_variable, None):
        # if it is already set, do not set it to the new value
        return
    # TODO is export needed as well?
    run("export " + env_variable + '="' + value + '"', shell=True)
    os.environ[env_variable] = value

ENV_STAGING_BASE_URL = os.getenv("STAGING_BASE_URL", "/")
base_url = os.getenv(ENV_STAGING_BASE_URL, "")
# Add leading slash
if not base_url.startswith("/"):
    base_url = "/" + base_url

# Remove trailing slash
base_url = base_url.rstrip("/").strip()
# always quote base url
base_url = quote(base_url, safe="/%")

# Dynamiruny set MAX_NUM_THREADS
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

sys.exit(
    run(
        "python /scripts/run_staging.py",
        shell=True,
    )
)
