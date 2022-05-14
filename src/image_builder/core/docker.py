import grp
import itertools
import io
import json
import os
import sys
import pwd
import tarfile
import tempfile
from abc import ABC
from time import time
from typing import List

import docker
from rich import box
from rich.live import Live
from rich.table import Table
from tqdm import trange

from ..configs import Constants, Settings
from ..helpers import InputOutput, PatternMatcher
from ..internal import (
    Logging,
    BuildError,
    OperationError
)
from .operations import Operations


__all__ = ['PushStatus', 'Docker']


class PushStatus(ABC):
    def __init__(self):
        self.logger = Logging()
        
        self.tracker = []
        self.layer = {}
        self.progress_tracker = {}
        self.num_trackers = []
        self.num_identities = []
        self.pbar = {}
        self.transfer_tracker = {}
        self.time_tracker = {}

    def store(self, progress):
        for status in self.tracker:
            if status.get("id") != None:
                self.layer[status.get("id")] = None
            for i in self.layer.keys():
                if i == status.get("id"):
                    if self.progress_tracker.get(status.get("id")) == None:
                        self.progress_tracker[status.get("id")] = []
                    else:
                        self.progress_tracker[status.get("id")].append({status.get("status"): status.get("progressDetail")})
        
        status_types = {}
        self.identities = []
        transfer_progress = {}
        transfer_totals = {}
        for idn, progressDetail in self.progress_tracker.items():
            #print(progressDetail)
            latest = len(progressDetail) - 1
            self.identities.append(idn)
            if transfer_progress.get(idn) == None:
                transfer_progress[idn] = {}   
                transfer_totals[idn] = {}        
            if len(progressDetail) > 1:
                progress_status = list(progressDetail[latest-1].keys())[0]
                status_types[progress_status] = None
                #print(status_types.keys())
                if progressDetail[latest] != {}:
                    #print(progressDetail[latest])
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
                    elif progressDetail[latest].get("Downloading") != None:
                        transfer_progress[idn] = {'status': progress_status, 'detail': progressDetail[latest].get(progress_status)}
                        #print(transfer_progress[idn])
                        if progressDetail[latest].get(progress_status) != None:
                            #print("true")
                            transfer_totals[idn] = {idn: progressDetail[latest].get(progress_status).get("total")}
                            #print(transfer_totals[idn])
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

        if "Downloading" in list(status_types.keys()):
            downloading = True
        else:
            downloading = False
            
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
                            #total = self.ops.convert_bytes(transfer_progress.get(idnt).get("detail").get("total"))
                            #transfer = self.ops.convert_bytes(transfer_progress.get(idnt).get("detail").get("current"))
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
                        #transfer_diff = self.ops.convert_bytes(transfer_latest - transfer_previous)
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
        if downloading:
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
                if status == "Downloading":
                    if not transfer_progress.get(idnt).get("detail") == None:
                        if not transfer_progress.get(idnt).get("detail").get("total") == None:
                            #total = self.ops.convert_bytes(transfer_progress.get(idnt).get("detail").get("total"))
                            #transfer = self.ops.convert_bytes(transfer_progress.get(idnt).get("detail").get("current"))
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
                        #transfer_diff = self.ops.convert_bytes(transfer_latest - transfer_previous)
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




class Docker(ABC):
    def __init__(self):
        self.constants = Constants()
        self.logger = Logging()
        self.io = InputOutput()
        self.ops = Operations()
        self.settings = Settings()
        
        self.cli = docker.APIClient(base_url='unix://var/run/docker.sock')
        self.term = {}
        self.logger.debug(self.cli.version())
        self.errors = docker.errors
        self.build_success = True
        self.pull_order = None
        self.pulled_image = None
        self.console_output = {}
        self.status_test = {}
        self.out_stream = str()

    def _copy_from_line(self, image_count: int, from_image:str, from_files: List) -> None:
        if from_files is None:
            self.logger.error(f"No copy from files specified for alias '{from_image}'")
            return

        for cp_fr in from_files:
            copy_instructions = cp_fr.split(":")
            if len(copy_instructions) == 2:
                from_line = f"COPY --from={from_image} {copy_instructions[0]} {copy_instructions[1]}"
                self.logger.info(f"copying files from alias '{from_image}':'{copy_instructions[0]}' to '{copy_instructions[1]}'")
            elif len(copy_instructions) == 3:
                from_line = f"COPY --from={from_image} --chown={copy_instructions[0]}:{copy_instructions[0]} {copy_instructions[1]} {copy_instructions[2]}"
                self.logger.info(f"copying files from alias '{from_image}':'{copy_instructions[1]}' to '{copy_instructions[2]}' with permission '{copy_instructions[0]}:{copy_instructions[0]}'")
            else:
                self.logger.error(f"copy instructions for alias '{from_image}' must in include src:dst, not '{cp_fr}'")                                
                continue
            
            self.dockerfile_image_lines[image_count].append(from_line)
            self.dockerfile_image_lines[image_count].append(from_line)

    def lines_to_text(self, lines, justify=None):
        count = 0
        formated_lines = []
        for i, l in enumerate(lines):
            if i == 0:
                fl = f"{str(count).ljust(justify)} {l}\n" if justify else f"{l}\n"
            elif i == (len(lines) - 1):
                fl = f"{str(count).ljust(justify)} {l}" if justify else f"{l}\n"
            else:
                fl = f"{str(count).ljust(justify)} {l}\n" if justify else f"{l}\n"
            formated_lines.append(fl)
            count+=1
        fulltext = str().join(formated_lines)
        return fulltext

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
            if self.constants.IS_WINDOWS_PLATFORM and path.startswith(
                    self.WINDOWS_LONGPATH_PREFIX):
                abs_dockerfile = '{}{}'.format(
                    self.constants.WINDOWS_LONGPATH_PREFIX,
                    os.path.normpath(
                        abs_dockerfile[len(self.constants.WINDOWS_LONGPATH_PREFIX):]
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

            if self.constants.IS_WINDOWS_PLATFORM:
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

    def process_build_stream(self, line):
        def rm_imgs():
            try:
                inter_image = self.cli.inspect_container(self.intermediate_container).get("Image")
                self.logger.warning(f"removing image: {inter_image}")
                self.cli.remove_container(self.intermediate_container, force=True)
                self.cli.remove_image(inter_image, force=True)
            except self.errors.APIError as err:
                raise BuildError(f"Builder: remove error - {err}")

        stream = line
        if stream.get("errorDetail"):
            raise BuildError("Builder: {err}".format(err=stream.get("errorDetail").get("message")))
        elif stream.get("aux"):
            if stream.get("aux").get("ID"):
                self.logger.info("Builder: {a}".format(a=stream.get("aux").get("ID")))
            else:
                self.logger.error("Builder: {a}".format(a=stream.get("aux")))
        elif stream.get("status"):
            idn = stream.get("id")
            idn_len = len(idn) if idn is not None else 0
            status = stream.get("status")
            self.status_test[status] = None
            #print(list(self.status_test.keys()))
            progress = stream.get("progress")
            detail = stream.get("progressDetail")
            if idn_len == 12:
                self.console_output[idn] = {
                    'status': status,
                    'progress': progress,
                }
            if len(self.console_output) > 0:
                #remove = {}
                #for idn, stats in self.console_output.items():
                #    if stats.get("status") == "Pull complete":
                #        remove[idn] = None
                #for idn, empty in remove.items():
                #    self.console_output.pop(idn, None)
                return self.console_output
        elif stream.get("stream"):
            if stream.get("stream").isspace():
                return
            ln = stream.get("stream").rstrip()
            items = ln.split()
            msg = [i for i in items[1:]]
            error_prompts = ["fatal:", "ERROR:", "error:"]
            if "E:" in items[0]:
                if self.settings.args.rm_inter_imgs:
                    rm_imgs()
                raise BuildError("Builder Apt Error: {m}".format(m=" ".join(msg)))
            elif "/bin/sh:" in items[0] and len(msg) > 0:
                if self.settings.args.rm_inter_imgs:
                    rm_imgs()
                raise BuildError("Builder Shell Error: {m}".format(m=" ".join(msg)))
            elif "CMake" in items[0] and "Error:" in items[1]:
                if self.settings.args.rm_inter_imgs:
                    rm_imgs()
                raise BuildError("Builder Cmake Error: {m}".format(m=" ".join(msg[1:])))
            if any([self.io.in_list(e, items[0]) for e in error_prompts]):
                if self.settings.args.rm_inter_imgs:
                    rm_imgs()
                raise BuildError("Builder Error: {m}".format(m=" ".join(msg)))
            #elif "\x1b[91m" in items[0]: # Look for catchall errors "red text"
            #    if self.settings.args.rm_inter_imgs:
            #        rm_imgs()
            #    raise BuildError("Builder: error - {m}".format(m=" ".join(msg)))
            elif items[0] == "Step": # Look for build steps
                self.logger.info("Builder: Step {m}".format(m=" ".join(msg)))
            elif items[0] == "--->": # Look for build progression info
                if items[1] == "Running" and items[2] == "in":
                    self.intermediate_container = items[3]
                self.logger.info("Builder: {m}".format(m=" ".join(msg)))
            elif items[0] == "Successfully": # Look for success info
                self.logger.info("Builder: Successfully {m}".format(m=" ".join(msg)))
                self.build_success = True
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
            else:
                self.logger.debug(ln)
        else:
            self.logger.error(stream)

    def build(self):
        pushstat = PushStatus()
        
        self.logger.info("Starting docker builder")
        
        if self.settings.args.gzip: self.logger.info(f"gzip file compression enabled")

        # Get permissions
        stat_info = os.stat(self.ops.work_dir)
        uid = stat_info.st_uid
        gid = stat_info.st_gid
        mask = str(oct(stat_info.st_mode)[-3:])
        user = pwd.getpwuid(uid)[0]
        group = grp.getgrgid(gid)[0]

        # Set main repository
        main_repository = self.settings.args.repository if self.settings.args.repository else self.ops.configs.get("info").get("repository")

        # Define project
        projects = self.ops.configs.get("build").get("projects")

        ### Process Dockerfiles
        self.dockerfile_image_lines = {}
        self.dockerfile_final_lines = []
        final_image_docker_path = ""
        project_files = []
        image_count = 0
        push_versions = {}
        pull_versions = {}
        total_images = sum([len(p.get("dockerfiles")) for p in projects])

        ### Generate a sorted and indexed list of images to check against the repository
        all_images_list = list(itertools.chain.from_iterable([(p.get("dockerfiles")) for p in projects]))
        all_images_dict = {}
        for idx, a_img_props in enumerate(all_images_list):
            docker_path = "{r}/{n}:{t}".format(r=a_img_props.get("repository"), n=a_img_props.get("name"), t=a_img_props.get("tag"))
            reverse_idx = (total_images - 1) - idx
            all_images_dict[reverse_idx] = {
                'path': docker_path,
                'repo': a_img_props.get("repository"),
                'name': a_img_props.get("name"),
                'tag': a_img_props.get("tag"),
                'push_version': a_img_props.get("push_version"),
                'pull_version': a_img_props.get("pull_version"),
            }
        pull_images = dict(sorted(all_images_dict.items()))

        ### Iterate through projects
        for p in projects:
            ### Store a list of Dockerfiles to process
            dockerfiles = []
            for df in p.get("dockerfiles"):
                dockerfiles.append(df.get("file"))

            ### Define directory to scan
            project_dir = self.ops.parent_dir.joinpath(p.get("directory"))
            default_dir = self.ops.default_images.joinpath(project_dir)
            if self.io.valid_dir(project_dir.as_posix()):
                project_dir = project_dir
            elif self.io.valid_dir(default_dir.as_posix()):
                project_dir = default_dir
            else:
                self.logger.error(f"Directories '{project_dir.as_posix()}' and '{default_dir.as_posix()}' do not exist! Checking current directory...")
                project_dir = Path.cwd()
            
            ### Scan project directory for dockerfiles
            if os.path.exists(project_dir.as_posix()):
                self.logger.info(f"processing dockerfiles in: '{project_dir.as_posix()}'")

                ### Iterate through images
                for image in p.get("dockerfiles"):                
                    # Get Dockerfile properties
                    image_repository = main_repository if main_repository else image.get("repository")
                    image_name = image.get("name")
                    image_tag = image.get("tag") if image.get("tag") else "latest"
                    # Get image arguments
                    image_args = {a.split("=")[0]:a.split("=")[1] for a in image.get("args") if len(a.split("=")) == 2} if image.get("args") else None
                    # Allow copying of image contents
                    image_copy_alias = image.get("copy-alias")
                    image_copy_from = image.get("copy-from")
                    image_copy_files = image.get("copy-files")
                    # Determine whether to copy existing entrypoint or command
                    image_copy_entrypoint = image.get("copy-entrypoint")
                    image_copy_cmd = image.get("copy-cmd")
                    # Set a user for the image
                    image_user = image.get("user")
                    # Set image exposed port
                    image_port= image.get("expose-port")
                    # Set dockerfile_path
                    dockerfile_path = project_dir.joinpath(image.get("file"))
                    # Set image Docker path
                    image_docker_path = f"{image_repository}/{image_name}:{image_tag}"

                    # Display current image and arguments
                    self.logger.debug(f"image({image_count}): {image_docker_path}")
                    self.logger.warning(f"image({image_count}) arguments:\n'{json.dumps(image_args, indent=4)}'")               

                    ### Pull images from repository if exists
                    if not self.pull_order:
                        for idx, img in pull_images.items():
                            push_version = img.get("push_version") if img.get("push_version") is not None else "latest"
                            image_push = True if self.settings.args.push or img.get("push_version") else False
                            if self.settings.args.push:
                                push_versions[img.get("path")] = [push_version, self.now_tag] + self.ops.version_tags
                            elif push_version != "latest":
                                push_versions[img.get("path")] = [push_version, "latest"] if image_push else []
                            elif push_version == "latest":
                                push_versions[img.get("path")] = ["latest", self.now_tag] if image_push else []
                                
                            pull_version = img.get("pull_version") if img.get("pull_version") is not None else "latest"
                            image_pull = True if self.settings.args.pull or img.get("pull_version") else False
                            pull_versions[img.get("path")] = self.ops.version_tags + [pull_version, ""]
                            if image_pull and not self.settings.args.local:
                                if not self.settings.args.dryrun:
                                    for tg in pull_versions[img.get("path")]:
                                        version_image_docker_path = "{p}-{t}".format(p=img.get("path"), t=tg)
                                        self.logger.debug(f"pulling image: '{version_image_docker_path}'")
                                        try:
                                            [pushstat.store(line) for line in self.cli.pull(
                                                "{r}/{n}".format(r=img.get("repo"), n=img.get("name")),
                                                "{ts}-{t}".format(ts=img.get("tag"), t=tg),
                                                stream=True, 
                                                decode=True
                                            )]
                                            self.run_build = False
                                            self.pull_order = (total_images - 1) - idx
                                            self.pulled_image = version_image_docker_path
                                            self.logger.info(f"Repo image found: '{version_image_docker_path}'")
                                        except self.errors.NotFound as notfound:
                                            self.logger.debug(f"Repo image not found: '{version_image_docker_path}'")
                                            self.run_build = True
                                            self.build_success = True
                                        except self.errors.APIError as a_err:
                                            self.logger.error(f"docker api error: {a_err}")
                                            self.run_build = False
                                            self.build_success = False                                                                      
                                        except Exception as err:
                                            self.logger.error(f"unknown error: {err}")
                                            self.run_build = False
                                            self.build_success = False
                                elif self.settings.args.dryrun:
                                    for tg in pull_versions[img.get("path")]:
                                        version_image_docker_path = "{p}-{t}".format(p=img.get("path"), t=tg)
                                        self.logger.debug(f"pulling image: '{version_image_docker_path}'")
                                        self.run_build = False
                                        self.pull_order = (total_images - 1) - idx
                                        self.pulled_image = version_image_docker_path
                                        self.logger.info(f"Repo image found: '{version_image_docker_path}'")
                        if not self.pulled_image:
                            # Set pull order to process all images
                            self.pull_order = image_count - 1          

                    if not self.settings.args.dryrun:
                        # Skip parent images of pulled image
                        if not self.pull_order or image_count <= self.pull_order:
                            image_count+=1
                            continue

                    # Show pulled parent image
                    if self.pulled_image:
                        self.logger.info(f"pulled({self.pull_order}): image: '{self.pulled_image}'")

                    # Set final name
                    if image_count == (total_images - 1): 
                        final_image_docker_path = image_docker_path

                    ### Run build logic
                    if os.path.exists(dockerfile_path.as_posix()):
                        self.logger.info(f"Building image: '{image_tag}' from '{dockerfile_path.as_posix()}'")

                        ### Read dockerfile
                        self.dockerfile_image_lines[image_count] = []
                        with open(dockerfile_path.as_posix()) as f:
                            lines = f.readlines()

                        ### Set from, entrypoint and command specified in config
                        build_base = self.pulled_image if self.pulled_image else self.ops.configs.get("build").get("base")
                        build_cmd = self.ops.configs.get("build").get("command") if self.ops.configs.get("build").get("command") else None
                        build_entrypoint = self.ops.configs.get("build").get("entrypoint") if self.ops.configs.get("build").get("entrypoint") else None
                        project_from = self.pulled_image if self.pulled_image else image.get("from")
                        dockerfile_entrypoint = None
                        dockerfile_cmd = None

                        ### Modify Dockerfile
                        copy_elements = []
                        cont_count = 0
                        list_files = False
                        for l in lines:
                            # Get list of files formated as ["file1", "file2"]
                            if l.isspace():
                                continue
                            if l[0] == "#":
                                self.logger.debug(f"skipping commented line: {l}")
                                continue
                            copy_chars = []
                            skip_line = False
                            items = l.split()
                            
                            copy_count = 0
                            num_items = len(items)
                            element = []
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
                                            element = []
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
                                        if all([image_count == 0, build_base, project_from]):
                                            if project_from == build_base:
                                                self.logger.debug(f"Base image: '{build_base}'")
                                                build_line = f"FROM {build_base}"
                                                self.dockerfile_final_lines.append(build_line)
                                                self.dockerfile_image_lines[image_count].append(build_line)
                                            else:
                                                self.logger.error(f"Base image: '{build_base}' does not match source of first image '{project_from}'!")
                                                sys.exit()
                                        elif all([image_count > 0, project_from is not None]):
                                            self.logger.debug(f"Source image: '{project_from}'")
                                            if image_copy_alias is not None:
                                                build_line = f"FROM {project_from} as {image_copy_alias}"
                                            else:
                                                build_line = f"FROM {project_from}"
                                            self.dockerfile_final_lines.append(build_line)
                                            self.dockerfile_image_lines[image_count].append(build_line)
                                        else:
                                            self.dockerfile_image_lines[image_count].append(f"{l}")
                                        skip_line = True
                                        continue
                                    if w == "ENTRYPOINT":
                                        if image_count == (total_images - 1):
                                            self.logger.debug(f"Image entrypoint: '{l.rstrip()}'")
                                            dockerfile_entrypoint = l.rstrip()
                                        skip_line = True
                                        continue
                                    if w == "CMD":
                                        if image_count == (total_images - 1):
                                            self.logger.debug(f"Image command: '{l.rstrip()}'")
                                            dockerfile_cmd = l.rstrip()
                                        skip_line = True
                                        continue
                                if skip_line:
                                    continue
                                else:
                                    self.dockerfile_image_lines[image_count].append(l.rstrip())
                                    self.dockerfile_final_lines.append(l.rstrip())
                        
                        # copy from image files
                        if image_copy_from is not None:
                            self._copy_from_line(image_count, image_copy_from, image_copy_files)
                        # create and set user
                        if image_user is not None:
                            user_create_line = f"RUN id -u {image_user} &>/dev/null || useradd -ms /bin/bash {image_user}"
                            self.dockerfile_image_lines[image_count].append("USER root")
                            self.dockerfile_final_lines.append("USER root")
                            self.dockerfile_image_lines[image_count].append(user_create_line)
                            self.dockerfile_final_lines.append(user_create_line)
                            
                            user_set_line = f"USER {image_user}"
                            self.dockerfile_image_lines[image_count].append(user_set_line)
                            self.dockerfile_final_lines.append(user_set_line)
                        if image_port is not None:
                            expose_line = f"EXPOSE {image_port}"
                            self.dockerfile_image_lines[image_count].append(expose_line)
                            self.dockerfile_final_lines.append(expose_line)
                        # copy image files
                        for e in copy_elements:
                            def is_from(field):
                                if field == "--from":
                                    self.logger.debug(f"skipping field: '{field}'")
                                    return True
                                else:
                                    return False
                            src = project_dir.joinpath(e)
                            dst = self.ops. project_build_dir.joinpath(e)
                            if self.settings.args.dryrun:
                                self.logger.debug(f"Dry run: copying: '{src}' --> '{dst}'")
                            elif not self.settings.args.dryrun:
                                if any([is_from(s) for s in e.split("=")]):
                                    continue
                                try:
                                    self.ops.copy_path(src, dst, self.settings.args.overwrite)
                                except OperationError as operr:
                                    self.logger.error(operr)
                            project_files.append(dst)
                        
                        # Track log file and project build directory
                        project_files.append(self.ops.log_file.as_posix())
                        project_files.append(self.ops.project_build_dir.as_posix())

                        # Set image entrypoint
                        if build_entrypoint:
                            final_entrypoint = build_entrypoint
                        elif dockerfile_entrypoint and image_copy_entrypoint:
                            final_entrypoint = dockerfile_entrypoint
                        else:
                            final_entrypoint = None
                        if final_entrypoint and image_count == (total_images - 1):
                            self.logger.debug(f"Final Entrypoint: '{final_entrypoint}'")
                            self.dockerfile_final_lines.append(f"ENTRYPOINT {final_entrypoint}")
                            self.dockerfile_image_lines[image_count].append(f"ENTRYPOINT {final_entrypoint}")

                        # Set image command
                        if build_cmd:
                            final_cmd = build_cmd
                        elif dockerfile_cmd and image_copy_cmd:
                            final_cmd = dockerfile_cmd
                        else:
                            final_cmd = None
                        if final_cmd and image_count == (total_images - 1):
                            self.logger.debug(f"Final Command: '{final_cmd}'")
                            self.dockerfile_final_lines.append(f"CMD {final_cmd}")
                            self.dockerfile_image_lines[image_count].append(f"CMD {final_cmd}")

                        # Display dockerfile contents to console
                        if self.settings.args.show:
                            print(f"Image: {image_docker_path}")
                            print(f"Dockerfile: {dockerfile_path}")
                            print(self.lines_to_text(self.dockerfile_image_lines[image_count], justify=4))
            
                        # Encode before building
                        dockerfile_encoded = io.BytesIO(self.lines_to_text(self.dockerfile_image_lines[image_count]).encode('utf-8'))

                        # Read dockerignore for files to exclude
                        docker_ignore = project_dir.joinpath('.dockerignore')
                        docker_exclude = None
                        if os.path.exists(docker_ignore.as_posix()):
                            with open(docker_ignore.as_posix(), 'r') as f:
                                docker_exclude = list(filter(
                                    lambda x: x != '' and x[0] != '#',
                                    [l.strip() for l in f.read().splitlines()]
                                ))

                        # Create manifest
                        dockerfile_processed = self.process_dockerfile(dockerfile_path.as_posix(), project_dir.as_posix())
                        encoding = None
                        encoding = 'gzip' if self.settings.args.gzip else encoding
                        dockerfile_obj = self.makebuildcontext(project_dir.as_posix(), dockerfile_encoded, dockerfile_processed, docker_exclude, self.settings.args.gzip)
                        
                        # Build images
                        self.run_build = True if self.build_success else False
                        if self.build_success:
                            self.logger.info(f"building: '{image_docker_path}'")
                            if self.run_build and image_count >= self.pull_order:
                                if not self.settings.args.dryrun:
                                    with Live(self.out_stream, screen=False, auto_refresh=False, transient=True) as live:
                                        try:
                                            for line in self.cli.build(
                                                fileobj=dockerfile_obj, 
                                                rm=True, 
                                                tag=image_docker_path,
                                                decode=True,
                                                custom_context=True,
                                                buildargs=image_args,
                                                nocache=self.settings.args.nocache,
                                            ):
                                                self.out_stream = self.process_build_stream(line)
                                                if self.out_stream:
                                                    table = Table(show_header=False, show_edge=False, box=box.SIMPLE)
                                                    table.add_column("ID", width=12)
                                                    table.add_column("Status", width=20)
                                                    table.add_column("Progress")
                                                    for idn, attr in self.out_stream.items():
                                                        table.add_row(idn, attr.get("status"), attr.get("progress"))
                                                    live.update(table, refresh=True)
                                            self.run_build = True
                                        except self.errors.APIError as a_err:
                                            self.logger.error(f"Docker API error: {a_err}")
                                            self.run_build = False
                                            self.build_success = False
                                        except self.errors.BuildError as b_err:
                                            self.logger.error(f"Docker Build error: {b_err}")
                                            self.run_build = False
                                            self.build_success = False
                                        except BuildError as b_err:
                                            self.logger.error(f"{b_err}")
                                            self.run_build = False
                                            self.build_success = False
                                        except TypeError as t_err:
                                            self.logger.error(f"error: {t_err}")
                                            self.run_build = False
                                            self.build_success = False                 
                                        except Exception as err:
                                            self.logger.error(f"unknown error: {err}")
                                            self.run_build = False
                                            self.build_success = False
                                elif self.settings.args.dryrun:
                                    self.run_build = True
                                if not self.run_build and not self.build_success:
                                    self.logger.info(f"failed to build: '{image_docker_path}'")
                                    self.logger.info(f"dockerfile: '{dockerfile_path.as_posix()}'")
                                    sys.exit()    
                            else:
                                self.logger.info(f"succesfully built: '{image_docker_path}'")
                                self.run_build = False
                                self.build_success = True
                            
                            # Set version tags for final image
                            for t in push_versions[image_docker_path]:
                                version_image_docker_path = f"{image_repository}/{image_name}:{image_tag}-{t}"
                                self.logger.info(f"tagging image: {version_image_docker_path}")
                                if not self.settings.args.dryrun:
                                    try:
                                        self.cli.tag(f"{image_docker_path}", f"{image_repository}/{image_name}", f"{image_tag}-{t}", force=True)
                                    except self.errors.ImageNotFound as i_err:
                                        self.logger.error(f"not found: {image_docker_path}")
                                    except Exception as err:
                                        self.logger.error(f"unknown error: {err}")
                                #if save:
                                    #self.logger.info(f"saving image: {version_image_docker_path}")
                                    #if not self.settings.args.dryrun:
                                        #    f = open('/tmp/busybox-latest.tar', 'wb')
                                        #    for chunk in image:
                                        #        f.write(chunk)
                                        #    f.close()
                                self.logger.info(f"Pushing: '{version_image_docker_path}'")
                                if not self.settings.args.dryrun:
                                    if self.settings.args.overwrite:
                                        self.logger.warning(f"Overwriting image: '{version_image_docker_path}'")
                                        self.cli.remove_image(version_image_docker_path, force=True)

                                    pushstat.set_image(version_image_docker_path)
                                    [pushstat.store(line) for line in self.cli.push(
                                        version_image_docker_path, stream=True, decode=True
                                    )]

                            image_count+=1
                        else:
                            self.logger.error(f"build failed: {image_docker_path}")
                    else:
                        self.logger.error(f"Dockerfile does not exists: '{dockerfile_path.as_posix()}")
                        sys.exit()                
            else:
                self.logger.error(f"Project dir does not exists: '{project_dir.as_posix()}")
                sys.exit()

        # Append to project file tracker for later (optional)removal
        project_files.append(self.ops.build_dir)

        # Set final dockerfile path
        dockerfile_final_path = self.ops.project_build_dir.joinpath("Dockerfile")
        
        ### Display final Dockerfile
        if self.settings.args.show:
            print(f"Final Image: {final_image_docker_path}")
            print(f"Final dockerfile: '{dockerfile_final_path}'")
            print(self.lines_to_text(self.dockerfile_final_lines, justify=4))
        
        ### Write final Dockerfile
        if self.settings.args.dryrun:
            self.logger.info(f"Dry run: Writing final Dockerfile to: '{dockerfile_final_path.as_posix()}'")
        if not self.settings.args.dryrun and self.build_success:
            self.logger.info(f"Writing final Dockerfile to: '{dockerfile_final_path.as_posix()}")
            with open(dockerfile_final_path.as_posix(), "w") as f: 
                f.write(self.lines_to_text(self.dockerfile_final_lines))
            # Track Dockerfile
            project_files.append(dockerfile_final_path.as_posix())
            # Fix Dockerfile permissions
            self.ops.chown(dockerfile_final_path.as_posix(), user, group)
            self.ops.chmod(dockerfile_final_path.as_posix(), "664")
            # Fix log file permissions
            self.ops.chown(self.ops.log_file.as_posix(), user, group)
            self.ops.chmod(self.ops.log_file.as_posix(), "664")

            # Remove residual project files
            if self.settings.args.rm_build_files:
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