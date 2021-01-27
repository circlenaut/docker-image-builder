#!/usr/bin/python

"""
Configure user
"""

import os
import shutil
import sys
import json
import docker
import bcrypt
import logging
import crypt
import codecs
import typing
import spwd
from pathlib    import Path
from subprocess import run, call
from users_mod  import PwdFile

def check_user_exists(username):
     exists = str()
     user_records = PwdFile().toJSON().get("pwdRecords")

     for user in user_records:
          if user.get("userName") == username:
               record = json.dumps(user, indent = 4)
               exists = "yes"
               break
          else:
               exists = "no"
     return exists, record

def run_pass_change(username, hash):
     log.info(f"new password hash: '{hash}'")
     cmd = ['usermod', '-p', hash, username]
     return_code = call(cmd)

     if return_code == 0:
          log.info('password change: success')
          return 'success'
     else:
          log.info('password change: error')
          return 'error'

def check_current_pass(username):
     current_password_hash = spwd.getspnam(username).sp_pwdp
     if current_password_hash == '':
          log.info("current password: empty")
          return 'empty'
     if not current_password_hash == '':
          log.info("current password: set")
          return 'set'
     else:
          log.info("current password: unknown error")
          return 'error'

def check_old_pass(username, password):
     current_password_hash = spwd.getspnam(username).sp_pwdp
     old_password_hash = crypt.crypt(password, current_password_hash)

     if current_password_hash == old_password_hash:
          log.info(f"old password '{password}': valid")
          return 'valid'
     elif not current_password_hash == old_password_hash:
          log.info(f"old password '{password}': invalid")
          return 'invalid'
     else:
          log.info("old password: unknown error")
          return 'error'

def change_pass(username, old_password, new_password):
     user_exists, record = check_user_exists(username)
     if user_exists == 'yes':
          current_password_hash = spwd.getspnam(username).sp_pwdp
          log.info(f"current password hash: '{current_password_hash}'")
          log.info(f"new password: '{new_password}'")
          current_pass = check_current_pass(username)

          if current_pass  == 'empty':
               salt = crypt.mksalt(crypt.METHOD_SHA512)
               new_password_hash = crypt.crypt(new_password, salt)
               run_pass_change(username, new_password_hash)

     elif current_pass == 'set':
          old_pass = check_old_pass(username, old_password)
          if old_pass == 'valid':
               new_password_hash = crypt.crypt(new_password, current_password_hash)
               if new_password_hash == current_password_hash:
                    log.info("new password same as current")
               else:
                    run_pass_change(username, new_password_hash)
          elif old_pass == 'invalid':
               return 1
          elif old_pass == 'error':
               return 126
          elif old_pass == 'error':
               return 126
     elif user_exists == 'no':
          log.info(f"user: '{username}' does not exist")
          return 1
     else:
          log.info("unknown error")

def change_user_shell(username, shell):
     user_exists, record = check_user_exists(username)
     if user_exists == 'yes':
          log.info(f"'{username}' shell changed to: '{shell}'")
          cmd = ['usermod', '--shell', shell, username]
          return_code = call(cmd)

          if return_code == 0:
               log.info('password change: success')
               return 'success'
          else:
               log.info('password change: error')
               return 'error'
     elif user_exists == 'no':
          log.info(f"user: '{username}' does not exist")
          return 1
     else:
          log.info("unknown error")

### Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

### Read system envs
ENV_HOSTNAME = os.getenv("HOSTNAME", "localhost")
ENV_USER = os.getenv("SUDO_USER", "coder")
ENV_WORKSPACE_AUTH_PASSWORD =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")

### Clean up envs
application = "config_user"
host_fqdn = ENV_HOSTNAME


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
data_dir = os.path.normpath(ENV_DATA_PATH)

### Generate password hash
password = ENV_WORKSPACE_AUTH_PASSWORD.encode()
salt = bcrypt.gensalt()
hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
#log.info(f"{application} password: '{ENV_WORKSPACE_AUTH_PASSWORD}'")
#log.info(f"{application} hashed password: '{hashed_password}'")
os.environ['HASHED_PASSWORD'] = hashed_password


change_pass(ENV_USER, "password", ENV_WORKSPACE_AUTH_PASSWORD)
change_user_shell(ENV_USER, shell="/usr/bin/zsh")
user_exists, user_record = check_user_exists(ENV_USER)
log.info(user_record)

### Write config file
#config_path = os.path.join(config_dir, f"{application}.json")
#config_json = json.dumps(config_file, indent = 4)

#with open(config_path, "w") as f: 
#    f.write(config_json)

#log.info(f"{application} config:")
#log.info(subprocess.run(["cat", config_path]))