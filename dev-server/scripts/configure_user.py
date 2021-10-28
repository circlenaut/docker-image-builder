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
import coloredlogs
import crypt
import spwd
import requests
from copy import copy
from urllib.parse import urlparse
from subprocess import run, call, Popen, PIPE
from users_mod  import PwdFile
from pathlib import Path
from watchgod import run_process
import functions as func

def get_id(idt, idn, id_list):
     set_id = int()
     if idn in id_list:
          if idt == "uid": idn = 1000
          elif idt == "gid": idn = 100
          else: log.error(f"Unknown id type: '{idt}'")
     while idn in id_list:
          idn+=1
     else:
          set_id = idn   
     return set_id

def check_user(user_name=None, user_home=None):
     user_exists = False
     home_exists = False
     user_record = dict()
     existing_records = dict()
     user_records = PwdFile().toJSON().get("pwdRecords")

     if user_home != None:
          if os.path.exists(user_home):
               home_exists = True
          else:
               home_exists = False

     names = list()
     uids = list()
     gids = list()
     homes = list()
     for user in user_records:
          record = json.dumps(user, indent = 4)
          name = user.get("userName")
          uid = user.get("userID")
          gid = user.get("groupID")
          home = user.get("homeDirPath")

          if name != None: names.append(name)
          if uid != None: uids.append(uid)
          if gid != None: gids.append(gid)
          if home != None: homes.append(home)
          #log.debug(record)
          #log.debug(name)
          if name == user_name:
               user_record = record
               user_exists = True
               break
          else:
               user_exists = False
     existing_records = {
          'names': names,
          'groups': [], # get this in the future
          'uids': uids,
          'gids': gids,
          'homes': homes
     }

     return user_exists, home_exists, user_record, existing_records

def create_user(config):
     user_exists, home_exists, user_record, existing_records = check_user()
     existing_uids = existing_records.get("uids")
     existing_gids = existing_records.get("gids")

     user_name = config.get("name")
     home = config.get("dirs").get("home").get("path")
     uid = config.get("uid")
     gid = config.get("gid")
     shell = config.get("shell_path")

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
     sudo_config = f"{user_name} ALL=(ALL:ALL) NOPASSWD:ALL"
     
     log.info(f"adding sudo config: '{sudo_config}' to '{sudo_config_path}'")
     with open(sudo_config_path, "w") as f: 
          f.write(sudo_config + "\n")

     log.info(f"fixing sudo config permission: '{sudo_config_path}'")
     func.chmod(sudo_config_path, "440")

     log.debug(f"sudo config file:")
     log.debug(func.cat_file(sudo_config_path))
     
def setup_ssh(user_name, user_home, user_group, environment):
     workspace_env = environment
     ssh_config_dir = os.path.join(user_home, ".ssh")
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
                         try:
                              if Path(p).owner() == user_name:
                                   log.warning(f"path '{p}', already owned by '{user_name}'")
                              else:
                                   log.info(f"setting ownership of '{p}', to '{user_name}:{user_group}'")
                                   func.recursive_chown(p, user_name, user_group)
                                   log.info(f"setting mode of '{p}', to '{dir_mode}'")
                                   func.recursive_chmod(p, dir_mode)
                         except KeyError:
                              log.error(f"Error getting user for path: '{p}'")
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

def change_pass(user_name, user_home, old_password, new_password):
     user_exists, home_exists, user_record, existing_records = check_user(user_name, user_home)
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

def change_user_shell(user_name, user_home, shell):
     user_exists, home_exists, user_record, existing_records = check_user(user_name, user_home)

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
     user_home = config.get("dirs").get("home").get("path")
     system_shell = 'bash'
     workspace_dir = config.get("dirs").get("workspace").get("path")
     resources_dir = config.get("dirs").get("resources").get("path")
     user_env = environment
     
     ### Set conda envs
     conda_root = os.path.join(user_home, ".conda")
     conda_bin = os.path.join(conda_root, "bin")
     conda_rc = os.path.join(user_home, ".condarc")
     log.info(f'adding {conda_bin} to PATH')
     user_env['PATH'] += os.pathsep + conda_bin
     # required for conda to work
     user_env['USER'] = user_name
     user_env['HOME'] = user_home

     # Install conda
     return_code = shell_cmd.run_url(
          'https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh', 
          ['-b', '-u', '-p', conda_root], 
          user_env,
          verbosity
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
     local_bin = os.path.join(user_home, ".local/bin")
     user_env['PATH'] += os.pathsep + local_bin

     log.debug(func.capture_cmd_stdout('env', user_env))
     
     return user_env

def setup_user(config, environment, args):
     # Get workspace environment
     workspace_env = environment

     # Get user config
     user_name = config.get("name")
     user_group = config.get("group")
     user_password = config.get("password")
     user_shell = config.get("shell_path")
     user_home = config.get("dirs").get("home").get("path")

     log.info(f"Creating user: '{user_name}'")
     # Create user and set permissions
     create_user(config)
     set_user_paths(config)
     
     # Run setup scripts
     setup_ssh(user_name, user_home, user_group, workspace_env)
     change_pass(user_name, user_home, "password", user_password)
     change_user_shell(user_name, user_home, user_shell)
     
     # Initialize user shell and environment
     user_env = init_shell(config, workspace_env)
     
     # Create json dumps for passage into scripts
     cli_args_json = json.dumps(args)
     cli_user_json = json.dumps(config)
     user_env_json = json.dumps(user_env)
     
     # Fix permissions
     set_user_paths(config)
     
     # Run final check
     user_exists, home_exists, user_record, existing_records = check_user(user_name, user_home)
     log.debug("user record:")
     log.debug(user_record)

     ssh_dir = os.path.join(user_home, ".ssh")
     log.warning("setting correct permissions on '.ssh'")
     func.recursive_chown(ssh_dir, user_name, user_group)
     func.recursive_chmod(ssh_dir, "600")
     func.chmod(ssh_dir, "700")

     # Configure user shell
     services = ["ssh", "zsh"]
     for serv in services:
          log.info(f"configuring user service: '{serv}'")
          run(
               ['sudo', '-i', '-u', config.get("name"), 'python', f'/scripts/configure_{serv}.py', 
                    '--opts', cli_args_json, 
                    '--env', user_env_json, 
                    '--user', cli_user_json],
               env=user_env
          )

     return user_env

def run_user_services_config(config, environment, exists, args):
     # configure user services and options
     user_env = environment
     user_name = config.get("name")

     if exists:
          vscode_extensions = ['ms-python.python']
 
     else:
          vscode_extensions = []

     services = {
          "caddy": {
               "config": {}
          }, 
          "vscode": {
               "config": {"extensions": vscode_extensions}
          }, 
          "filebrowser": {
               "config": {}
          }, 
          "app": {
               "config": {}
          }
     } 

     # Create json dumps for passage into scripts
     cli_args_json = json.dumps(args)
     user_env_json = json.dumps(user_env)
     cli_user_json = json.dumps(config)

     for serv, settings in services.items():
          log.info(f"configuring user service: '{serv}'")
          # format dictionary arguments as json
          settings_json = json.dumps(settings)
          run(
               ['sudo', '-i', '-u', user_name, 'python', f'/scripts/configure_{serv}.py', 
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
parser.add_argument('--configs', type=json.loads, help='Load YAML config')

args, unknown = parser.parse_known_args()
if unknown:
    log.error("Unknown arguments " + str(unknown))

# load arguments
cli_opts = args.opts
cli_env = args.env
cli_configs = args.configs

### Set log level
verbosity = cli_opts.get("verbosity")
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

### Pull functions
shell_cmd = func.ShellCommand()

### Get envs
user_name = cli_env.get("WORKSPACE_USER")
user_group = cli_env.get("WORKSPACE_GROUP")
user_password = cli_env.get("WORKSPACE_USER_PASSWORD")

### Set workspace env
workspace_env = cli_env

### Create json dumps for passage into scripts
cli_opts_json = json.dumps(cli_opts)
workspace_env_json = json.dumps(workspace_env)

# Get existing user settings
user_exists, home_exists, user_record, existing_records = check_user()
existing_names = existing_records.get("names")
existing_groups = existing_records.get("groups")
existing_homes = existing_records.get("homes")
existing_uids = existing_records.get("uids")
existing_gids = existing_records.get("gids")

### Run user creation scripts
usr_count = 0
username_list = list()
for usr in cli_configs.get("users"):
     ### Set configs
     # set overrides
     u_name = usr.get("name")
     u_group = usr.get("group")
     u_uid = int(usr.get("uid"))
     u_gid = int(usr.get("gid"))
     
     if u_name in existing_names:
          user_override = f"{u_name}_"
          log.warning(f"Username '{u_name}' already exists! changing to '{name_override}'")
          user_name = user_override
          usr["name"] = user_override
     else:
          user_name = u_name
     username_list.append(user_name)
     if u_group in existing_groups:
          group_override = f"{u_group}_"
          log.warning(f"Group '{u_group}' already exists! changing to '{group_override}'")
          user_group = group_override
          usr["group"] = group_override
     else:
          user_group = u_group
     if u_uid in existing_uids:
          uid_override = get_id("uid", u_uid, existing_uids)
          log.warning(f"UID '{u_uid}' already exists! changing to '{uid_override}'")
          user_uid = str(uid_override)
          usr["uid"] = str(uid_override)
     else:
          user_uid = str(u_uid)
     if u_gid in existing_gids:
          gid_override = get_id("gid", u_gid, existing_gids)
          log.warning(f"GID '{u_gid}' already exists! changing to '{gid_override}'")
          user_gid = str(gid_override)
          usr["gid"] = str(gid_override)
     else:
          user_gid = str(u_gid)

     # set user shell
     if usr.get("shell") == "zsh": 
          shell_path = "/usr/bin/zsh"
     elif usr.get("shell") == "bash":
          shell_path = "/bin/bash"
     else:
          log.warning(f"invalid shell for user '{name}': '{shell}'")
     cli_configs.get("users")[usr_count]["shell_path"] = shell_path

     # set user directory ownership
     u_dirs = dict()
     for d in usr.get("directories"):
          u_dirs[d.get("name")] = dict()
          u_dirs[d.get("name")]["path"] = d.get("path")
          u_dirs[d.get("name")]["mode"] = d.get("mode")
     cli_configs.get("users")[usr_count]["dirs"] = copy(u_dirs)

     # define user folders
     u_home = cli_configs.get("users")[usr_count].get("dirs").get("home").get("path")
     if u_home in existing_homes:
          home_override = f"{u_home}_"
          log.warning(f"Home '{u_home}' already exists! changing to '{home_override}'")
          user_home = home_override
     else:
          user_home = u_home
     workspace_dir = cli_configs.get("users")[usr_count].get("dirs").get("workspace").get("path")
     config_backup_folder = workspace_dir + "/.workspace/backup/"

     user_exists, home_exists, user_record, existing_records = check_user(user_name, user_home)
     log.debug(user_record)

     # create json dump of user config for passage into scripts
     cli_user_json = json.dumps(usr)

     ### Create user and home dir on conditions
     if not user_exists and not home_exists:
          log.warning(f"User and home does not exist, creating: '{user_name}' with home '{user_home}'")

          if os.path.exists(config_backup_folder):
               log.info(f"config backup folder exists '{config_backup_folder}', restoring.")
               # Create user
               create_user(usr)
               user_exists, home_exists, user_record, existing_records = check_user(user_name, user_home)

               # Set password
               change_pass(user_name, user_home, "password", usr.get("password"))

               # Run user config restoration
               action = "restore"
               log.info(f"backup script: '{action}'")

               run(
                    ['sudo', '-i', '-u', user_name, 'python', '/scripts/backup_restore_config.py', 
                         '--opts', cli_opts_json,
                         '--env', workspace_env_json,
                         '--user', cli_user_json,
                         '--mode', action],
                    env=workspace_env
               )

               # Fix permissiosn
               set_user_paths(usr)
               
          else:
               # Create user
               log.info(f"creating user '{user_name}'")
               user_env = setup_user(usr, workspace_env, cli_opts)
               user_exists, home_exists, user_record, existing_records = check_user(user_name, user_home)
               log.debug(user_record)

               # Setup user services
               exists = False      
               run_user_services_config(usr, user_env, exists, cli_opts)

               # Setup backup script
               log.info(f"configuring user service: 'cron'")
               run(
                    ['sudo', '-i', '-u', user_name, 'python', f'/scripts/configure_cron.py', 
                         '--opts', cli_opts_json, 
                         '--env', workspace_env_json, 
                         '--user', cli_user_json],
                    env=workspace_env
               )

               for env, value in user_env.items():
                    func.set_env_variable(env, value, ignore_if_set=False)

     elif user_exists and not home_exists:
          log.warning(f"user exists '{user_name}' without a home, creating '{user_home}'...")
          # create missing user's home
          user_env = os.environ.copy()
          log.warning(f"User exists '{user_name}' but home is missing")
          
          #@TODO: write function similar to setup_user that copies existing 
          # shadows info and init's shell

          exists = False
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)

     elif not user_exists and home_exists:
          log.warning(f"user '{user_name}' does not exist but a home does exists '{user_home}', creating user but skipping home creation and shell initialization.")
          user_env = os.environ.copy()
          #log.warning(f"User does not exist but a home directory exists, creating: '{user_name}'")

          #@TODO: Impliment below when there's a way to backup/check against previous /etc/shadows file
          # move old home to backup
          #existing_home = os.path.join("/home", user_name)
          #backup_home = os.path.join("/home", f"{user_name}_previous")
          #shutil.move(existing_home, backup_home) 

          # Create user
          create_user(usr)
          # Set password
          change_pass(user_name, user_home, "password", usr.get("password"))
          # fix permissions
          set_user_paths(usr)
          # Configure services
          
          exists = True
          run_user_services_config(usr, user_env, exists, cli_opts)

          # Set enviornments
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)    

     elif user_exists and home_exists:
          # All's peachy for new user
          # move old home to backup and create new user
          user_env = os.environ.copy()
          log.warning(f"User '{user_name}' and home '{user_home}' exists")

          exists = True
          for env, value in user_env.items():
               func.set_env_variable(env, value, ignore_if_set=True)                    
          
     else:
          log.error(f"User exists: 'error'")

     ### Create conda environments
     # Set conda envs
     conda_root = os.path.join(user_home, ".conda")
     conda_bin = os.path.join(conda_root, "bin")
     log.info(f'adding {conda_bin} to PATH')
     workspace_env['PATH'] += os.pathsep + conda_bin
     # required for conda to work
     workspace_env['USER'] = user_name
     workspace_env['HOME'] = user_home

     # Execute
     log.info(f"Creating conda environments'")
     run(
          ['conda', 'run','-n', 'base', 'python', '/scripts/setup_conda_envs.py', 
               '--opts', cli_opts_json,
               '--env', workspace_env_json, 
               '--user', cli_user_json],
          env=workspace_env
     )
     log.info(f"Running installer scripts")
     run(
          ['sudo', '-i', '-u', user_name, 'python', '/scripts/run_installers.py', 
               '--opts', cli_opts_json,
               '--env', workspace_env_json,
               '--user', cli_user_json],
          env=workspace_env
     )
     startup_custom_script = os.path.join(workspace_dir, "on_startup.sh")
     if os.path.exists(startup_custom_script):
          log.info("Running user script script 'on_startup.sh' from workspace folder")
          # run startup script from workspace folder - can be used to run installation routines on workspace updates
          shell_cmd.run_script(startup_custom_script)

     # Fix permissions
     log.info(f"fixing ownership of '{conda_root}' for '{user_name}:{user_group}'")
     func.recursive_chown(conda_root, user_name, user_group)

     ### Run user config backup
     action = "backup"
     log.info(f"backup script: '{action}'")
     run(
          ['sudo', '-i', '-u', user_name, 'python', '/scripts/backup_restore_config.py', 
               '--opts', cli_opts_json,
               '--env', workspace_env_json,
               '--user', cli_user_json,
               '--mode', action],
          env=workspace_env
     )

     usr_count+=1

### Setup SSH
# pass through list of authorized users
cli_users_json = json.dumps({"users": username_list})
# execute
run(
     ['python', f'/scripts/setup_ssh.py', 
          '--opts', cli_opts_json, 
          '--env', workspace_env_json,
          '--users', cli_users_json],
     env=workspace_env
)
