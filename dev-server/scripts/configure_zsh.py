#!/usr/bin/python

"""
Configure zsh
"""

import os
import sys
import psutil
import re
import logging
import requests
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

### Read system envs
ENV_USER = os.getenv("USER", "coder")

### Read docker envs
ENV_WORKSPACE_USER = os.getenv("WORKSPACE_USER", "coder")
ENV_WORKSPACE_AUTH_PASSWORD =  os.getenv("WORKSPACE_AUTH_PASSWORD", "password")
ENV_RESOURCES_PATH = os.getenv("RESOURCES_PATH", "/resources")
ENV_WORKSPACE_HOME = os.getenv("WORKSPACE_HOME", "/workspace")
ENV_DATA_PATH = os.getenv("DATA_PATH", "/data")
ENV_APPS_PATH = os.getenv("APPS_PATH", "/apps")
ENV_ZSH_PROMPT = os.getenv("ZSH_PROMPT", "none")
ENV_ZSH_THEME = os.getenv("ZSH_THEME", "spaceship")
ENV_ZSH_PLUGINS = os.getenv("ZSH_PLUGINS", "all")

### Clean up envs
user = ENV_WORKSPACE_USER
home = os.path.join("/home", ENV_WORKSPACE_USER)

### Set config and data paths
workspace_dir = os.path.normpath(ENV_WORKSPACE_HOME)
resources_dir = os.path.normpath(ENV_RESOURCES_PATH)

### Set zsh envs
zsh_env = os.environ.copy()
zsh_env['USER'] = user
zsh_env['HOME'] = home
zsh_env['WORKSPACE_USER'] = user
zsh_env['WORKSPACE_USER_HOME'] = home


### Set Path
# conda
conda_root = os.path.join(home, ".conda")
conda_bin_path = os.path.join(conda_root, "bin")
conda_bin_dir = os.path.join(conda_root, 'condabin')
conda_exe = os.path.join(conda_root, 'condabin', 'conda')
#zsh_env['PATH'] += os.pathsep + conda_bin_path
#zsh_env['PATH'] += os.pathsep + conda_bin_dir

# pyenv dir
pyenv_root = f"{resources_dir}/.pyenv"
#zsh_env['PATH'] += os.pathsep + os.path.join(pyenv_root, "shims")
#zsh_env['PATH'] += os.pathsep + os.path.join(pyenv_root, "bin")

# local
local_bin = os.path.join(home, ".local/bin")
#zsh_env['PATH'] += os.pathsep + local_bin
system_path = zsh_env.get("PATH")

### Install Oh-My-Zsh
on_my_zsh_dir = os.path.join(home, ".oh-my-zsh")
on_my_zsh_config_path = os.path.join(home, ".zshrc")

if not os.path.exists(on_my_zsh_dir):
    log.info("Installing Oh-My-Zsh")

    func.run_shell_installer_url(
        'https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh',
        ['--unattended'],
        zsh_env
    )

    # Set options to load
    prompt_list = [
        "https://github.com/sindresorhus/pure",
    ]

    theme_list = [
        "https://github.com/romkatv/powerlevel10k",
        "https://github.com/denysdovhan/spaceship-prompt",
        "https://github.com/sobolevn/sobole-zsh-theme",
    ]

    plugin_list = [
        "git",
        "k",
        "extract",
        "cp",
        "yarn",
        "npm",
        "supervisor",
        "rsync",
        "command-not-found",
        "autojump",
        "colored-man-pages",
        "git-flow",
        "git-extras",
        "python",
        "zsh-autosuggestions",
        "history-substring-search",
        "zsh-completions",
        "ssh-agent",
        "https://github.com/zsh-users/zsh-autosuggestions",
        "https://github.com/zsh-users/zsh-completions",
        "https://github.com/zsh-users/zsh-syntax-highlighting",
        "https://github.com/zsh-users/zsh-history-substring-search",
        "https://github.com/supercrabtree/k",
    ]

    additional_args = [
        f'export PATH="{system_path}:$PATH"',
        'eval "$(pyenv virtualenv-init -)"',
        'autoload -U bashcompinit',
        'bashcompinit',
        'eval "$(register-python-argcomplete pipx)"',
        f'export PATH="{conda_bin_dir}:$PATH"',
        f'export PATH="{conda_bin_path}:$PATH"',
        f'export PATH="{local_bin}:$PATH"',
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
                f'SOBOLE_DEFAULT_USER="{ENV_WORKSPACE_USER}"',
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
    plugins_path = os.path.join(home, ".oh-my-zsh/custom/plugins")
    if not os.path.exists(plugins_path): os.makedirs(plugins_path)

    for index, plugin in enumerate(plugin_list):
        if func.check_valid_url(plugin):
            if func.url_active(plugin):
                plugin_name = func.get_url_suffix(plugin)
                log.info(f"installing zsh plugin: '{plugin_name}'")
                run(['git', 'clone', plugin, os.path.join(plugins_path, plugin_name)])
                plugin_list[index] = plugin_name
            else:
                log.info(f"repo down, skipping: '{plugin}'")                
        else:
            plugin_name = plugin
            plugin_list[index] = plugin_name
    
    # Setup theme
    themes_path = os.path.join(home, ".oh-my-zsh/custom/themes")
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
                log.info(f"repo down, skipping: '{theme_url}'")

    # Setup prompt
    prompts_path = os.path.join(home, ".oh-my-zsh/custom/prompts")
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
                log.info(f"repo down, skipping: '{prompt_url}'")            

    # Specify prompt specific settings
    if prompt_name == "pure": 
        prompt[prompt_name]['config'] = [
            prompt.get(prompt_name).get("fpath"),
            "autoload -U promptinit",
            "promptinit",
            f"prompt {prompt_name}",
        ]

    # Run validation checks
    set_prompt = ENV_ZSH_PROMPT
    set_theme = ENV_ZSH_THEME
    default_theme = "robbyrussell"
        
    if set_prompt in prompt_names or set_prompt == "none":
        log.info(f"ZSH prompt set to: '{set_prompt}'")
    else:
        log.info(f"Invalid ZSH prompt: '{set_prompt}'")
        sys.exit()
    
    if set_theme in installed_themes:
        if not set_prompt == "none":
            log.info(f"Cannot use ZSH prompt '{set_prompt}' with themes. Disabling")
            set_prompt = "none"
        log.info(f"ZSH theme set to: '{set_theme}'")
    elif set_theme in oh_my_zsh_themes:
        if not set_prompt == "none":
            log.info(f"Cannot use ZSH prompt '{set_prompt}' with themes. Disabling")
            set_prompt = "none"
        theme[set_theme] = dict()
        theme[set_theme]['name'] = set_theme
        theme[set_theme]['config'] = []
        log.info(f"ZSH theme set to: '{set_theme}'")
        log.info(theme.get(set_theme).get("name"))
    elif set_theme == "none":
        if not set_prompt in prompt_names:
            log.info(f"Must set ZSH theme when no prompt is specified.")
            sys.exit()
        log.info(f"ZSH theme set to: '{set_theme}'")
    else:
        log.info(f"Invalid theme: '{set_theme}'")
        set_theme = default_theme
        theme[set_theme] = dict()
        theme[set_theme]['name'] = set_theme
        theme[set_theme]['config'] = []
        log.info(f"ZSH theme set to: '{set_theme}'")
        log.info(theme.get(set_theme).get("name"))

    # Write config file
    write_zsh_config(
        home,
        prompt.get(set_prompt), 
        theme.get(set_theme),
        plugin_list, 
        additional_args, 
    )


    ### Setup Conda
    #@TODO: See why conda's not loading to PATH
    # Init Conda
    run(
        [conda_exe, 'init', 'zsh'],
        env=zsh_env
    )
    # Install conda base
    run(
        [conda_exe, 'install', '-c', 'conda-forge', '--quiet', '--yes',
            'python=3.8',
            'pip',
            'pyyaml',
            'yaml'],
        env=zsh_env
    )
    # disable auto load on login
    run(
        [conda_exe, 'config', '--set', 'auto_activate_base', 'false'],
        env=zsh_env
    )
    
    ### Configure Git
    run(
        ['git', 'config', '--global', 'core.fileMode', 'false'],
        env=zsh_env
    )
    run(
        ['git', 'config', '--global', 'http.sslVerify', 'false'],
        env=zsh_env
    )
    run(
        ['git', 'config', '--global', 'credential.helper', '"cache --timeout=31540000"'],
        env=zsh_env
    )

    ### Install pip packages
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
    #func.run_shell_installer_url(
    #    'https://get.sdkman.io ',
    #    [],
    #    zsh_env
    #)

    run(
        'curl -s https://get.sdkman.io | bash',
        shell=True,
    )

    ### Set permissions
    #log.info(f"setting permissions on '{on_my_zsh_dir}' to '{ENV_WORKSPACE_USER}'")
    #run(['sudo', '--preserve-env', 'chown', '-R', f'{ENV_WORKSPACE_USER}:users', on_my_zsh_dir])
    #log.info(f"setting permissions on '{on_my_zsh_config_path}' to '{ENV_WORKSPACE_USER}'")
    #run(['sudo', '--preserve-env', 'chown', '-R', f'{ENV_WORKSPACE_USER}:users', on_my_zsh_config_path])

    ### Display config to console
    log.info(f"On My ZSH config:")
    log.info(call(["cat", on_my_zsh_config_path]))

else:
    log.info("Oh-My-Zsh already installed")