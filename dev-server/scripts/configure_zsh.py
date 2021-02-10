#!/usr/bin/python

"""
Configure zsh
"""

import os
import sys
import psutil
import re
import logging
import coloredlogs
import requests
import argparse
import json
import pip_api
from urllib.parse import urlparse
from subprocess   import run, call, Popen
from users_mod    import PwdFile
import functions as func

def write_zsh_config(home, prompt, theme, plugin_list, additional_args):
    root_path = os.path.join(home, ".oh-my-zsh")
    config_path = os.path.join(home, ".zshrc")
    s = ' '
    plugins = s.join(plugin_list)

    zshrc_template = [
        f'export ZSH="{root_path}"',
        f'ZSH_THEME="{theme.get("name")}"',
        'source $ZSH/oh-my-zsh.sh',
        #'export LANG="en_US.UTF-8"',
        #'export LANGUAGE="en_US:en"',
        #'export LC_ALL="en_US.UTF-8"',
        'export TERM=xterm',
        f'plugins=({plugins})'
    ]

    # Create a new config file with template settings
    with open(config_path, "w") as f:
        f.write("# New settings" + "\n")
        for setting in zshrc_template:
            f.write(setting + "\n")

    # Append additional settings to config
    with open(config_path, "a") as f:
        f.write("# Additional settings" + "\n")
        for setting in additional_args:
            f.write(setting + "\n")

    # Apply prompt specific settings
    with open(config_path, "a") as f:
        f.write("# Prompt settings" + "\n")
        for setting in prompt.get("config"):
            f.write(setting + "\n")

    # Apply theme specific settings
    with open(config_path, "a") as f:
        f.write("# Theme settings" + "\n")
        for setting in theme.get("config"):
            f.write(setting + "\n")

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

### Pull functions
shell_cmd = func.ShellCommand()

### Get envs
zsh_prompt = cli_env.get("ZSH_PROMPT")
zsh_theme = cli_env.get("ZSH_THEME")
zsh_plugins = cli_env.get("ZSH_PLUGINS")

# Get user settings
user_name = cli_user.get("name")
user_shell = cli_user.get("shell_path")
user_home = cli_user.get("dirs").get("home").get("path")
workspace_dir = cli_user.get("dirs").get("workspace").get("path")

### Set zsh env
zsh_env = cli_env

### Set system path
system_path = zsh_env.get("PATH")

### Install Oh-My-Zsh
on_my_zsh_dir = os.path.join(user_home, ".oh-my-zsh")
on_my_zsh_config_path = os.path.join(user_home, ".zshrc")

if not os.path.exists(on_my_zsh_dir):
    log.info("Installing Oh-My-Zsh")
    
    return_code = shell_cmd.run_url(
        'https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh',
        ['--unattended'],
        zsh_env,
        verbosity
    )

    # Set options to load
    prompt_list = cli_user.get("zsh").get("prompt") if cli_user.get("zsh").get("prompt") != None else []
    theme_list = cli_user.get("zsh").get("theme") if cli_user.get("zsh").get("theme") != None else []
    plugin_list = cli_user.get("zsh").get("plugins") if cli_user.get("zsh").get("plugins") != None else []

    additional_args = [
        f'export PATH="{system_path}:$PATH"',
        'eval "$(pyenv virtualenv-init -)"',
        'autoload -U bashcompinit',
        'bashcompinit',
        'eval "$(register-python-argcomplete pipx)"',
        f'cd "{workspace_dir}"',
    ]

    # Theme settings
    theme = {
        'powerlevel10k': {
            'name' : 'powerlevel10k',
            'config': [
                'POWERLEVEL9K_SHORTEN_STRATEGY="truncate_to_last"',
                'POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(user dir vcs status)',
                'POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=()',
                'POWERLEVEL9K_STATUS_OK=false',
                'POWERLEVEL9K_STATUS_CROSS=true',
            ]
        },
        # configs: https://denysdovhan.com/spaceship-prompt/docs/Options.html#exit-code-exit_code
        'spaceship': {
            'name': 'spaceship',
            'config': [
                'SPACESHIP_PROMPT_ADD_NEWLINE="false"',
                'SPACESHIP_PROMPT_SEPARATE_LINE="false"',
                'SPACESHIP_HOST_SHOW="false"',
                'SPACESHIP_USER_SHOW="false"',
            ]
        },
        'sobole': {
            'name': 'sobole',
            'config': [
                'SOBOLE_THEME_MODE="dark"',
                f'SOBOLE_DEFAULT_USER="{user_name}"',
                'SOBOLE_DONOTTOUCH_HIGHLIGHTING="false"',
            ]
        },
        'none': {
            'name': '',
            'config': []
        }
    }

    oh_my_zsh_themes = [
        "robbyrussell",
        ]

    # Setup plugins
    plugins_path = os.path.join(user_home, ".oh-my-zsh/custom/plugins")
    if not os.path.exists(plugins_path): os.makedirs(plugins_path)

    for index, plugin in enumerate(plugin_list):
        if func.check_valid_url(plugin):
            if func.url_active(plugin):
                plugin_name = func.get_url_suffix(plugin)
                log.info(f"installing zsh plugin: '{plugin_name}'")
                run(['git', 'clone', plugin, os.path.join(plugins_path, plugin_name)])
                plugin_list[index] = plugin_name
            else:
                log.error(f"repo down, skipping: '{plugin}'")                
        else:
            plugin_name = plugin
            plugin_list[index] = plugin_name
    
    # Setup theme
    themes_path = os.path.join(user_home, ".oh-my-zsh/custom/themes")
    if not os.path.exists(themes_path): os.makedirs(themes_path)

    theme_name = str()
    installed_themes = list()
    if len(theme_list) > 0:
        for theme_url in theme_list:
            if func.url_active(theme_url):
                theme_repo = func.get_url_suffix(theme_url)
                theme_dir = os.path.join(themes_path, theme_repo)
                log.info(f"installing zsh theme: '{theme_repo}'")
                run(['git', 'clone', theme_url, theme_dir])
                for f in os.listdir(theme_dir):
                    n = f.split(".")
                    if len(n) == 2:
                        if n[1] == "zsh-theme": 
                            theme_name = n[0]
                            installed_themes.append(theme_name)
                            ext = n[1]
                            filename = "{}.{}".format(theme_name, ext)
                            os.symlink(
                                os.path.join(theme_dir, filename), 
                                os.path.join(themes_path, filename)
                            )
            else:
                log.error(f"repo down, skipping: '{theme_url}'")

    # Setup prompt
    prompts_path = os.path.join(user_home, ".oh-my-zsh/custom/prompts")
    if not os.path.exists(prompts_path): os.makedirs(prompts_path)
    
    prompt_name = str()
    prompt_names = list()
    prompt = dict()
    prompt['none'] = dict()
    prompt['none']['config'] = []
    if len(prompt_list) > 0:
        for prompt_url in prompt_list:
            if func.url_active(prompt_url):
                prompt_name = func.get_url_suffix(prompt_url)
                prompt_names.append(prompt_name)
                prompt[prompt_name] = dict()
                prompt_dir = os.path.join(prompts_path, prompt_name)
                log.info(f"installing zsh prompt: '{prompt_name}'")
                run(['git', 'clone', prompt_url, prompt_dir])
                fpath = f"fpath+={ prompt_dir}"
                prompt[prompt_name]['fpath'] = fpath
            else:
                log.error(f"repo down, skipping: '{prompt_url}'")            

    # Specify prompt specific settings
    if prompt_name == "pure": 
        prompt[prompt_name]['config'] = [
            prompt.get(prompt_name).get("fpath"),
            "autoload -U promptinit",
            "promptinit",
            f"prompt {prompt_name}",
        ]

    # Run validation checks
    default_theme = "robbyrussell"
    set_prompt = cli_user.get("zsh").get("set_prompt") if cli_user.get("zsh").get("set_prompt") != None else "none"
    set_theme = cli_user.get("zsh").get("set_theme") if cli_user.get("zsh").get("set_theme") != None else default_theme
        
    if set_prompt in prompt_names or set_prompt == "none":
        log.info(f"ZSH prompt set to: '{set_prompt}'")
    else:
        log.critical(f"Invalid ZSH prompt: '{set_prompt}'")
        sys.exit()
    
    if set_theme in installed_themes:
        if not set_prompt == "none":
            log.warning(f"Cannot use ZSH prompt '{set_prompt}' with themes. Disabling")
            set_prompt = "none"
        log.info(f"ZSH theme set to: '{set_theme}'")
    elif set_theme in oh_my_zsh_themes:
        if not set_prompt == "none":
            log.warning(f"Cannot use ZSH prompt '{set_prompt}' with themes. Disabling")
            set_prompt = "none"
        theme[set_theme] = dict()
        theme[set_theme]['name'] = set_theme
        theme[set_theme]['config'] = []
        log.info(f"ZSH theme set to: '{set_theme}'")
    elif set_theme == "none":
        if not set_prompt in prompt_names:
            log.warning(f"Must set ZSH theme when no prompt is specified.")
            sys.exit()
        log.info(f"ZSH theme set to: '{set_theme}'")
    else:
        log.error(f"Invalid theme: '{set_theme}'")
        set_theme = default_theme
        theme[set_theme] = dict()
        theme[set_theme]['name'] = set_theme
        theme[set_theme]['config'] = []
        log.info(f"ZSH theme set to: '{set_theme}'")

    # Write config file
    write_zsh_config(
        user_home,
        prompt.get(set_prompt), 
        theme.get(set_theme),
        plugin_list, 
        additional_args, 
    )

    # Init conda
    log.info(f"initializing conda on '{user_shell}'")
    run(['conda', 'init', 'zsh'], env=zsh_env)
    
    # Install conda base
    run(
        ['conda', 'install', '-c', 'conda-forge', '--quiet', '--yes',
            'python=3.8',
            'pip',
            'psutil',
            'pyyaml',
            'yaml',
            'yamale',
            'coloredlogs'
            ],
        env=zsh_env
    )
    # Disable auto conda activation
    log.info(f"disabling conda auto activation for '{user_shell}'")
    run(
        ['conda', 'config', '--set', 'auto_activate_base', 'false'],
        env=zsh_env
    )
    # Disable showing active conda environment at command line prompt; zsh does this.
    log.info(f"disabling cli display of active environment '{user_shell}'")
    run(
        ['conda', 'config', '--set', 'changeps1', 'false'],
        env=zsh_env
    )
    ### Configure Git
    log.info(f"setting git config for '{user_name}': core.fileMode=false")
    run(
        ['git', 'config', '--global', 'core.fileMode', 'false'],
        env=zsh_env
    )
    log.info(f"setting git config for '{user_name}': http.sslVerify=false")
    run(
        ['git', 'config', '--global', 'http.sslVerify', 'false'],
        env=zsh_env
    )
    log.info(f"setting git config for '{user_name}': credential.helper='cache --timeout=31540000'")
    run(
        ['git', 'config', '--global', 'credential.helper', '"cache --timeout=31540000"'],
        env=zsh_env
    )

    #@TODO: get this working
    ### Install pip packages
    #for app in pip_api.installed_distributions():
    #    log.error(app.name)
    run(
        ['pip3', 'install',
            'Pygments',
            'ranger-fm',
            'thefuck',
            'bpytop'],
        env=zsh_env
    )

    #@TODO: doesn't work, fix
    ### Setup sdkman
    #return_code = shell_cmd.run_url(
    #    'https://get.sdkman.io ',
    #    [],
    #    zsh_env,
    #    verbosity
    #)

    run(
        'curl -s https://get.sdkman.io | bash',
        shell=True,
    )

    ### Display config to console
    log.debug(f"On My ZSH config:")
    log.debug(func.capture_cmd_stdout(f'cat {on_my_zsh_config_path}', zsh_env))

else:
    log.warning("Oh-My-Zsh already installed")