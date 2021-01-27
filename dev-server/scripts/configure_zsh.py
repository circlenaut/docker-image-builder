#!/usr/bin/python

"""
Configure zsh
"""

import os
import sys
import re
import logging
from urllib.parse import quote, urljoin, urlparse
from subprocess   import run, call
from users_mod    import PwdFile

def read_file(path):
    with open(path) as f:
        lines = f.readlines()
    return lines

def check_valid_url(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    url = [x[0] for x in url]
    if len(url) > 0:
        url = url[0]
        return True
    else:
        return False

def get_url_suffix(url):
    http = urlparse(url)
    base = os.path.basename(http.path)
    return base

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
ENV_HOME = os.path.join("/home", ENV_USER)
ENV_ZSH_PROMPT = os.getenv("ZSH_PROMPT", "none")
ENV_ZSH_THEME = os.getenv("ZSH_THEME", "spaceship")
ENV_ZSH_PLUGINS = os.getenv("ZSH_PLUGINS", "all")

### Set Path to Conda
os.environ['PATH'] += os.pathsep + "/opt/conda/bin"

### Install Oh-My-Zsh
on_my_zsh_dir = os.path.join(ENV_HOME, ".oh-my-zsh")
on_my_zsh_config_path = os.path.join(ENV_HOME, ".zshrc")

if not os.path.exists(on_my_zsh_dir):
    log.info("Installing Oh-My-Zsh")
    run(
        'sh -c "$(curl https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)" --unattended',
        shell=True,
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
        'eval "$(pyenv virtualenv-init -)"',
        'autoload -U bashcompinit',
        'bashcompinit',
        'eval "$(register-python-argcomplete pipx)"',
        'export PATH="/opt/conda/bin:$PATH"',
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
                f'SOBOLE_DEFAULT_USER="{ENV_USER}"',
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
    plugins_path = os.path.join(ENV_HOME, ".oh-my-zsh/custom/plugins")
    if not os.path.exists(plugins_path): os.makedirs(plugins_path)

    for index, plugin in enumerate(plugin_list):
        if check_valid_url(plugin):
            plugin_name = get_url_suffix(plugin)
            log.info(f"installing zsh plugin: '{plugin_name}'")
            run(['git', 'clone', plugin, os.path.join(plugins_path, plugin_name)])
            plugin_list[index] = plugin_name
        else:
            plugin_name = plugin
            plugin_list[index] = plugin_name
    
    # Setup theme
    themes_path = os.path.join(ENV_HOME, ".oh-my-zsh/custom/themes")
    if not os.path.exists(themes_path): os.makedirs(themes_path)
    
    theme_name = str()
    installed_themes = list()
    if len(theme_list) > 0:
        for theme_url in theme_list:
            theme_repo = get_url_suffix(theme_url)
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

    # Setup prompt
    prompts_path = os.path.join(ENV_HOME, ".oh-my-zsh/custom/prompts")
    if not os.path.exists(prompts_path): os.makedirs(prompts_path)
    
    prompt_name = str()
    prompt_names = list()
    prompt = dict()
    prompt['none'] = dict()
    prompt['none']['config'] = []
    if len(prompt_list) > 0:
        for prompt_url in prompt_list:
            prompt_name = get_url_suffix(prompt_url)
            prompt_names.append(prompt_name)
            prompt[prompt_name] = dict()
            prompt_dir = os.path.join(prompts_path, prompt_name)
            log.info(f"installing zsh prompt: '{prompt_name}'")
            run(['git', 'clone', prompt_url, prompt_dir])
            fpath = f"fpath+={ prompt_dir}"
            prompt[prompt_name]['fpath'] = fpath

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
        sys.exit()
    
    # Write config file
    write_zsh_config(
        ENV_HOME,
        prompt.get(set_prompt), 
        theme.get(set_theme),
        plugin_list, 
        additional_args, 
        )

    ### Init Conda
    run(
        'conda init zsh',
        shell=True,
    )

    ### Setup sdkman
    run(
        'curl -s https://get.sdkman.io | bash',
        shell=True,
    )

    ### Disable auto conda activation
    run(
        'conda config --set auto_activate_base false',
        shell=True,
    )

    ### Set permissions
    #log.info(f"setting permissions on '{on_my_zsh_dir}' to '{ENV_USER}'")
    #run(['sudo', '--preserve-env', 'chown', '-R', f'{ENV_USER}:users', on_my_zsh_dir])
    #log.info(f"setting permissions on '{on_my_zsh_config_path}' to '{ENV_USER}'")
    #run(['sudo', '--preserve-env', 'chown', '-R', f'{ENV_USER}:users', on_my_zsh_config_path])

    ### Display config to console
    log.info(f"On My ZSH config:")
    log.info(call(["cat", on_my_zsh_config_path]))

else:
    log.info("Oh-My-Zsh already installed")