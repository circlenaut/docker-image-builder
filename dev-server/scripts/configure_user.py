#!/usr/bin/python

"""
Configure user
"""

import os
import pwd
import sys
import shutil
import psutil
import json
import bcrypt
import logging
import crypt
import spwd
import requests
from urllib.parse import urlparse
from subprocess import run, call, Popen, PIPE
from users_mod  import PwdFile
from pathlib import Path
import functions as func

def check_user(username):
     user_exists = False
     record = dict()
     home = os.path.join("/home", username)
     user_records = PwdFile().toJSON().get("pwdRecords")

     if os.path.exists(home):
          home_exists = True
     else:
          home_exists = False

     for user in user_records:
          if user.get("userName") == username:
               record = json.dumps(user, indent = 4)
               user_exists = True
               break
          else:
               user_exists = False

     return user_exists, home_exists, record

def create_user(config):
     username = config.get("name")
     home = config.get("dirs").get("home").get("path")
     uid = config.get("uid")
     gid = config.get("gid")
     shell = config.get("shell")

     return_codes = list()

     log.info(f"creating user group: '{username}'")
     cmd = ['groupadd', \
          '--gid', gid, \
          '-o', username
          ]
     return_code = call(cmd)

     if return_code == 0:
          log.info("group creation: success")
          return_codes.append(return_code)
     else:
          log.info("group creation: error")
          return_codes.append(return_code)

     if os.path.exists(home):
          log.info(f"creating user without home: '{username}'")
          cmd = ['useradd', \
               '--uid', uid, \
               '--gid', gid, \
               '--shell', shell, \
               username
               ]
          return_code = call(cmd)
     else:
          log.info(f"creating user with home: '{username}'")
          cmd = ['useradd', \
          '--uid', uid, \
          '--gid', gid, \
          '--create-home', \
          '--shell', shell, \
          username
          ]
          return_code = call(cmd)

     if return_code == 0:
          log.info("user creation: success")
          return_codes.append(return_code)
     else:
          log.info("user creation: error")
          return_codes.append(return_code)

     log.info(f"adding to sudo: '{username}'")
     cmd = ['adduser', username, 'sudo']
     return_code = call(cmd)

     if return_code == 0:
          log.info(f"'{username}'' added to sudo: success")
          return_codes.append(return_code)
     else:
          log.info(f"'{username}'' added to sudo: error")
          return_codes.append(return_code)

     ### Create user sudo config
     sudo_config_path = os.path.join("/etc/sudoers.d", username)
     sudo_config = f"{username} ALL=(root) NOPASSWD:ALL"
     
     log.info(f"adding sudo config: '{sudo_config}' to '{sudo_config_path}'")
     with open(sudo_config_path, "w") as f: 
          f.write(sudo_config + "\n")

     log.info(f"fixing sudo config permission: '{sudo_config_path}'")
     func.chmod(sudo_config_path, "440")

     log.info(f"sudo config file:")
     log.info(run(["cat", sudo_config_path]))
     
def setup_ssh(username, environment):
     system_env = environment
     home = os.path.join("/home", username)
     ssh_config_dir = os.path.join(home, ".ssh")
     ssh_config = os.path.join(ssh_config_dir, 'config')
     ssh_env = os.path.join(ssh_config_dir, 'environment')

     if not os.path.exists(ssh_config_dir):
          log.info(f"creating ssh config directory: '{ssh_config_dir}'")
          os.mkdir(ssh_config_dir)

     if not os.path.exists(ssh_config):
          log.info(f"creating ssh config file: '{ssh_config}'")
          with open(ssh_config, "w") as f: 
                    f.write(" ")

     log.info(f"setting ownership of '{ssh_config_dir}' to '{username}'")
     func.recursive_chown(ssh_config_dir, username)

     if not os.path.exists(ssh_env):
          log.info(f"creating ssh environment file: '{ssh_env}'")
          
          for env, value in system_env.items():
               env_var = f"{env}={value}"
               with open(ssh_env, "a") as f: 
                         f.write(env_var + "\n")
          log.info(f"ssh env file:")
          log.info(run(["cat", ssh_env]))

def set_user_paths(config):
     username = config.get("name")

     for name, attr in config.get("dirs").items():
          dir_path = attr.get("path")
          dir_mode = attr.get("mode")
          if os.path.exists(dir_path):
               log.info(f"path exists: '{dir_path}'")
               if Path(dir_path).owner() == username:
                    log.info(f"path '{dir_path}', already owned by '{username}'")
               else:
                    # Set ownership of top path
                    log.info(f"setting ownership of '{dir_path}', to '{username}'")
                    func.chown(dir_path, username)
                    log.info(f"setting mode of '{dir_path}', to '{dir_mode}'")
                    func.chmod(dir_path, dir_mode)
                    # Go one level down, docker sets mounted dir ownership to root
                    for d in os.listdir(dir_path):
                         p = os.path.join(dir_path, d)
                         if Path(p).owner() == username:
                              log.info(f"path '{p}', already owned by '{username}'")
                         else:
                              log.info(f"setting ownership of '{p}', to '{username}'")
                              func.recursive_chown(p, username)
                              log.info(f"setting mode of '{p}', to '{dir_mode}'")
                              func.recursive_chmod(p, dir_mode)
          else:
               log.info(f"creating directory: '{dir_path}'")
               os.makedirs(dir_path)
               log.info(f"setting ownership of '{dir_path}', to '{username}'")
               func.recursive_chown(dir_path, username)
               log.info(f"setting mode of '{dir_path}', to '{dir_mode}'")
               func.recursive_chmod(dir_path, dir_mode)

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
     empty_passwords = ['', '!']
     if current_password_hash in empty_passwords:
          log.info("current password: empty")
          return 'empty'
     elif not current_password_hash in empty_passwords:
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
     user_exists, home_exists, record = check_user(username)
     if user_exists:
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
     elif not user_exists:
          log.info(f"user: '{username}' does not exist")
          return 1
     else:
          log.info("unknown error")

def change_user_shell(username, shell):
     user_exists, home_exists, record = check_user(username)

     if user_exists:
          log.info(f"'{username}' shell changed to: '{shell}'")
          cmd = ['usermod', '--shell', shell, username]
          return_code = call(cmd)

          if return_code == 0:
               log.info('password change: success')
               return 'success'
          else:
               log.info('password change: error')
               return 'error'
     elif not user_exists:
          log.info(f"user: '{username}' does not exist")
          return 1
     else:
          log.info("unknown error")

def init_shell(config, environment):
     username = config.get("name")
     home = os.path.join("/home", username)
     workspace_dir = config.get("dirs").get("workspace").get("path")
     resources_dir = config.get("dirs").get("resources").get("path")
     user_env = environment
     
     ### Set conda envs
     conda_root = os.path.join(home, ".conda")
     user_env['PATH'] += os.pathsep + os.path.join(conda_root, "bin")
     conda_env = environment
     conda_env['USER'] = username
     conda_env['HOME'] = home
     conda_env['CONDA_BIN'] = conda_root

     # Install conda
     func.run_shell_installer_url(
          'https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh', 
          ['-u', '-b', '-p', conda_root], 
          os.environ.copy()
     )

     ### Set Path
     #conda_bin = os.path.join(conda_root, 'condabin', 'conda')
     ### Set Paths
     # conda
     conda_root = os.path.join(home, ".conda")
     conda_bin_path = os.path.join(conda_root, "bin")
     conda_bin_dir = os.path.join(conda_root, 'condabin')
     conda_bin_exe = os.path.join(conda_root, 'condabin', 'conda')
     user_env['CONDA_BIN'] = conda_root
     user_env['PATH'] += os.pathsep + conda_bin_path
     user_env['PATH'] += os.pathsep + conda_bin_dir
     conda_env['PATH'] += os.pathsep + conda_bin_path
     conda_env['PATH'] += os.pathsep + conda_bin_dir

     # pyenv dir
     pyenv_root = f"{resources_dir}/.pyenv"
     user_env['PATH'] += os.pathsep + os.path.join(pyenv_root, "shims")
     user_env['PATH'] += os.pathsep + os.path.join(pyenv_root, "bin")

     # local
     local_bin = os.path.join(home, ".local/bin")
     user_env['PATH'] += os.pathsep + local_bin

    ### Disable auto conda activation
     run(
          ['conda', 'config', '--set', 'auto_activate_base', 'false'],
          env=conda_env
     )
     
     #user_env['PATH'] += os.pathsep + os.path.join(pyenv_root, "shims")
     #user_env['PATH'] += os.pathsep + os.path.join(pyenv_root, "bin")
     #user_env['PATH'] += os.pathsep + os.path.join(conda_root, "bin")

     return user_env

def setup_user(config, environment):
     system_env = environment

     log.info("Creating user: '{name}'".format(name=config.get("name")))
     create_user(config)
     
     setup_ssh(config.get("name"), system_env)
     change_pass(config.get("name"), "password", config.get("password"))
     change_user_shell(config.get("name"), config.get("shell"))
     
     user_env = init_shell(config, system_env)
     
     set_user_paths(config)
     user_exists, home_exists, user_record = check_user(config.get("name"))
     log.info(user_record)

     # configure system services
     services = ["ssh", "cron"]
     for serv in services:
          log.info(f"configuring system service: '{serv}'")
          run(
               ['python3', f"/scripts/configure_{serv}.py"], 
               env=user_env
          )

     # configure user settings
     services = ["zsh"]
     for serv in services:
          log.info(f"configuring user service: '{serv}'")
          run(
               ['sudo', '-i', '-u', config.get("name"), 'python3', f"/scripts/configure_{serv}.py"], 
               env=user_env
          )

     startup_custom_script = os.path.join(workspace_dir, "on_startup.sh")
     if os.path.exists(startup_custom_script):
          log.info("Run on_startup.sh user script from workspace folder")
          # run startup script from workspace folder - can be used to run installation routines on workspace updates
          run(
               ['/bin/bash', startup_custom_script], 
               env=user_env
          )

     ### Create conda environments
     #@TODO: fix conda PATH to avoid using conda_exe trick
     conda_exe = os.path.join(home, ".conda", 'condabin', 'conda')
     run(
          ['sudo', '-i', '-u', config.get("name"), conda_exe, 'run','-n', 'base', 'python', '/scripts/setup_workspace.py'], 
          env=user_env
     )

     return user_env

def run_user_services_config(username, environment, exists):
     # configure user services and options
     services = dict()
     log.info(exists)
     if exists:
          services = {
               "caddy": {
                    "config": {}
               }, 
               "vscode": {
                    "config": {
                         "extensions": []
                    }
               }, 
               "filebrowser": {
                    "config": {}
               }, 
               "app": {
                    "config": {}
               }
          } 
     else:
          services = {
               "caddy": {
                    "config": {}
               }, 
               "vscode": {
                    "config": {
                         "extensions": [
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
                              'yzhang.markdown-all-in-one',
                         ]
                    }
               }, 
               "filebrowser": {
                    "config": {}
               }, 
               "app": {
                    "config": {}
               }
          } 

     for serv, opts in services.items():
          log.info(f"configuring user service: '{serv}'")
          # format dictionary arguments as json
          load = json.dumps(opts)
          run(
               ['sudo', '-i', '-u', username, 'python3', f'/scripts/configure_{serv}.py', '--opts', load], 
               env=environment
          )

### Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

system_env = os.environ.copy()

### Read system envs
ENV_USER = os.getenv("USER", "coder")
ENV_HOME = os.path.join("/home", ENV_USER)

### Read docker envs
ENV_WORKSPACE_USER = os.getenv("WORKSPACE_USER", "coder")
ENV_WORKSPACE_AUTH_PASSWORD =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")
ENV_APPS_PATH = os.getenv("APPS_PATH", "/apps")

### Clean up envs
application = "config_user"
username = ENV_WORKSPACE_USER
home = os.path.join("/home", ENV_WORKSPACE_USER)
workspace_password = ENV_WORKSPACE_AUTH_PASSWORD

### Set config and data paths
workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
resources_dir = os.path.normpath(ENV_RESOURCES_PATH)
data_dir = os.path.normpath(ENV_DATA_PATH)
apps_dir = os.path.normpath(ENV_APPS_PATH)
     
users = dict()

#USERS = f"coder:1000:100:zsh test:1001:101:bash"
USERS = f"{username}:1000:100:zsh:{workspace_password}"

for u in USERS.split(" "):
     configs = u.split(":")
     log.info(configs)
     name = configs[0]
     uid = configs[1]
     gid = configs[2]
     shell = configs[3]
     password = configs[4]
     home = os.path.join("/home", name)
     
     if shell == "zsh": 
          shell_path = "/usr/bin/zsh"
     elif shell == "bash":
          shell_path = "/bin/bash"
     else:
          log.info(f"invalid shell for user '{name}': '{shell}'")

     users[name] = {
          'name': name,
          'uid': uid,
          'gid': gid,
          'shell': shell_path,
          'password': password,
          'dirs' : {
               'home': {
                    'path': home,
                    'mode': "755"
               },
               'resources': {
                    'path': resources_dir, 
                    'mode': "755"
               },
               'workspace':  {
                    'path': workspace_dir,
                    'mode': "755"
               },
               'data': {
                    'path': data_dir,
                    'mode': "755"
               },
               'app': {
                    'path': apps_dir,
                    'mode': "755"
               }
          }
     }

for u, config in users.items():
     name = config.get("name")
     workspace_auth_password = config.get("password")
     user_exists, home_exists, user_record = check_user(name)

     if not user_exists and not home_exists:
          log.info(f"User and home does not exist, creating: '{name}'")
          user_env = setup_user(config, system_env)

          exists = False      
          run_user_services_config(name, user_env, exists)

          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=False)

     elif user_exists and not home_exists:
          # create missing user's home
          user_env = os.environ.copy()
          log.info(f"User exists '{name}' but home is missing")
          
          #@TODO: write function similar to setup_user that copies existing 
          # shadows info and init's shell

          exists = False
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)

     elif not user_exists and home_exists:
          user_env = os.environ.copy()
          home = os.path.join("/home", name)
          log.info(f"User does not exist but a home directory exists, creating: '{name}'")

          #@TODO: Impliment below when there's a way to backup/check against previous /etc/shadows file
          # move old home to backup
          #existing_home = os.path.join("/home", name)
          #backup_home = os.path.join("/home", f"{name}_previous")
          #shutil.move(existing_home, backup_home) 

          # Create user
          create_user(config)
          # Set password
          change_pass(config.get("name"), "password", config.get("password"))
          # fix permissions
          set_user_paths(config)
          # Configure services
          
          exists = True
          run_user_services_config(name, user_env, exists)
          ssh_dir = os.path.join(config.get("dirs").get("home").get("path"), ".ssh")
          log.info("setting correct permissions on '.ssh'")
          func.recursive_chmod(ssh_dir, "600")

          # Set enviornments
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)    

     elif user_exists and home_exists:
          # All's peachy for new user
          # move old home to backup and create new user
          user_env = os.environ.copy()
          log.info(f"User and home exists '{name}'")

          exists = True
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)                    
          
     else:
          log.info(f"User exists 'error'")


