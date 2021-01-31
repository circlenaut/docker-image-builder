#!/usr/bin/python

"""
Configure user
"""

import os
import pwd
import sys
import shutil
import psutil
import argparse
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

def check_user(user_name):
     user_exists = False
     record = dict()
     home = os.path.join("/home", user_name)
     user_records = PwdFile().toJSON().get("pwdRecords")

     if os.path.exists(home):
          home_exists = True
     else:
          home_exists = False

     for user in user_records:
          if user.get("user_name") == user_name:
               record = json.dumps(user, indent = 4)
               user_exists = True
               break
          else:
               user_exists = False

     return user_exists, home_exists, record

def create_user(config):
     user_name = config.get("name")
     home = config.get("dirs").get("home").get("path")
     uid = config.get("uid")
     gid = config.get("gid")
     shell = config.get("shell")

     return_codes = list()

     log.info(f"creating user group: '{user_name}'")
     cmd = ['groupadd', \
          '--gid', gid, \
          '-o', user_name
          ]
     return_code = call(cmd)

     if return_code == 0:
          log.info("group creation: success")
          return_codes.append(return_code)
     else:
          log.error("group creation: error")
          return_codes.append(return_code)

     if os.path.exists(home):
          log.warning(f"creating user without home: '{user_name}'")
          cmd = ['useradd', \
               '--uid', uid, \
               '--gid', gid, \
               '--shell', shell, \
               user_name
               ]
          return_code = call(cmd)
     else:
          log.info(f"creating user with home: '{user_name}'")
          cmd = ['useradd', \
          '--uid', uid, \
          '--gid', gid, \
          '--create-home', \
          '--shell', shell, \
          user_name
          ]
          return_code = call(cmd)

     if return_code == 0:
          log.info("user creation: success")
          return_codes.append(return_code)
     else:
          log.error("user creation: error")
          return_codes.append(return_code)

     log.info(f"adding to sudo: '{user_name}'")
     cmd = ['adduser', user_name, 'sudo']
     return_code = call(cmd)

     if return_code == 0:
          log.info(f"'{user_name}'' added to sudo: success")
          return_codes.append(return_code)
     else:
          log.error(f"'{user_name}'' added to sudo: error")
          return_codes.append(return_code)

     ### Create user sudo config
     sudo_config_path = os.path.join("/etc/sudoers.d", user_name)
     sudo_config = f"{user_name} ALL=(root) NOPASSWD:ALL"
     
     log.info(f"adding sudo config: '{sudo_config}' to '{sudo_config_path}'")
     with open(sudo_config_path, "w") as f: 
          f.write(sudo_config + "\n")

     log.info(f"fixing sudo config permission: '{sudo_config_path}'")
     func.chmod(sudo_config_path, "440")

     log.debug(f"sudo config file:")
     log.debug(func.cat_file(sudo_config_path))
     
def setup_ssh(user_name, user_group, environment):
     workspace_env = environment
     home = os.path.join("/home", user_name)
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

     log.info(f"setting ownership of '{ssh_config_dir}' to '{user_name}:{user_group}'")
     func.recursive_chown(ssh_config_dir, user_name, user_group)

     if not os.path.exists(ssh_env):
          log.info(f"creating ssh environment file: '{ssh_env}'")
          
          for env, value in workspace_env.items():
               env_var = f"{env}={value}"
               with open(ssh_env, "a") as f: 
                         f.write(env_var + "\n")
          log.debug(f"ssh env file:")
          log.debug(func.capture_cmd_stdout(f'cat {ssh_env}', os.environ.copy()))

def set_user_paths(config):
     user_name = config.get("name")
     user_group = config.get("group")

     for name, attr in config.get("dirs").items():
          dir_path = attr.get("path")
          dir_mode = attr.get("mode")
          if os.path.exists(dir_path):
               log.warning(f"path exists: '{dir_path}'")
               if Path(dir_path).owner() == user_name:
                    log.warning(f"path '{dir_path}', already owned by '{user_name}'")
               else:
                    # Set ownership of top path
                    log.info(f"setting ownership of '{dir_path}', to '{user_name}:{user_group}'")
                    func.chown(dir_path, user_name, user_group)
                    log.info(f"setting mode of '{dir_path}', to '{dir_mode}'")
                    func.chmod(dir_path, dir_mode)
                    # Go one level down, docker sets mounted dir ownership to root
                    for d in os.listdir(dir_path):
                         p = os.path.join(dir_path, d)
                         if Path(p).owner() == user_name:
                              log.warning(f"path '{p}', already owned by '{user_name}'")
                         else:
                              log.info(f"setting ownership of '{p}', to '{user_name}:{user_group}'")
                              func.recursive_chown(p, user_name, user_group)
                              log.info(f"setting mode of '{p}', to '{dir_mode}'")
                              func.recursive_chmod(p, dir_mode)
          else:
               log.info(f"creating directory: '{dir_path}'")
               os.makedirs(dir_path)
               log.info(f"setting ownership of '{dir_path}', to '{user_name}:{user_group}'")
               func.recursive_chown(dir_path, user_name, user_group)
               log.info(f"setting mode of '{dir_path}', to '{dir_mode}'")
               func.recursive_chmod(dir_path, dir_mode)

def run_pass_change(user_name, hash):
     log.info(f"new password hash: '{hash}'")
     cmd = ['usermod', '-p', hash, user_name]
     return_code = call(cmd)

     if return_code == 0:
          log.info('password change: success')
          return 'success'
     else:
          log.error('password change: error')
          return 'error'

def check_current_pass(user_name):
     current_password_hash = spwd.getspnam(user_name).sp_pwdp
     empty_passwords = ['', '!']
     if current_password_hash in empty_passwords:
          log.warning("current password: empty")
          return 'empty'
     elif not current_password_hash in empty_passwords:
          log.info("current password: set")
          return 'set'
     else:
          log.error("current password: unknown error")
          return 'error'

def check_old_pass(user_name, password):
     current_password_hash = spwd.getspnam(user_name).sp_pwdp
     old_password_hash = crypt.crypt(password, current_password_hash)

     if current_password_hash == old_password_hash:
          log.info(f"old password '{password}': valid")
          return 'valid'
     elif not current_password_hash == old_password_hash:
          log.warning(f"old password '{password}': invalid")
          return 'invalid'
     else:
          log.error("old password: unknown error")
          return 'error'

def change_pass(user_name, old_password, new_password):
     user_exists, home_exists, record = check_user(user_name)
     if user_exists:
          current_password_hash = spwd.getspnam(user_name).sp_pwdp
          log.info(f"current password hash: '{current_password_hash}'")
          log.info(f"new password: '{new_password}'")
          current_pass = check_current_pass(user_name)
          if current_pass  == 'empty':
               salt = crypt.mksalt(crypt.METHOD_SHA512)
               new_password_hash = crypt.crypt(new_password, salt)
               run_pass_change(user_name, new_password_hash)
          elif current_pass == 'set':
               old_pass = check_old_pass(user_name, old_password)
               if old_pass == 'valid':
                    new_password_hash = crypt.crypt(new_password, current_password_hash)
                    if new_password_hash == current_password_hash:
                         log.warning("new password same as current")
                    else:
                         run_pass_change(user_name, new_password_hash)
               elif old_pass == 'invalid':
                    return 1
               elif old_pass == 'error':
                    return 126
               elif old_pass == 'error':
                    return 126
     elif not user_exists:
          log.error(f"user: '{user_name}' does not exist")
          return 1
     else:
          log.error("unknown error")

def change_user_shell(user_name, shell):
     user_exists, home_exists, record = check_user(user_name)

     if user_exists:
          log.info(f"'{user_name}' shell changed to: '{shell}'")
          cmd = ['usermod', '--shell', shell, user_name]
          return_code = call(cmd)

          if return_code == 0:
               log.info('password change: success')
               return 'success'
          else:
               log.error('password change: error')
               return 'error'
     elif not user_exists:
          log.error(f"user: '{user_name}' does not exist")
          return 1
     else:
          log.error("unknown error")

def init_shell(config, environment):
     user_name = config.get("name")
     user_group = config.get("group")
     home = os.path.join("/home", user_name)
     system_shell = 'bash'
     workspace_dir = config.get("dirs").get("workspace").get("path")
     resources_dir = config.get("dirs").get("resources").get("path")
     user_env = environment
     
     ### Set conda envs
     conda_root = os.path.join(home, ".conda")
     conda_bin = os.path.join(conda_root, "bin")
     conda_rc = os.path.join(home, ".condarc")
     log.info(f'adding {conda_bin} to PATH')
     user_env['PATH'] += os.pathsep + conda_bin
     # required for conda to work
     user_env['USER'] = user_name
     user_env['HOME'] = home

     # Install conda
     func.run_shell_installer_url(
          'https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh', 
          ['-b', '-u', '-p', conda_root], 
          user_env
     )

     # fix permissions
     log.info(f"fixing ownership of '{conda_root}' for '{user_name}:{user_group}'")
     func.recursive_chown(conda_root, user_name, user_group)

     # Init Conda
     log.info(f"initializing conda on '{system_shell}'")
     run(['conda', 'init', system_shell], env=user_env)

     # Disable auto conda activation
     log.info(f"disabling conda auto activation for '{system_shell}'")
     run(['conda', 'config', '--set', 'auto_activate_base', 'false'], env=user_env)
     
     # fix permissions
     log.info(f"fixing ownership of '{conda_rc}' for '{user_name}:{user_group}'")
     func.chown(conda_rc, user_name, user_group)

     ### Set local bin PATH
     local_bin = os.path.join(home, ".local/bin")
     user_env['PATH'] += os.pathsep + local_bin

     log.info(func.capture_cmd_stdout('env', user_env))
     
     return user_env

def setup_user(config, environment, args):
     workspace_env = environment
     cli_args_json = json.dumps(args)
     cli_user_json = json.dumps(config)

     user_name = config.get("name")
     user_group = config.get("group")
     user_password = config.get("password")
     user_shell = config.get("shell")
     user_home = config.get("dirs").get("home").get("path")

     log.info(f"Creating user: '{user_name}'")
     create_user(config)
     set_user_paths(config)
     
     setup_ssh(user_name, user_group, workspace_env)
     change_pass(user_group, "password", user_password)
     change_user_shell(user_name, user_shell)
     
     user_env = init_shell(config, workspace_env)
     user_env_json = json.dumps(user_env)
     
     set_user_paths(config)
     user_exists, home_exists, user_record = check_user(name)
     log.debug(user_record)

     # configure system services
     #services = ["ssh", "cron"]

     log.info(func.capture_cmd_stdout('env', user_env))

     services = ["ssh"]
     for serv in services:
          log.info(f"configuring system service: '{serv}'")
          run(
               ['python3', f'/scripts/configure_{serv}.py', 
               '--opts', cli_args_json, 
               '--env', user_env_json, 
               '--user', cli_user_json],
               env=user_env
          )

     # configure user settings
     services = ["zsh"]
     for serv in services:
          log.info(f"configuring user service: '{serv}'")
          run(
               ['sudo', '-i', '-u', config.get("name"), 'python3', f'/scripts/configure_{serv}.py', 
                    '--opts', cli_args_json, 
                    '--env', user_env_json, 
                    '--user', cli_user_json],
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
     run(
           ['conda', 'run','-n', 'base', 'python', '/scripts/setup_workspace.py', '--opts', cli_args_json], 
          env=user_env
     )
     # fix permissions
     conda_root = os.path.join(user_home, ".conda")
     log.info(f"fixing ownership of '{conda_root}' for '{user_name}:{user_group}'")
     func.recursive_chown(conda_root, user_name, user_group)

     return user_env

def run_user_services_config(config, environment, exists, args):
     # configure user services and options
     user_env = environment
     user_name = config.get("name")

     if exists:
          vscode_extensions = [
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
 
     else:
          vscode_extensions = []

     services = {
          "caddy": {
               "config": {}
          }, 
          "vscode": {
               "config": {
                    "extensions": vscode_extensions
               }
          }, 
          "filebrowser": {
               "config": {}
          }, 
          "app": {
               "config": {}
          }
     } 


     cli_args_json = json.dumps(args)
     user_env_json = json.dumps(user_env)
     cli_user_json = json.dumps(config)

     for serv, settings in services.items():
          log.info(f"configuring user service: '{serv}'")
          # format dictionary arguments as json
          settings_json = json.dumps(settings)
          run(
               ['sudo', '-i', '-u', user_name, 'python3', f'/scripts/configure_{serv}.py', 
                    '--opts', cli_args_json, 
                    '--env', user_env_json, 
                    '--user', cli_user_json,
                    '--settings', settings_json], 
               env=user_env
          )

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

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

# load arguments
cli_opts = args.opts
cli_env = args.env

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)

### Get envs
user_name = cli_env.get("WORKSPACE_USER")
user_group = cli_env.get("WORKSPACE_GROUP")
user_password = cli_env.get("WORKSPACE_USER_PASSWORD")
proxy_base_url = cli_env.get("PROXY_BASE_URL")
caddy_virtual_base_url = cli_env.get("CADDY_VIRTUAL_BASE_URL")
app_bind_addr = cli_env.get("APP_BIND_ADDR")
app_base_url = cli_env.get("APP_BASE_URL")
app_user = cli_env.get("APP_USER")
app_password = cli_env.get("APP_PASSWORD")

### Set workspace env
workspace_env = cli_env

### Set config and data paths
workspace_dir = os.path.normpath(cli_env.get("WORKSPACE_HOME"))
resources_dir = os.path.normpath(cli_env.get("RESOURCES_PATH"))
data_dir = os.path.normpath(cli_env.get("DATA_PATH"))
apps_dir = os.path.normpath(cli_env.get("APPS_PATH"))
app_dir = os.path.normpath(cli_env.get("APP_ROOT_DIR"))
     
users = dict()

#USERS = f"coder:1000:100:zsh test:1001:101:bash"
USERS = f"{user_name}:{user_group}:1000:100:zsh:{user_password}"

for u in USERS.split(" "):
     configs = u.split(":")
     name = configs[0]
     group = configs[1]
     uid = configs[2]
     gid = configs[3]
     shell = configs[4]
     password = configs[5]
     home = os.path.join("/home", name)
     
     if shell == "zsh": 
          shell_path = "/usr/bin/zsh"
     elif shell == "bash":
          shell_path = "/bin/bash"
     else:
          log.warning(f"invalid shell for user '{name}': '{shell}'")

     users[name] = {
          'name': name,
          'group': group,
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
               'apps': {
                    'path': apps_dir,
                    'mode': "755"
               },
               'app': {
                    'path': app_dir,
                    'mode': "755"
               }
          }
     }

for u, config in users.items():
     name = config.get("name")
     workspace_auth_password = config.get("password")
     user_exists, home_exists, user_record = check_user(name)

     if not user_exists and not home_exists:
          log.warning(f"User and home does not exist, creating: '{name}'")
          user_env = setup_user(config, workspace_env, cli_opts)

          exists = False      
          run_user_services_config(config, user_env, exists, cli_opts)

          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=False)

     elif user_exists and not home_exists:
          # create missing user's home
          user_env = os.environ.copy()
          log.warning(f"User exists '{name}' but home is missing")
          
          #@TODO: write function similar to setup_user that copies existing 
          # shadows info and init's shell

          exists = False
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)

     elif not user_exists and home_exists:
          user_env = os.environ.copy()
          home = os.path.join("/home", name)
          log.warning(f"User does not exist but a home directory exists, creating: '{name}'")

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
          run_user_services_config(config, user_env, exists, cli_opts)
          ssh_dir = os.path.join(config.get("dirs").get("home").get("path"), ".ssh")
          log.warning("setting correct permissions on '.ssh'")
          func.recursive_chmod(ssh_dir, "600")

          # Set enviornments
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)    

     elif user_exists and home_exists:
          # All's peachy for new user
          # move old home to backup and create new user
          user_env = os.environ.copy()
          log.warning(f"User and home exists '{name}'")

          exists = True
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)                    
          
     else:
          log.error(f"User exists: 'error'")


