"""
Collection of commonly used functions
"""

import os
import sys
import psutil
import shutil
import re
import logging
import requests
from urllib.parse import quote, urljoin, urlparse
from subprocess   import run, call, Popen, PIPE

### Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

def set_env_variable(env_variable: str, value: str, ignore_if_set: bool = False):
    if ignore_if_set and os.getenv(env_variable, None):
        # if it is already set, do not set it to the new value
        return
    # TODO is export needed as well?
    run("export " + env_variable + '="' + value + '"', shell=True)
    os.environ[env_variable] = value

def chown(path, owner):
     shutil.chown(path, owner)

def chmod(path, mode):
     os.chmod(path, int(mode, base=8))

def recursive_chown(path, owner):
     for dirpath, dirnames, filenames in os.walk(path):
          chown(dirpath, owner)
          for filename in filenames:
               file_path = os.path.join(dirpath, filename)
               # Don't set permissions on symlinks
               if not os.path.islink(file_path):
                    chown(file_path, owner)

def recursive_chmod(path, mode):
     for dirpath, dirnames, filenames in os.walk(path):
          chmod(dirpath, mode)
          for filename in filenames:
               file_path = os.path.join(dirpath, filename)
               # Don't set permissions on symlinks
               if not os.path.islink(file_path):
                    chmod(file_path, mode)

def hash_password(password):
     encoded_password = password.encode()
     salt = bcrypt.gensalt()
     hashed_password = bcrypt.hashpw(password, salt).decode('utf-8')
     return hashed_password

def read_file(path):
    with open(path) as f:
        lines = f.readlines()
    return lines

def cat_file(path):
    lines = read_file(path)
    s = '\n'
    cat = s.join(lines)
    return cat

def capture_cmd_stdout(cmd, environment):
    command = cmd.split(" ")
    output= run(command, capture_output=True, text=True, env=environment).stdout
    return output

def check_valid_url(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    url = [x[0] for x in url]
    if len(url) > 0:
        url = url[0]
        return True
    else:
        return False

def clean_url(base_url):
    # set base url
    url = base_url.rstrip("/").strip()
    # always quote base url
    url = quote(base_url, safe="/%")
    return url

def get_url_hostname(url, uri_type):
    """Get the host name from the url"""
    parsed_uri = urlparse(url)
    if uri_type == 'both':
        return '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    elif uri_type == 'netloc_only':
        return '{uri.netloc}'.format(uri=parsed_uri)

def url_active(url):
    response = requests.get(url)
    if response.status_code == 200:
        return True
    else:
        return False

def get_url_suffix(url):
    http = urlparse(url)
    base = os.path.basename(http.path)
    return base

def run_shell_installer_url(url, args, environment):
    def on_terminate(proc):
        log.info("process {} terminated".format(proc))
    if check_valid_url(url) and url_active(url):
        log.info(f"installing '{url}' with arguments: '{args}''")
        filename = get_url_suffix(url)
        file_object = requests.get(url)
        with open(filename, 'wb') as installer:
            installer.write(file_object.content)
        cmd = ['sh', filename] + args
        ps = Popen(cmd, env=environment)
        procs_list = [psutil.Process(ps.pid)]
        while True: 
            gone, alive = psutil.wait_procs(procs_list, timeout=3, callback=on_terminate) 
            if len(gone)>0: 
                break
        os.remove(filename)
    else:
        log.error(f"invalid '{url}'")

def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

# These two functions are dirty, sudo -i -u is better.
def demote(user_uid, user_gid):
    def result():
        os.setgid(user_gid)
        os.setuid(user_uid)
    return result

def exec_cmd(username, cmd):
    # get user info from username
    pw_record = pwd.getpwnam(username)
    homedir = pw_record.pw_dir
    user_uid = pw_record.pw_uid
    user_gid = pw_record.pw_gid
    env = os.environ.copy()
    env.update({'HOME': homedir, 'LOGNAME': username, 'PWD': os.getcwd(), 'FOO': 'bar', 'USER': username})
    """
    Warning The preexec_fn parameter is not safe to use in the presence of threads in your application. 
    The child process could deadlock before exec is called. If you must use it, keep it trivial! 
    Minimize the number of libraries you call into.
    Ref: https://docs.python.org/3/library/subprocess.html
    """
    proc = Popen([cmd],
                              shell=True,
                              env=env,
                              preexec_fn=demote(user_uid, user_gid),
                              stdout=PIPE)
    proc.wait()
