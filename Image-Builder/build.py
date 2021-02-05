
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
import yaml
import yamale
import json
import docker
import argparse
import logging
import shutil
import tarfile
import tempfile
from urllib.parse import quote, urljoin
from subprocess   import run, call

### Set constants
IS_WINDOWS_PLATFORM = (sys.platform == 'win32')
_SEP = re.compile('/|\\\\') if IS_WINDOWS_PLATFORM else re.compile('/')
_cache = {}
_MAXCACHE = 100

### Define classes
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

### Define functions
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

def yaml_valid(schema, data, level):
    log.setLevel(level)
    try:
        yamale.validate(schema, data)
        return True
    except yamale.YamaleError as e:
        log.error('YAML Validation failed!\n%s' % str(e))
        return False

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

def exclude_paths(root, patterns, dockerfile=None):
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


def decode_stream(line):
    ### Set clean logging
#    logging.basicConfig(
#        format='', 
#        level=logging.INFO, 
#        stream=sys.stdout)
#    logger = logging.getLogger(__name__)
#    logger.setLevel("INFO")

    clean_line = json.loads(line.decode("utf-8").rstrip()).get("stream")
    if clean_line != None and not clean_line.isspace():
#        logger.info(clean_line.rstrip())
        log.debug(clean_line.rstrip())

def process_dockerfile(dockerfile, path):
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

def makebuildcontext(path, fileobj, dockerfile, exclude=None, gzip=None):
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

    files=sorted(exclude_paths(root, exclude, dockerfile=dockerfile[0]))
    extra_files = extra_files or []
    extra_names = set(e[0] for e in extra_files)

    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w:gz' if gzip else 'w', fileobj=f)

    for path in files:
        log.debug(f"adding to context: '{path}'")
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

def main(opts, log_level, config, dryrun, gzip):
    ### Enable docker API
    clients = docker.from_env()
    cli = docker.APIClient(base_url='unix://var/run/docker.sock')
    log.debug(cli.version())

    if gzip: log.info(f"gzip file compression enabled")

    ### Load arguments
    verbosity = log_level.upper()
    config_path = os.path.normpath(config)
 
    ### Set parent working directory
    work_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(work_dir)

    # Get permissions
    stat_info = os.stat(work_dir)
    uid = stat_info.st_uid
    gid = stat_info.st_gid
    user = pwd.getpwuid(uid)[0]
    group = grp.getgrgid(gid)[0]

    ### Parse config file
    if os.path.exists(config_path):
        # Validate file
        schema = yamale.make_schema(os.path.join(work_dir, 'schema.yaml'))
        data = yamale.make_data(config_path)
        valid_config = yaml_valid(schema, data, verbosity)
        # Load config as yaml object
        if valid_config:
            log.info(f"Loading config file: '{config_path}'")
            with open(config_path, "r") as f:
                configs = yaml.load(f, Loader=yaml.FullLoader)
        else:
            log.error(f"Invalid config file: '{config_path}'")
    else:
        log.debug("No yaml config files available to load")
        sys.exit()

    ### Set relative paths
    build_dir =  os.path.join(work_dir, "build")
    log.debug(f"setting ownership of '{build_dir}' to '{user}:{group}'")
    recursive_chown(build_dir, user, group)

    project_build_dir = os.path.join(build_dir, os.path.basename(configs.get("info").get("name")))
    if os.path.exists(project_build_dir):
        log.warning(f"removing previous build directory: '{project_build_dir}'")
        shutil.rmtree(project_build_dir)
    else:
        log.warning(f"creating build directory: '{project_build_dir}'")
        os.makedirs(project_build_dir)
        log.debug(f"setting ownership of '{project_build_dir}' to '{user}:{group}'")
        recursive_chown(project_build_dir, user, group)

    log_file = os.path.join(project_build_dir, 'build.log')

    base_image = configs.get("build").get("base")
    projects = configs.get("build").get("projects")

    dockerfile_final = list()
    ### Execute Dockerfiles
    image_count = 0
    for p in projects:
        name = p.get("name")
        repository = p.get("repository")
        tag = p.get("tag")

        dockerfiles = list()
        for df in p.get("dockerfiles"):
            dockerfiles.append(df.get("file"))

        # Set full name
        docker_path = f"{repository}/{name}:{tag}"

        # Scan project directories
        project_dir = os.path.join(parent_dir, p.get("directory"))
           
        if os.path.exists(project_dir):
            log.info(f"processing dockerfiles in: '{project_dir}")

            total_images = len(p.get("dockerfiles"))
            for image in p.get("dockerfiles"):
                dockerfile_path = os.path.join(project_dir, image.get("file"))
                image_tag = image.get("tag")

                if os.path.exists(dockerfile_path):
                    log.info(f"Building image: '{image_tag}' from '{dockerfile_path}'")
                    project_files = ["scripts", "files", "configs"]
                    for d in project_files:
                        src = os.path.join(project_dir, d)
                        dst = os.path.join(project_build_dir, d)
                        if os.path.exists(src):
                            log.info(f"Copying build files to root dir: '{d}'")
                            # Copy dockerfile "COPY" files
                            if os.path.exists(dst): 
                                shutil.rmtree(dst)
                                shutil.copytree(src, dst)
                                log.debug(f"setting ownership of '{dst}' to '{user}:{group}'")
                                chown(dst, user, group)
                                recursive_chown(dst, user, group)
                            else:
                                shutil.copytree(src, dst)
                                log.debug(f"setting ownership of '{dst}' to '{user}:{group}'")
                                chown(dst, user, group)
                                recursive_chown(dst, user, group)

                    # Read dockerfile
                    df_lines = list()
                    with open(dockerfile_path) as f:
                        lines = f.readlines()

                    # Set from image specified in config
                    dockerfile_from = image.get("from")
                    dockerfile_entrypoint = str()
                    dockerfile_cmd = str()
                    
                    # Modify file
                    for l in lines:
                        skip_line = False
                        words = l.split()
                        for w in words:
                            if w == "FROM":
                                if image_count == 0:
                                    log.info(f"Base image: '{dockerfile_from}'")
                                    dockerfile_final.append(f"FROM {dockerfile_from} \n")
                                    df_lines.append(f"FROM {dockerfile_from} \n")
                                else:
                                    df_lines.append(f"FROM {dockerfile_from} \n")
                                skip_line = True
                                continue
                            if w == "ENTRYPOINT":
                                if image_count == total_images:
                                    log.info(f"Image entrypoint: '{l.rstrip()}'")
                                    dockerfile_entrypoint = l.rstrip()
                                    dockerfile_final.append(f"{dockerfile_entrypoint} \n")
                                    df_lines.append(f"{dockerfile_entrypoint} \n")
                                skip_line = True
                                continue
                            if w == "CMD":
                                if image_count == total_images:
                                    log.info(f"Image command: '{l.rstrip()}'")
                                    dockerfile_cmd = l.rstrip()
                                    dockerfile_final.append(f"CMD {dockerfile_cmd} \n")
                                    df_lines.append(f"{dockerfile_cmd} \n")
                                skip_line = True
                                continue
                        if skip_line:
                            continue
                        else:
                            df_lines.append(l.rstrip())
                            dockerfile_final.append(l.rstrip())

                    image_count+=1

                    s = '\n'
                    dockerfile_mod = s.join(df_lines)
                    log.debug(dockerfile_mod)
        
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

                    dockerfile_processed = process_dockerfile(dockerfile_path, project_dir)
                    
                    encoding = None
                    encoding = 'gzip' if gzip else encoding
                 
                    dockerfile_obj = makebuildcontext(project_dir, dockerfile_encoded, dockerfile_processed, docker_exclude, gzip)     

                    [decode_stream(line) for line in cli.build(
                        fileobj=dockerfile_obj, rm=True, tag=image_tag, custom_context=True
                    )]

#                     quiet (bool): Whether to return the status
#                     pull (bool): Downloads any updates to the FROM image in Dockerfiles
#                     buildargs (dict): A dictionary of build arguments
#                     container_limits (dict): A dictionary of limits applied to each
#                     labels (dict): A dictionary of labels to set on the image
#                     cache_from (:py:class:`list`): A list of images used for build cache resolution

    #                for d in project_files:
    #                    dst = os.path.join(project_build_dir, d)
    #                    if os.path.exists(dst):
    #                        log.info(f"removing build files in root dir: '{d}'")
    #                        shutil.rmtree(dst)

#                     container = clients.containers.get("pod2-colab")
#                     container_name = container.name
#                     log.info(container_name)

                else:
                    log.error(f"Dockerfile does not exists: '{dockerfile_path}")
        else:
            log.error(f"Project dir does not exists: '{project_dir}")
    s = '\n'
    dockerfile_final = s.join(dockerfile_final)
    log.debug("Final dockerfile")
    log.debug(dockerfile_final)

    ### Write final Dockerfile
    dockerfile_final_path = os.path.join(project_build_dir, "Dockerfile")
    log.info(f"Writing final Dockerfile to: '{dockerfile_final_path}")
    with open(dockerfile_final_path, "w") as f: 
        f.write(dockerfile_final)

if __name__ == '__main__':
    ### Enable argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('--opts', type=json.loads, help='Set script arguments')
    parser.add_argument('--log_level', choices=('debug', 'info', 'warning', 'error', 'critical'), default='info', const='info', nargs='?', required=False, help='Set script log level of verbosity')
    parser.add_argument('--config', type=str, default='default', required=True, help="Location of build YAML file")
    parser.add_argument('--dryrun', action='store_true', default=False, required=False, help='Execute as a dry run')
    parser.add_argument('--gzip', action='store_true', default=False, required=False, help='Compress context files')

    args, unknown = parser.parse_known_args()
    if unknown:
        log.error("Unknown arguments " + str(unknown))

    ### Enable logging
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s', 
        level=logging.INFO, 
        stream=sys.stdout)

    log = logging.getLogger(__name__)

    # Set log level
    log.setLevel(args.log_level.upper())
    
    log.info("Starting docker builder")

    main(**vars(args))