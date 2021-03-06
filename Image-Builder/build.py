
#!/usr/bin/env python

"""
Build script adapted from docker-py

Refs:
- https://docker-py.readthedocs.io/en/stable/images.html
- https://github.com/docker/docker-py/blob/master/docker/utils/build.py
- https://github.com/docker/docker-py/blob/master/docker/api/build.py
- https://github.com/docker/docker-py/blob/master/docker/utils/decorators.py
- https://github.com/docker/docker-py/blob/master/docker/utils/fnmatch.py
- https://docs.docker.com/engine/context/working-with-contexts/
- https://github.com/docker/docker-py/issues/538
- https://github.com/docker/docker-py/pull/209
- https://github.com/docker/docker-py/issues/974
- https://github.com/docker/docker-py/issues/2079
- https://github.com/docker/docker-py/issues/980
- https://github.com/docker/docker-py/issues/2682
- https://stackoverflow.com/questions/58204987/docker-python-client-not-building-image-from-custom-context
- https://stackoverflow.com/questions/53743886/create-docker-from-tar-with-python-docker-api

"""

#@TODO:
# - incorporate elements from these:
#   https://raw.githubusercontent.com/bgruening/docker-build/master/build.py
#   https://github.com/AlienVault-Engineering/pybuilder-docker/blob/master/src/main/python/pybuilder_docker/__init__.py
#   https://github.com/stencila/dockta

import os
import io
import re
import sys
import grp
import pwd
import json
import enum
import platform
import argparse
import subprocess
import logging
import shutil
import tarfile
import tempfile
from math import floor
from time import time, sleep
from urllib.parse import quote, urljoin

### Set constants
IS_WINDOWS_PLATFORM = (sys.platform == 'win32')
_SEP = re.compile('/|\\\\') if IS_WINDOWS_PLATFORM else re.compile('/')
_cache = {}
_MAXCACHE = 100

### Define functions
def split_path(p):
    return [pt for pt in re.split(_SEP, p) if pt and pt != '.']

def normalize_slashes(p):
    if IS_WINDOWS_PLATFORM:
        return '/'.join(split_path(p))
    return p

def fnmatch(name, pat):
    """Test whether FILENAME matches PATTERN.
    Patterns are Unix shell style:
    *       matches everything
    ?       matches any single character
    [seq]   matches any character in seq
    [!seq]  matches any char not in seq
    An initial period in FILENAME is not special.
    Both FILENAME and PATTERN are first case-normalized
    if the operating system requires it.
    If you don't want this, use fnmatchcase(FILENAME, PATTERN).
    """

    name = name.lower()
    pat = pat.lower()
    return fnmatchcase(name, pat)

def fnmatchcase(name, pat):
    """Test whether FILENAME matches PATTERN, including case.
    This is a version of fnmatch() which doesn't case-normalize
    its arguments.
    """

    try:
        re_pat = _cache[pat]
    except KeyError:
        res = translate(pat)
        if len(_cache) >= _MAXCACHE:
            _cache.clear()
        _cache[pat] = re_pat = re.compile(res)
    return re_pat.match(name) is not None

def translate(pat):
    """Translate a shell PATTERN to a regular expression.
    There is no way to quote meta-characters.
    """
    i, n = 0, len(pat)
    res = '^'
    while i < n:
        c = pat[i]
        i = i + 1
        if c == '*':
            if i < n and pat[i] == '*':
                # is some flavor of "**"
                i = i + 1
                # Treat **/ as ** so eat the "/"
                if i < n and pat[i] == '/':
                    i = i + 1
                if i >= n:
                    # is "**EOF" - to align with .gitignore just accept all
                    res = res + '.*'
                else:
                    # is "**"
                    # Note that this allows for any # of /'s (even 0) because
                    # the .* will eat everything, even /'s
                    res = res + '(.*/)?'
            else:
                # is "*" so map it to anything but "/"
                res = res + '[^/]*'
        elif c == '?':
            # "?" is any char except "/"
            res = res + '[^/]'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j + 1
            if j < n and pat[j] == ']':
                j = j + 1
            while j < n and pat[j] != ']':
                j = j + 1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\', '\\\\')
                i = j + 1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)

    return res + '$'

### Define classes
class BuildError(ValueError):
    '''raise this when there's a ValueError during the build process'''

class Settings(object):
    def __init__(self):
        self.arg = self.get_arg()

    def get_arg(self):
        self.parser = argparse.ArgumentParser()
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--opts', type=json.loads, help='Set script arguments')
        self.parser.add_argument('--log_level', choices=('debug', 'info', 'warning', 'error', 'critical'), default='info', const='info', nargs='?', required=False, help='Set script log level of verbosity')
        self.parser.add_argument('--config', type=str, default='default', required=True, help="Location of build YAML file")
        self.parser.add_argument('--push', action='store_true', default=False, required=False, help="Push images to repositoy")
        self.parser.add_argument('--repository', type=str, default='', required=False, help="Repository to push to")
        self.parser.add_argument('--save', type=str, required=False, help="Location to save image")
        self.parser.add_argument('--dryrun', action='store_true', default=False, required=False, help='Execute as a dry run')
        self.parser.add_argument('--gzip', action='store_true', default=False, required=False, help='Compress context files')
        self.parser.add_argument('--overwrite', action='store_true', default=False, required=False, help='Overwrite existing build files')
        self.parser.add_argument('--rm_build_files', action='store_true', default=False, required=False, help='Overwrite existing build files')
        self.parser.add_argument('-f', '--force', action='store_true', default=False, required=False, help='Force a command without checks')
        self.parser.add_argument('-rmi', '--rm_inter_imgs', action='store_true', default=False, required=False, help='Remove intermediary images')
        #self.parser.add_argument('-s, --save', type=str, required=False, help="Location to save image")
        
        args, unknown = self.parser.parse_known_args()
        if unknown:
            print("Unknown arguments " + str(unknown))

        self.arg = self.parser.parse_args()
        return self.arg

class Pattern(object):
    def __init__(self, pattern_str):
        self.exclusion = False
        if pattern_str.startswith('!'):
            self.exclusion = True
            pattern_str = pattern_str[1:]

        self.dirs = self.normalize(pattern_str)
        self.cleaned_pattern = '/'.join(self.dirs)

    @classmethod
    def normalize(cls, p):

        # Leading and trailing slashes are not relevant. Yes,
        # "foo.py/" must exclude the "foo.py" regular file. "."
        # components are not relevant either, even if the whole
        # pattern is only ".", as the Docker reference states: "For
        # historical reasons, the pattern . is ignored."
        # ".." component must be cleared with the potential previous
        # component, regardless of whether it exists: "A preprocessing
        # step [...]  eliminates . and .. elements using Go's
        # filepath.".
        i = 0
        split = split_path(p)
        while i < len(split):
            if split[i] == '..':
                del split[i]
                if i > 0:
                    del split[i - 1]
                    i -= 1
            else:
                i += 1
        return split

    def match(self, filepath):
        return fnmatch(normalize_slashes(filepath), self.cleaned_pattern)

class PatternMatcher(object):
    def __init__(self, patterns):
        self.patterns = list(filter(
            lambda p: p.dirs, [Pattern(p) for p in patterns]
        ))
        self.patterns.append(Pattern('!.dockerignore'))

    def matches(self, filepath):
        matched = False
        parent_path = os.path.dirname(filepath)
        parent_path_dirs = split_path(parent_path)

        for pattern in self.patterns:
            negative = pattern.exclusion
            match = pattern.match(filepath)
            if not match and parent_path != '':
                if len(pattern.dirs) <= len(parent_path_dirs):
                    match = pattern.match(
                        os.path.sep.join(parent_path_dirs[:len(pattern.dirs)])
                    )

            if match:
                matched = not negative

        return matched

    def walk(self, root):
        def rec_walk(current_dir):
            for f in os.listdir(current_dir):
                fpath = os.path.join(
                    os.path.relpath(current_dir, root), f
                )
                if fpath.startswith('.' + os.path.sep):
                    fpath = fpath[2:]
                match = self.matches(fpath)
                if not match:
                    yield fpath

                cur = os.path.join(root, fpath)
                if not os.path.isdir(cur) or os.path.islink(cur):
                    continue

                if match:
                    # If we want to skip this file and it's a directory
                    # then we should first check to see if there's an
                    # excludes pattern (e.g. !dir/file) that starts with this
                    # dir. If so then we can't skip this dir.
                    skip = True

                    for pat in self.patterns:
                        if not pat.exclusion:
                            continue
                        if pat.cleaned_pattern.startswith(
                                normalize_slashes(fpath)):
                            skip = False
                            break
                    if skip:
                        continue
                for sub in rec_walk(cur):
                    yield sub

        return rec_walk(root)

class Basics(Settings):
    def __init__(self):
        Settings.__init__(self)
    
    def continue_input(self, prompt=True):
        yes = False
        while not yes:
            if prompt:
                self.logger.info("continue?")
            answer = input("(y/n): ")
            self.logger.info(answer)
            if answer.lower() in ["true", "yes", "y"]:
                yes = True
            elif answer.lower() in ["false", "no", "n"]:
                yes = False
                break
            else:
                self.logger.error(f"invalid response, try again: '{answer}'") 
        return yes

    def read_file(self, p):
        if self.valid_file(p, logger=True):
            with open(p) as f:
                lines = f.readlines()
            return lines

    def print_list(self, lst):
        for e in lst:
            print(e)

    def is_type_path(self, entry):
        spl = entry.split(os.sep)
        s = pathlib.PurePath(entry).suffix
        if len(spl) > 1:
            return True
        elif s:
            return True
        else:
            return False

    def valid_file(self, path, logger=False):
        try:
            exists = os.path.exists(path)
        except PermissionError:
            self.logger.error(f"permission denied: '{path}'")
            return
        except Exception as err:
            self.logger.error(f"{err}")    
            return    
        if exists:
            if os.path.isfile(path):
                return True
            else:
                if logger: 
                    self.logger.error(f"not a file: '{source}'")
                return False
        else:
            if logger:
                self.logger.error(f"does not exist: '{path}'")
            return False

    def valid_dir(self, path, logger=False):
        try:
            exists = os.path.exists(path)
        except PermissionError:
            self.logger.error(f"permission denied: '{path}'")
            return
        except Exception as err:
            self.logger.error(f"{err}")    
            return    
        if exists:
            if os.path.isdir(path):
                return True
            else:
                if logger: 
                    self.logger.error(f"not a directory: '{source}'")
                return False
        else:
            if logger:
                self.logger.error(f"does not exist: '{path}'")
            return False

class Logging(Basics):
    def __init__(self):
        Basics.__init__(self)
        self.logger = self.setup_logging()
        self.work_dir = os.path.dirname(os.path.abspath(__file__))
    
    def setup_logging(self):
        logging.basicConfig(
            format='[%(levelname)s] %(message)s',
            level=logging.INFO,
            stream=sys.stdout)
        self.log = logging.getLogger(__name__)   
        self.log.setLevel(self.arg.log_level.upper())
        return self.log
    
    def color_logs(self):
        coloredlogs.install(fmt='[%(levelname)s] %(message)s', level=self.arg.log_level.upper(), logger=self.log)

    def save_logs(self, path):
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        fh = logging.FileHandler(path)
        fh.setLevel(self.arg.log_level.upper())
        fh.setFormatter(formatter)
        self.log.addHandler(fh)
        return self.log

class Setup(Logging):
    def __init__(self):
        Logging.__init__(self)
        self.pip = ['pip3', '--version']
    
    def execute(self, cmd):
        try:
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        except FileNotFoundError:
            self.logger.error("command not found: '{c}'".format(c=" ".join(cmd)))
    
    def exit_code(self, cmd, logger=None):
        sp = self.execute(cmd)
        if sp == None:
            status = -1
            return status
        else:
            status = sp.wait()
            out, err = sp.communicate()
            self.logger.debug("console: {o}".format(o=out.rstrip('\r\n')))
            self.logger.debug("error: {e}".format(e=err))
            return status
    
    def install(self, required_pkgs):
        if not self.arg.force:
            self.check_linux()
        local_bin = os.path.join(os.getenv("HOME"), ".local/bin")
        def is_installed(requirement):
            import pkg_resources
            try:
                pkg_resources.require(requirement)
            except pkg_resources.ResolutionError:
                return False
            else:
                return True
        def is_local_path_set():
            exists = False
            paths = os.getenv("PATH").split(":")
            for p in paths:
                if p == local_bin:
                    exists = True
            return exists
        if not is_local_path_set():
            os.environ["PATH"] += os.pathsep + local_bin
        for pkg in required_pkgs:
            installed = is_installed(pkg)
            if installed == False:
                if not self.arg.force:
                    self.check_pip()
                p = pkg.split(">=")
                self.logger.info(f"installing: '{p[0]}'")
                if not self.arg.force: 
                    if self.continue_input():
                        subprocess.run(['pip3', 'install', pkg])
                    else:
                        sys.exit()
                else:
                    subprocess.run(['pip3', 'install', pkg])
    
    def check_pip(self):
        exit_code = self.exit_code(self.pip)
        if exit_code == 0:
            self.logger.debug("Pip installation found")
        else:
            self.logger.error("Pip is not installed!")
            sys.exit()

    def check_linux(self):
        sys_arch = platform.system()
        if sys_arch == "Linux":
            self.logger.debug(f"Running on: '{sys_arch}'")
            is_linux = True
            return True
        else:
            self.logger.warning(f"This script has not been tested on '{sys_arch}'")
            if not self.continue_input():
                sys.exit()

class PushStatus(object):
    def __init__(self):
        self.tracker = list()
        self.layer = dict()
        self.progress_tracker = dict()
        self.num_trackers = list()
        self.num_identities = list()
        self.pbar = dict()
        self.transfer_tracker = dict()
        self.time_tracker = dict()

    def store(self, progress):
        for status in self.tracker:
            if status.get("id") != None:
                self.layer[status.get("id")] = None
            for i in self.layer.keys():
                if i == status.get("id"):
                    if self.progress_tracker.get(status.get("id")) == None:
                        self.progress_tracker[status.get("id")] = list()
                    else:
                        self.progress_tracker[status.get("id")].append({status.get("status"): status.get("progressDetail")})
        
        status_types = dict()
        self.identities = list()
        transfer_progress = dict()
        transfer_totals = dict()
        for idn, progressDetail in self.progress_tracker.items():
            latest = len(progressDetail) - 1
            self.identities.append(idn)
            if transfer_progress.get(idn) == None:
                transfer_progress[idn] = dict()   
                transfer_totals[idn] = dict()        
            if len(progressDetail) > 1:
                progress_status = list(progressDetail[latest-1].keys())[0]
                status_types[progress_status] = None
                if progressDetail[latest] != {}:
#                    if progressDetail[latest].get("Preparing") != None:
#                        transfer_progress[idn] = {'status': progress_status, 'detail': progressDetail[latest].get(progress_status)}
#                    elif progressDetail[latest].get("Waiting") != None:
#                        transfer_progress[idn] = {'status': progress_status, 'detail': progressDetail[latest].get(progress_status)}
#                    elif progressDetail[latest].get("Layer already exists") != None:
#                        transfer_progress[idn] = {'status': progress_status, 'detail': progressDetail[latest].get(progress_status)}
                    if progressDetail[latest].get("Pushing") != None:
                        transfer_progress[idn] = {'status': progress_status, 'detail': progressDetail[latest].get(progress_status)}
                        if progressDetail[latest].get(progress_status) != None:
                            transfer_totals[idn] = {idn: progressDetail[latest].get(progress_status).get("total")}
#                    elif progressDetail[latest].get("Pushed") != None:
#                        transfer_progress[idn] = {'status': progress_status, 'detail': progressDetail[latest].get(progress_status)}
#                    else:
#                        self.logger.info(f" {idn} - Unknown status")

        self.num_trackers.append(len(transfer_totals))
        self.num_identities.append(len(self.identities))

        t_trak = 0
        total_trackers = int()
        num_pbars = int()
        for t in self.num_trackers:
            if t > t_trak:
                t_trak = t
            elif t == t_trak:
                total_trackers = t_trak

        t_iden = 0
        l_num_iden = len(self.num_identities)
        total_identities = int()
        for t in self.num_identities:

            if t > t_iden:
                t_iden = t
            elif t == t_iden:
                total_identities = t_trak

        if "Pushing" in list(status_types.keys()):
            pushing = True
        else:
            pushing = False
            
        if pushing:
            for idnt in self.identities:
                status = transfer_progress.get(idnt).get("status")
                detail = transfer_progress.get(idnt).get("detail")
                epoch = int(time())
                max_time = 3600
                transfer_diff = int()
#                if status in ["Preparing", "Waiting", "Layer already exists", "Pushed"]:
#                    if not self.time_tracker.get(idnt):
#                        self.time_tracker[idnt] = [epoch]
#                    else:
#                        self.time_tracker[idnt].append(epoch)
#                        epoch_position = len(self.time_tracker[idnt]) - 1
#                        epoch_latest = self.time_tracker[idnt][epoch_position]
#                        epoch_previous = self.time_tracker[idnt][epoch_position - 1]
#                        epoch_diff = epoch_latest - epoch_previous
#                    if not self.pbar.get(idnt):
#                        if status == "Preparing":
#                            self.pbar[idnt] = trange(max_time, bar_format='{desc}')
#                        elif status == "Waiting":
#                            self.pbar[idnt] = trange(max_time, bar_format='{desc}')
#                        elif status == "Layer already exists":
#                            self.pbar[idnt] = trange(max_time, bar_format='{desc}')     
#                        elif status == "Pushed":
#                            self.pbar[idnt] = trange(max_time, bar_format='{desc}')               
#                        else:
#                            self.pbar[idnt] = trange(1)
#                    else:
#                       self.pbar[idnt].set_description(f"{idnt}: {status}")
#                       self.pbar[idnt].update(epoch_diff)
                if status == "Pushing":
                    if not transfer_progress.get(idnt).get("detail") == None:
                        if not transfer_progress.get(idnt).get("detail").get("total") == None:
                            #total = convert_bytes(transfer_progress.get(idnt).get("detail").get("total"))
                            #transfer = convert_bytes(transfer_progress.get(idnt).get("detail").get("current"))
                            total = transfer_progress.get(idnt).get("detail").get("total")
                            transfer = transfer_progress.get(idnt).get("detail").get("current")
                        else:
                            total = 0
                            transfer = 0
                    else:
                        total = 0
                        transfer = 0
                    if not self.transfer_tracker.get(idnt):
                        self.transfer_tracker[idnt] = [0]
                    else:
                        self.transfer_tracker[idnt].append(transfer)
                        transfer_position = len(self.transfer_tracker[idnt]) - 1
                        transfer_latest = self.transfer_tracker[idnt][transfer_position]
                        transfer_previous = self.transfer_tracker[idnt][transfer_position - 1]
                        #transfer_diff = convert_bytes(transfer_latest - transfer_previous)
                        transfer_diff = transfer_latest - transfer_previous
                    if not self.pbar.get(idnt):
    #                    self.logger.info(transfer_progress.get(idnt).get("detail"))
                        self.pbar[idnt] = trange(total, unit=" bytes", bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} bytes [{elapsed}<{remaining}, {rate_fmt}]')
                    else:
                        if transfer >= total:
                            self.pbar[idnt].close()
                        elif transfer < total:
                            self.pbar[idnt].set_description(f"{idnt}: {status}")
                            self.pbar[idnt].update(transfer_diff)
        self.tracker.append(progress)

    def set_image(self, name):
        self.image = name


class Operations(Logging):
    def __init__(self):
        Logging.__init__(self)
        self.config_path = os.path.normpath(self.arg.config)
        ### Set parent working directory
        self.build_dir =  os.path.join(self.work_dir, "build")
#        logger.debug(f"setting ownership of '{build_dir}' to '{user}:{group}'")
        self.parent_dir = os.path.dirname(self.work_dir)
        self.configs = self.load_config()
        self.project_build_dir = os.path.join(self.build_dir, os.path.basename(self.configs.get("info").get("name")))
        # Create build directory
        if self.arg.dryrun:
            self.logger.info(f"Dry run: creating build directories: '{self.project_build_dir}'")
        elif not self.arg.dryrun:
            self.logger.info(f"creating build directory: '{self.project_build_dir}'")
            self.recursive_make_dir(self.project_build_dir)
        # Setup filesystem logging
        self.log_file = os.path.join(self.project_build_dir, 'build.log')
        if not self.arg.dryrun:
            self.save_logs(self.log_file)

    def load_config(self):
        if self.valid_file(self.config_path, logger=True):
            #Try
            schema = yamale.make_schema(os.path.join(self.work_dir, 'schema.yaml'))
            data = yamale.make_data(self.config_path)
            valid_config = self.yaml_valid(schema, data)
            # Load config as yaml object
            if valid_config:
                self.logger.info(f"Loading config file: '{self.config_path}'")
                try:
                    with open(self.config_path, "r") as f:
                        loaded_config = yaml.load(f, Loader=yaml.FullLoader)
                except PermissionError:
                    self.logger.error(f"permission denied: '{self.config_path}'")
                    return
                except:
                    self.logger.error(f"failed to copy: '{self.config_path}'")
                    return 
            else:
                logger.error(f"Invalid config file: '{self.config_path}'")
        else:
            logger.debug("No yaml config files available to load")
            sys.exit()
        return loaded_config

    def copy_file(self, source, target, check=True):
        success = False
        if self.valid_file(source):
            try:
                shutil.copy2(source, target)
            except PermissionError:
                self.logger.error(f"permission denied: '{source}'")
                return
            except:
                self.logger.error(f"failed to copy: '{source}'")
                return
            if check:
                st = os.stat(source)
                if self.is_hash_same(self.get_file_hash(source), self.get_file_hash(target), logger=True):
                    success = True
                    self.logger.debug("copied '{s}' to '{t}' with hash '{h}'".format(s=source, t=target, h=self.get_file_hash(source)))
                else:
                    self.logger.error(f"error copying up: '{source}'")
        return success

    def copy_dir(self, source, target):
        success = False
        if self.valid_dir(source):
            #for dirpath, dirnames, filenames in os.walk(source):
            #    for f in filenames:
            #        src_file = os.path.join(dirpath, src_file)
            #        dst_file = os.path.join(dirpath, src_file)
            #        # Don't set permissions on symlinks
            #        if not os.path.islink(src_file):
            #                copy_file(src_file, dst_file)            
            try:
                shutil.copytree(source, target)
            except PermissionError:
                self.logger.error(f"permission denied: '{source}'")
                return
            except:
                self.logger.error(f"failed to copy: '{source}'")
                return
            st = os.stat(source)
            if self.is_hash_same(self.get_file_hash(source), self.get_file_hash(target), logger=True):
                success = True
                self.logger.debug(" '{s}' saved at '{t}' with hash '{h}'".format(s=source, t=target, h=self.get_file_hash(source)))
            else:
                self.logger.error(f"error backing up: '{source}'")
        return success

    def get_file_hash(self, path, algo="blake"):
        if self.valid_file(path):
            try:
                with open(path, "rb") as f:
                    if algo == "blake":
                        file_hash = hashlib.blake2b()
                    elif algo == "md5":
                        file_hash = hashlib.md5()
                    chunk = f.read(8192)
                    while chunk:
                        file_hash.update(chunk)
                        chunk = f.read(8192)
            except PermissionError:
                self.logger.error(f"permission denied: '{path}'")
                return
            except:
                self.logger.error(f"failed to copy: '{path}'")
                return
            file_hash_digest = file_hash.hexdigest()
            return file_hash_digest

    def is_hash_same(self, source_hash, target_file_hash, logger=False):
        if source_hash == target_file_hash:
            self.logger.debug(f"hash match: '{source_hash}'")
            return True
        else:
            if logger: self.logger.warning(f"hash '{source_hash}' does not match '{target_file_hash}'")

    def convert_bytes(self, bytes_number):
        tags = [ "Byte", "Kilobyte", "Megabyte", "Gigabyte", "Terabyte" ]
    
        i = 0
        double_bytes = bytes_number
    
        while (i < len(tags) and  bytes_number >= 1024):
                double_bytes = bytes_number / 1024.0
                i = i + 1
                bytes_number = bytes_number / 1024
    
        #return str(round(double_bytes, 2)) + " " + tags[i]
        return int(round(double_bytes, 1))

    def touch(self, path):
        def _fullpath(path):
            return os.path.abspath(os.path.expanduser(path))
        def _mkdir(path):
            if path.find("/") > 0 and not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
        def _utime(path):
            try:
                os.utime(path, None)
            except Exception:
                open(path, 'a').close()
        path = _fullpath(path)
        _mkdir(path)
        _utime(path)

    def chown(self, path, user, group):
        shutil.chown(path, user, group)

    def chmod(self, path, mode):
        os.chmod(path, int(mode, base=8))

    def recursive_chown(self, path, user, group):
        for dirpath, dirnames, filenames in os.walk(path):
            chown(dirpath, user, group)
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                # Don't set permissions on symlinks
                if not os.path.islink(file_path):
                        chown(file_path, user, group)

    def recursive_chmod(self, path, mode):
        for dirpath, dirnames, filenames in os.walk(path):
            chmod(dirpath, mode)
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                # Don't set permissions on symlinks
                if not os.path.islink(file_path):
                        chmod(file_path, mode)

    def recursive_make_dir(self, path):
        def make_forward(dest):
            parent_dir = os.path.dirname(dest)
            if os.path.exists(parent_dir):
                # Get parent mode and permissions
                stat_info = os.stat(parent_dir)
                uid = stat_info.st_uid
                gid = stat_info.st_gid
                mask = str(oct(stat_info.st_mode)[-3:])
                user = pwd.getpwuid(uid)[0]
                group = grp.getgrgid(gid)[0]
                # create dir and set permissions and mask
                self.logger.debug(f"creating: '{dest}' set to: '{user}:{group}:{mask}'")
                os.mkdir(dest)
                chown(dest, user, group)
                chmod(dest, mask)
            else:
                self.logger.error(f"parent directory does not exist! '{parent_dir}'")

        #@TODO: replace with PurePath.parts
        path_elements = path.split(os.path.sep)
        sep = os.path.sep
        if path_elements[0] == "..":
            root = ".."
        elif path_elements[0] == "/" :
            root = "/"
        elif path_elements[0] == "" :
            root = "/"
        elif path_elements[0] == os.path.sep:
            root = os.path.sep
        else:
            self.logger.error(f"Unknown base seperator! '{path_elements[0]}'")
            sys.exit()
        count = 0
        last_path = root
        for e in path_elements:
            path = os.path.join(last_path, e)
            if e == ".." and count == 0:
                path = root
            else:
                path = path
            last_path = path
            exists = os.path.exists(path)
            count+=1
            if not exists:
                make_forward(path)

    def copy_path(self, src, dst, overwrite=False):
        def cp_dir(src, dst, user, group, mask):
                self.copy_dir(src, dst)
                self.recursive_chown(dst, user, group)     
                self.recursive_chmod(dst, mask)
                # also change root dir
                self.chown(dst, user, group)
                self.chmod(dst, mask)
        def cp_file(src, dst, user, group, mask):
                self.copy_file(src, dst)
                self.chown(dst, user, group)
                self.chmod(dst, mask)
        def copy_check(src, dst, overwrite, user, group, mask):
            if os.path.isdir(src):
                if os.path.exists(dst):
                    if overwrite:
                        self.logger.warning(f"removing directory and copying new: '{src}' --> '{dst}'")
                        shutil.rmtree(dst)
                        cp_dir(src, dst, user, group, mask)
                    else:
                        self.logger.warning(f"directory exists! skipping copy: '{dst}'")                                    
                elif not os.path.exists(dst):
                    self.logger.debug(f"copying: '{src}' --> '{dst}'")
                    cp_dir(src, dst, user, group, mask)      
            elif os.path.isfile(src):
                if os.path.exists(dst):
                    if overwrite:
                        self.logger.warning(f"removing file and copying new: '{src}' --> '{dst}'")
                        os.remove(dst)
                        cp_file(src, dst, user, group, mask)
                    else:
                        self.logger.warning(f"file exists! skipping copy: '{dst}'")
                elif not os.path.exists(dst):
                    self.logger.debug(f"copying: '{src}' --> '{dst}'")
                    cp_file(src, dst, user, group, mask)                      
            else:
                self.logger.error(f"unknown path type: '{src}'")

        if os.path.exists(src):
            # Get permissions
            stat_info = os.stat(src)
            uid = stat_info.st_uid
            gid = stat_info.st_gid
            mask = str(oct(stat_info.st_mode)[-3:])
            user = pwd.getpwuid(uid)[0]
            group = grp.getgrgid(gid)[0]

            dst_parent_dir = os.path.dirname(dst)
            if os.path.exists(dst_parent_dir):
                copy_check(src, dst, overwrite, user, group, mask)
            elif not os.path.exists(dst_parent_dir):
                recursive_make_dir(dst_parent_dir)
                copy_check(src, dst, overwrite, user, group, mask)
        else:
            self.logger.error(f"source path does not exist! '{src}', exiting")
            sys.exit()

    def yaml_valid(self, schema, data):
        try:
            yamale.validate(schema, data)
            return True
        except yamale.YamaleError as e:
            self.logger.error('YAML Validation failed!\n%s' % str(e))
            return False

class Docker(Operations):
    def __init__(self):
        import docker
        Operations.__init__(self)
        #clients = docker.from_env()
        self.cli = docker.APIClient(base_url='unix://var/run/docker.sock')
        self.logger.debug(self.cli.version())
        self.errors = docker.errors
        self.color_logs()

    def process_stream(self, line):
        ln = json.loads(line.decode("utf-8").rstrip()).get("stream")
        if ln != None and not ln.isspace():
            ln = ln.rstrip()
            items = ln.split()
            msg = [i for i in items[1:]]
            if items[0] == "\x1b[91mE:": # Look for apt errors "E:", formated with red colorcode
                if self.arg.rm_inter_imgs:
                    try:
                        inter_image = self.cli.inspect_container(self.intermediate_container).get("Image")
                        self.logger.warning(f"removing image: {inter_image}")
                        self.cli.remove_container(self.intermediate_container, force=True)
                        self.cli.remove_image(inter_image, force=True)
                    except self.errors.APIError as err:
                        raise BuildError(f"Builder: remove error - {err}")

                raise BuildError("Builder: apt error - {m}".format(m=" ".join(msg)))
            elif items[0] == "Step": # Look for build steps
                self.logger.info("Builder: Step {m}".format(m=" ".join(msg)))
            elif items[0] == "--->": # Look for build progression info
                if items[1] == "Running" and items[2] == "in":
                    self.intermediate_container = items[3]
                self.logger.info("Builder: {m}".format(m=" ".join(msg)))
            elif items[0] == "Successfully": # Look for success info
                self.logger.info("Builder: Successfully {m}".format(m=" ".join(msg)))
            elif items[0] == "Fetched": # Look for fetch info
                self.logger.info("Builder: Fetched {m}".format(m=" ".join(msg)))
            elif items[0] == "Reading": # Look for reading info
                self.logger.info("Builder: Reading {m}".format(m=" ".join(msg)))
            elif items[0] == "Building": # Look for reading info
                self.logger.info("Builder: Building {m}".format(m=" ".join(msg)))         
            elif len(items[0].split(":")) == 2: # Look for download progression info
                get = items[0].split(":")[0]
                get_idx = items[0].split(":")[1]
                if get == "Get":
                    self.logger.info("Builder: Get({i}) {m}".format(i=get_idx, m=" ".join(msg)))
            else:
                self.logger.debug(ln)

    def exclude_paths(self, root, patterns, dockerfile=None):
        """
        Given a root directory path and a list of .dockerignore patterns, return
        an iterator of all paths (both regular files and directories) in the root
        directory that do *not* match any of the patterns.
        All paths returned are relative to the root.
        """

        if dockerfile is None:
            dockerfile = 'Dockerfile'

        patterns.append('!' + dockerfile)
        pm = PatternMatcher(patterns)
        return set(pm.walk(root))

    def process_dockerfile(self, dockerfile, path):
        if not dockerfile:
            return (None, None)

        abs_dockerfile = dockerfile
        if not os.path.isabs(dockerfile):
            abs_dockerfile = os.path.join(path, dockerfile)
            if constants.IS_WINDOWS_PLATFORM and path.startswith(
                    constants.WINDOWS_LONGPATH_PREFIX):
                abs_dockerfile = '{}{}'.format(
                    constants.WINDOWS_LONGPATH_PREFIX,
                    os.path.normpath(
                        abs_dockerfile[len(constants.WINDOWS_LONGPATH_PREFIX):]
                    )
                )
        if (os.path.splitdrive(path)[0] != os.path.splitdrive(abs_dockerfile)[0] or
                os.path.relpath(abs_dockerfile, path).startswith('..')):
            # Dockerfile not in context - read data to insert into tar later
            with open(abs_dockerfile, 'r') as df:
                return (
                    '.dockerfile.{0:x}'.format(random.getrandbits(160)),
                    df.read()
                )

        # Dockerfile is inside the context - return path relative to context root
        if dockerfile == abs_dockerfile:
            # Only calculate relpath if necessary to avoid errors
            # on Windows client -> Linux Docker
            # see https://github.com/docker/compose/issues/5969
            dockerfile = os.path.relpath(abs_dockerfile, path)
        return (dockerfile, None)

    def makebuildcontext(self, path, fileobj, dockerfile, exclude=None, gzip=None):
        root = os.path.abspath(path)
        exclude = exclude or []
        dockerfile = dockerfile or (None, None)
        extra_files = []
        if dockerfile[1] is not None:
            dockerignore_contents = '\n'.join(
                (exclude or ['.dockerignore']) + [dockerfile[0]]
            )
            extra_files = [
                ('.dockerignore', dockerignore_contents),
                dockerfile,
            ]

        files=sorted(self.exclude_paths(root, exclude, dockerfile=dockerfile[0]))
        extra_files = extra_files or []
        extra_names = set(e[0] for e in extra_files)

        f = tempfile.NamedTemporaryFile()
        t = tarfile.open(mode='w:gz' if gzip else 'w', fileobj=f)

        for path in files:
            self.logger.debug(f"adding to context: '{path}'")
            if path in extra_names:
                # Extra files override context files with the same name
                continue
            full_path = os.path.join(root, path)

            i = t.gettarinfo(full_path, arcname=path)

            if i is None:
                # This happens when we encounter a socket file. We can safely
                # ignore it and proceed.
                continue

            # Workaround https://bugs.python.org/issue32713
            if i.mtime < 0 or i.mtime > 8**11 - 1:
                i.mtime = int(i.mtime)

            if IS_WINDOWS_PLATFORM:
                # Windows doesn't keep track of the execute bit, so we make files
                # and directories executable by default.
                i.mode = i.mode & 0o755 | 0o111

            if i.isfile():
                try:
                    with open(full_path, 'rb') as fl:
                        t.addfile(i, fl)
                except IOError:
                    raise IOError(
                        'Can not read file in context: {}'.format(full_path)
                    )
            else:
                # Directories, FIFOs, symlinks... don't need to be read.
                t.addfile(i, None)

        for name, contents in extra_files:
            info = tarfile.TarInfo(name)
            contents_encoded = contents.encode('utf-8')
            info.size = len(contents_encoded)
            t.addfile(info, io.BytesIO(contents_encoded))
    
        dfinfo = tarfile.TarInfo('Dockerfile')
        dfinfo.size = len(fileobj.getvalue())
        t.addfile(dfinfo, fileobj)
        
        t.close()
        f.seek(0)
        
        return f

    def build(self):
        pushstat = PushStatus()
        
        self.logger.info("Starting docker builder")
        
        if self.arg.gzip: self.logger.info(f"gzip file compression enabled")

        # Get permissions
        stat_info = os.stat(self.work_dir)
        uid = stat_info.st_uid
        gid = stat_info.st_gid
        mask = str(oct(stat_info.st_mode)[-3:])
        user = pwd.getpwuid(uid)[0]
        group = grp.getgrgid(gid)[0]

        # Set main repository
        main_repository = self.arg.repository if self.arg.repository else self.configs.get("info").get("repository")

        # Define project
        base_image = self.configs.get("build").get("base")
        projects = self.configs.get("build").get("projects")

        ### Process Dockerfiles
        dockerfile_final = list()
        project_files = list()
        image_count = 0
        for p in projects:

            ### Store a list of Dockerfiles to process
            dockerfiles = list()
            for df in p.get("dockerfiles"):
                dockerfiles.append(df.get("file"))

            ### Scan project directories
            project_dir = os.path.join(self.parent_dir, p.get("directory"))
            
            if os.path.exists(project_dir):
                self.logger.info(f"processing dockerfiles in: '{project_dir}")

                total_images = len(p.get("dockerfiles"))
                for image in p.get("dockerfiles"):
                    dockerfile_path = os.path.join(project_dir, image.get("file"))
                    # Get Dockerfile properties
                    image_repository = main_repository if main_repository else image.get("repository")
                    image_name = image.get("name")
                    image_tag = image.get("tag") if image.get("tag") else "latest"
                    image_push = True if self.arg.push or image.get("push").lower() == "true" else False

                    # Set image Docker path
                    image_docker_path = f"{image_repository}/{image_name}:{image_tag}"

                    if os.path.exists(dockerfile_path):
                        self.logger.info(f"Building image: '{image_tag}' from '{dockerfile_path}'")

                        ### Read dockerfile
                        df_lines = list()
                        with open(dockerfile_path) as f:
                            lines = f.readlines()

                        ### Set from image specified in config
                        dockerfile_from = image.get("from")
                        dockerfile_entrypoint = image.get("entrypoint")
                        dockerfile_cmd = str()
                        
                        ### Modify Dockerfile
                        copy_elements = list()
                        cont_count = 0
                        list_files = False
                        for l in lines:
                            # Get list of files formated as ["file1", "file2"]
                            if l.isspace():
                                continue
                            if l[0] == "#":
                                self.logger.debug(f"skipping commented line: {l}")
                                continue
                            copy_chars = list()
                            skip_line = False
                            items = l.split()
                            
                            copy_count = 0
                            num_items = len(items)
                            element = list()
                            if items[0] == "COPY":
                                for c in l:
                                    if c == '[':
                                        list_files = True
                                        skip_line = True
                                    elif c == '"' or c == ' ':
                                        continue
                                    elif c == ']':
                                        list_files = False
                                    elif list_files:
                                        if c == ',':
                                            copy_elements.append("".join(element))
                                            element = list()
                                        else:
                                            element.append(c)
                            # Get list of files seperated by spaces and spanning lines
                            if not skip_line:
                                for w in items:
                                    if cont_count > 0:
                                        if not w == "\\": 
                                            copy_elements.append(w)
                                            cont_count+=1
                                        if items[num_items-1] == "\\":
                                            continue
                                        else:
                                            copy_elements.pop()
                                            cont_count = 0                              
                                    if w == "COPY":
                                        copy_length = range(num_items)
                                        # Add every element except first and last to copy list
                                        for e in copy_length:
                                            if items[e] == "\\":
                                                cont_count+=1                            
                                            if copy_count == (num_items-2):
                                                continue
                                            else:
                                                copy_elements.append(items[e+1])
                                                copy_count+=1
                                                cont_count = 0
                                    if w == "FROM":
                                        if image_count == 0:
                                            self.logger.debug(f"Base image: '{dockerfile_from}'")
                                            dockerfile_final.append(f"FROM {dockerfile_from} \n")
                                            df_lines.append(f"FROM {dockerfile_from} \n")
                                        else:
                                            df_lines.append(f"FROM {dockerfile_from} \n")
                                        skip_line = True
                                        continue
                                    if w == "ENTRYPOINT":
                                        if image_count == total_images:
                                            self.logger.debug(f"Image entrypoint: '{l.rstrip()}'")
                                            dockerfile_entrypoint = l.rstrip()
                                            dockerfile_final.append(f"{dockerfile_entrypoint} \n")
                                            df_lines.append(f"{dockerfile_entrypoint} \n")
                                        skip_line = True
                                        continue
                                    if w == "CMD":
                                        if image_count == total_images:
                                            self.logger.debug(f"Image command: '{l.rstrip()}'")
                                            dockerfile_cmd = l.rstrip()
                                            dockerfile_final.append(f"{dockerfile_cmd} \n")
                                            df_lines.append(f"{dockerfile_cmd} \n")
                                        skip_line = True
                                        continue
                                if skip_line:
                                    continue
                                else:
                                    df_lines.append(l.rstrip())
                                    dockerfile_final.append(l.rstrip())
                        
                        # copy image files
                        for e in copy_elements:
                            src = os.path.join(project_dir, e)
                            dst = os.path.join(self.project_build_dir, e)
                            if self.arg.dryrun:
                                self.logger.debug(f"Dry run: copying: '{src}' --> '{dst}'")
                            elif not self.arg.dryrun:
                                self.copy_path(src, dst, self.arg.overwrite)
                            project_files.append(dst)
                        
                        # Track log file and project build directory
                        project_files.append(self.log_file)
                        project_files.append(self.project_build_dir)

                        image_count+=1

                        if dockerfile_entrypoint:
                            self.logger.debug(f"Final Entrypoint: '{dockerfile_entrypoint}'")
                            dockerfile_final.append(f"ENTRYPOINT {dockerfile_entrypoint} \n")
                            df_lines.append(f"ENTRYPOINT {dockerfile_entrypoint} \n")

                        s = '\n'
                        dockerfile_mod = s.join(df_lines)
                        
                        count = 0
                        dockerfile_mod_debug = list()
                        for l in df_lines:
                            dockerfile_mod_debug.append(f"{str(count).ljust(5)} {l}")
                            count+=1

                        dockerfile_mod_debug = s.join(dockerfile_mod_debug)
                        self.logger.debug(dockerfile_mod_debug)
            
                        # Encode before building
                        dockerfile_encoded = io.BytesIO(dockerfile_mod.encode('utf-8'))

                        # Read dockerignore for files to exclude
                        docker_ignore = os.path.join(project_dir, '.dockerignore')
                        docker_exclude = None
                        if os.path.exists(docker_ignore):
                            with open(docker_ignore, 'r') as f:
                                docker_exclude = list(filter(
                                    lambda x: x != '' and x[0] != '#',
                                    [l.strip() for l in f.read().splitlines()]
                                ))

                        dockerfile_processed = self.process_dockerfile(dockerfile_path, project_dir)
                        
                        encoding = None
                        encoding = 'gzip' if self.arg.gzip else encoding
                    
                        dockerfile_obj = self.makebuildcontext(project_dir, dockerfile_encoded, dockerfile_processed, docker_exclude, self.arg.gzip)     

                        if not self.arg.dryrun:
                            try:
                                [self.process_stream(line) for line in self.cli.build(
                                    fileobj=dockerfile_obj, 
                                    rm=True, 
                                    tag=image_docker_path, 
                                    custom_context=True,
                                )]
                            except self.errors.APIError   as a_err:
                                self.logger.error(f"Docker API error: {a_err}")
                                sys.exit()
                            except self.errors.BuildError as b_err:
                                self.logger.error(f"Docker Build error: {b_err}")
                                sys.exit()
                            except BuildError as b_err:
                                self.logger.error(f"{b_err}")
                                sys.exit()
                            except TypeError as t_err:
                                self.logger.error(f"error: {t_err}")
                                sys.exit()                  
                            except:
                                self.logger.error("unknown error")
                                sys.exit()
                            #if save:
                            #    f = open('/tmp/busybox-latest.tar', 'wb')
                            #    for chunk in image:
                            #        f.write(chunk)
                            #    f.close()
                            if image_push:
                                self.logger.info(f"Pushing: '{image_docker_path}'")
                                pushstat.set_image(image_docker_path)
                                [pushstat.store(line) for line in self.cli.push(
                                    image_docker_path, stream=True, decode=True
                                )]

                    else:
                        self.logger.error(f"Dockerfile does not exists: '{dockerfile_path}")
                        sys.exit()
            else:
                self.logger.error(f"Project dir does not exists: '{project_dir}")
                sys.exit()

        project_files.append(self.build_dir)
                
        s = '\n'
        dockerfile_final = s.join(dockerfile_final)
        self.logger.debug("Final dockerfile")
        self.logger.debug(dockerfile_final)

        ### Write final Dockerfile
        dockerfile_final_path = os.path.join(self.project_build_dir, "Dockerfile")
        if self.arg.dryrun:
            self.logger.info(f"Dry run: Writing final Dockerfile to: '{dockerfile_final_path}")
        if not self.arg.dryrun:
            self.logger.info(f"Writing final Dockerfile to: '{dockerfile_final_path}")
            with open(dockerfile_final_path, "w") as f: 
                f.write(dockerfile_final)
            # Track Dockerfile
            project_files.append(dockerfile_final_path)
            # Fix Dockerfile permissions
            self.chown(dockerfile_final_path, user, group)
            self.chmod(dockerfile_final_path, "664")
            # Fix log file permissions
            self.chown(self.log_file, user, group)
            self.chmod(self.log_file, "664")

            ### Remove residual project files
            if rm_build_files:
                for p in project_files:
                    if os.path.exists(p):
                        self.logger.info(f"removing: '{p}'")
                        if os.path.isdir(p):
                            try:
                                shutil.rmtree(p)
                            except OSError as err:
                                self.logger.error(f"error: {err}")
                        elif os.path.isfile(p):
                            os.remove(p)

def main():
    ### Start builder
    docker = Docker()
    docker.build()

if __name__ == '__main__':
    setup = Setup()
    setup.install([
        'coloredlogs>=15.0', 
        'ruyaml>=0.20.0'
        'bcrypt>=3.2.0',
        'passlib>=1.7.4',
        'tqdm>=4.59.0',
        'yamale>=3.0.4',
        'PyYAML>=5.4.1',
    ])

    import yaml
    import yamale
    import coloredlogs
    from ruyaml import YAML
    from passlib.hash import bcrypt
    from tqdm import tqdm, trange

    main()