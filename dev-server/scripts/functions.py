"""
Collection of commonly used functions
"""

import os
import sys
import re
import json
import psutil
import shutil
import yamale
import requests
import logging
import coloredlogs
from urllib.parse import quote, urljoin, urlparse
from subprocess   import run, call, Popen, PIPE

### Enable logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s', 
    level=logging.INFO, 
    stream=sys.stdout)

log = logging.getLogger(__name__)

# Set log level
verbosity = os.getenv("LOG_VERBOSITY", "INFO")
log.setLevel(verbosity)
# Setup colored console logs
coloredlogs.install(fmt='%(asctime)s [%(levelname)s] %(message)s', level=verbosity, logger=log)

### Define classes

class ShellCommand(object):
    def __init__(self):
        self.track_exit = int()

    def run_script(self, path, args=None, environment=None, verbosity='INFO'):
        return_code = -1
        log.setLevel(verbosity)
        def on_terminate(proc, level=verbosity):
            log.debug("process {} terminated".format(proc))
            self.track_exit = proc.returncode
        if args != None:
            if isinstance(args, list):
                cmd = ['sh', path] + args
            else:
                log.error(f"is not at list!: '{args}'")
                sys.exit()
        else:
            cmd = ['sh', path]
        if environment != None:
            ps = Popen(cmd, env=environment)
        else:
            ps = Popen(cmd)
        procs_list = [psutil.Process(ps.pid)]
        while True: 
            gone, alive = psutil.wait_procs(procs_list, timeout=3, callback=on_terminate) 
            if len(gone)>0: 
                break
        return_code = self.track_exit
        return return_code

    def run_url(self, url, args=None, environment=None, verbosity='INFO'):
        return_code = -1
        log.setLevel(verbosity)
        if check_valid_url(url) and url_active(url):
            log.info(f"installing '{url}' with arguments: '{args}''")
            filename = get_url_suffix(url)
            file_object = requests.get(url)
            with open(filename, 'wb') as installer:
                installer.write(file_object.content)
            return_code = self.run_script(filename, args, environment, verbosity)
            os.remove(filename)
        else:
            log.error(f"invalid '{url}'")
        return return_code    

### Define functions

def set_env_variable(env_variable: str, value: str, ignore_if_set: bool = False):
    if ignore_if_set and os.getenv(env_variable, None):
        # if it is already set, do not set it to the new value
        return
    # TODO is export needed as well?
    run("export " + env_variable + '="' + value + '"', shell=True)
    os.environ[env_variable] = value

def chown(path, user, group):
     shutil.chown(path, user, group)

def chmod(path, mode):
     os.chmod(path, int(mode, base=8))

def recursive_chown(path, user, group):
     for dirpath, dirnames, filenames in os.walk(path):
          chown(dirpath, user, group)
          for filename in filenames:
               file_path = os.path.join(dirpath, filename)
               # Don't set permissions on symlinks
               if not os.path.islink(file_path):
                    chown(file_path, user, group)

def recursive_chmod(path, mode):
     for dirpath, dirnames, filenames in os.walk(path):
          chmod(dirpath, mode)
          for filename in filenames:
               file_path = os.path.join(dirpath, filename)
               # Don't set permissions on symlinks
               if not os.path.islink(file_path):
                    chmod(file_path, mode)

def recursive_make_dir(path, user=None, group=None, mode=None):
    def make_forward(dest):
        parent_dir = os.path.dirname(dest)
        if os.path.exists(parent_dir):
            # Get parent mode and permissions
            stat_info = os.stat(parent_dir)
            uid = stat_info.st_uid
            gid = stat_info.st_gid
            user = user if user else pwd.getpwuid(uid)[0]
            group = group if group else grp.getgrgid(gid)[0]
            mask = mode if mode else str(oct(stat_info.st_mode)[-3:])
            # create dir and set permissions and mask
            log.debug(f"creating: '{dest}' set to: '{user}:{group}:{mask}'")
            os.mkdir(dest)
            chown(dest, user, group)
            chmod(dest, mask)
        else:
            log.error(f"parent directory does not exist! '{parent_dir}'")

def yaml_valid(schema, data, level):
    log.setLevel(level)
    try:
        yamale.validate(schema, data)
        return True
    except yamale.YamaleError as e:
        log.error('YAML Validation failed!\n%s' % str(e))
        return False

def is_json(path):
  try:
    json_object = json.loads(path)
  except ValueError as e:
    return False
  return True

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
