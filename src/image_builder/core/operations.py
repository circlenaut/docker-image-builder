import grp
import hashlib
import os
import pwd
import shutil
import sys
from abc import ABC
from pathlib import Path
from datetime import datetime

import yaml
import yamale

from ..configs import Settings
from ..helpers import InputOutput
from ..internal import (
    Logging,
    BuildError,
    LoadError
)

__all__ = ['Operations']


class Operations(ABC):
    def __init__(self):
        self.logger = Logging()
        self.io = InputOutput()
        self.settings = Settings()
        
        # Set directories
        self.config_path = Path(self.settings.args.config)
        self.etc_path = Path("/usr/local/etc/image-builder")
        self.default_images = Path("/opt/docker/Docker-Images")
        self.script_dir = Path(__file__).resolve().parent
        self.work_dir = Path.cwd().joinpath(self.config_path.parent) if not self.config_path.as_posix() == "" else Path.cwd()
        self.parent_dir = self.work_dir.parent
        # Load config
        try:
            self.configs = self._load_config()
        except LoadError as err:
            self.logger.error(f"'{err}'")
            sys.exit()     
        except BuildError as b_err:
            self.logger.error(f"'{b_err}'")
            sys.exit()
        self.build_dir = Path(self.configs.get("info").get("build_dir")) if self.configs.get("info").get("build_dir") else self.work_dir.joinpath("build")
        self.project_build_dir = self.build_dir.joinpath(Path(self.configs.get("info").get("name")))
        self.version_tags = self.configs.get("info").get("tags")
        
        # Get current for tagging
        now = datetime.now()
        self.now_tag = now.strftime("%Y-%m-%d_%H-%M%z")

        # Create build directory
        if self.settings.args.dryrun:
            self.logger.info(f"Dry run: creating build directories: '{self.project_build_dir.as_posix()}'")
        elif not self.settings.args.dryrun:
            self.logger.info(f"creating build directory: '{self.project_build_dir.as_posix()}'")
            self.recursive_make_dir(self.project_build_dir.as_posix())
        # Setup filesystem logging
        self.log_file = self.project_build_dir.joinpath('build.log')
        if not self.settings.args.dryrun:
            self.logger.save_logs(self.log_file.as_posix())

    def _load_config(self):
        if self.io.valid_file(self.config_path, logger=True):
            schema_paths = [
                self.script_dir.joinpath('..', 'configs', 'schema.yaml'),
                self.etc_path.joinpath('schema.yaml'),
            ]
            print(schema_paths)
            if any([self.io.valid_file(sp.as_posix()) for sp in schema_paths]):
                for sp in schema_paths:
                    if self.io.valid_file(sp.as_posix()):
                        schema_path = sp
                        self.logger.debug(f"using schema file found at: '{schema_path.as_posix()}'")
            else:
                raise BuildError("Builder Schema Error: schema file not found")
            try:
                schema = yamale.make_schema(schema_path.as_posix())
            except Exception as err:
                self.logger.error(f"failed to load: '{schema_path.as_posix()}'")
                raise LoadError(f"{err}") 
            try:
                data = yamale.make_data(self.config_path)
            except Exception as err:
                self.logger.error(f"failed to load: '{self.config_path}'")
                raise LoadError(f"{err}")            
            valid_config = self.yaml_valid(schema, data)
            # Load config as yaml object
            if valid_config:
                self.logger.info(f"Loading config file: '{self.config_path}'")
                try:
                    with open(self.config_path, "r") as f:
                        loaded_config = yaml.load(f, Loader=yaml.FullLoader)
                except PermissionError as perm:
                    self.logger.error(f"permission denied: '{self.config_path}'")
                    raise LoadError(f"{perm}")
                except Exception as err:
                    self.logger.error(f"failed to load: '{self.config_path}'")
                    raise LoadError(f"{err}")
                return loaded_config
            else:
                self.logger.error(f"Invalid config file: '{self.config_path}'")
                sys.exit()
        else:
            self.logger.debug("No yaml config files available to load")
            sys.exit()

    def copy_file(self, source, target, check=True):
        success = False
        if self.io.valid_file(source):
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
                if self.is_hash_same(self.get_file_hash(source), self.get_file_hash(target)):
                    success = True
                    self.logger.debug("copied '{s}' to '{t}' with hash '{h}'".format(s=source, t=target, h=self.get_file_hash(source)))
                else:
                    self.logger.error(f"error copying: '{source}'")
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
            except Exception as err:
                self.logger.error(f"failed to copy: '{source}'")
                self.logger.error(f"{err}")
                return
            st = os.stat(source)
            if self.is_hash_same(self.get_file_hash(source), self.get_file_hash(target)):
                success = True
                self.logger.debug(" '{s}' saved at '{t}' with hash '{h}'".format(s=source, t=target, h=self.get_file_hash(source)))
            else:
                self.logger.error(f"error copying: '{source}'")
        return success

    def get_file_hash(self, path, algo="blake"):
        if self.io.valid_file(path):
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
            except Exception as err:
                self.logger.error(f"{err}")
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
        units = [ "Byte", "Kilobyte", "Megabyte", "Gigabyte", "Terabyte" ]
    
        i = 0
        double_bytes = bytes_number
    
        while (i < len(units) and  bytes_number >= 1024):
                double_bytes = bytes_number / 1024.0
                i = i + 1
                bytes_number = bytes_number / 1024
    
        #return str(round(double_bytes, 2)) + " " + units[i]
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
            self.chown(dirpath, user, group)
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                # Don't set permissions on symlinks
                if not os.path.islink(file_path):
                        self.chown(file_path, user, group)

    def recursive_chmod(self, path, mode):
        for dirpath, dirnames, filenames in os.walk(path):
            self.chmod(dirpath, mode)
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                # Don't set permissions on symlinks
                if not os.path.islink(file_path):
                        self.chmod(file_path, mode)

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
                self.chown(dest, user, group)
                self.chmod(dest, mask)
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
            root = "./"
            #self.logger.error(f"Unknown base seperator! '{path_elements[0]}'")
            #sys.exit()
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
                raise OperationError(f"unknown path type: '{src}'")

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
                self.recursive_make_dir(dst_parent_dir)
                copy_check(src, dst, overwrite, user, group, mask)
        else:
            raise OperationError(f"source path does not exist! '{src}'")

    def yaml_valid(self, schema, data):
        try:
            yamale.validate(schema, data)
            return True
        except yamale.YamaleError as e:
            self.logger.error('YAML Validation failed!\n%s' % str(e))
            return False