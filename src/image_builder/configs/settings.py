import argparse
import json
from abc import ABC

__all__ = ['Settings']


class Settings(ABC):
    def __init__(self):
        self.args = self.get_arg()

    def get_arg(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--opts', type=json.loads, help='Set script arguments')
        self.parser.add_argument('--log_level', choices=('debug', 'info', 'warning', 'error', 'critical'), default='info', const='info', nargs='?', required=False, help='Set script log level of verbosity')
        self.parser.add_argument('config', type=str, default='default', help="Location of build YAML file")
        self.parser.add_argument('--push', action='store_true', default=False, required=False, help="Push images to repositoy")
        self.parser.add_argument('--pull', action='store_true', default=False, required=False, help="Pull images from repositoy")
        self.parser.add_argument('--local', action='store_true', default=False, required=False, help="build all images locally")
        self.parser.add_argument('--nocache', action='store_true', default=False, required=False, help="build using cache")
        self.parser.add_argument('--repository', type=str, default='', required=False, help="Repository to push to")
        self.parser.add_argument('--save', type=str, required=False, help="Location to save image")
        self.parser.add_argument('--dryrun', action='store_true', default=False, required=False, help='Execute as a dry run')
        self.parser.add_argument('--gzip', action='store_true', default=False, required=False, help='Compress context files')
        self.parser.add_argument('--overwrite', action='store_true', default=False, required=False, help='Overwrite existing build files and images')
        self.parser.add_argument('--show', action='store_true', default=False, required=False, help='Show Dockerfiles on console')
        self.parser.add_argument('--rm_build_files', action='store_true', default=False, required=False, help='Remove build files')
        self.parser.add_argument('-f', '--force', action='store_true', default=False, required=False, help='Force a command without checks')
        self.parser.add_argument('-rmi', '--rm_inter_imgs', action='store_true', default=False, required=False, help='Remove intermediary images')
        #self.parser.add_argument('-s, --save', type=str, required=False, help="Location to save image")
        
        args, unknown = self.parser.parse_known_args()
        if unknown:
            print("Unknown arguments " + str(unknown))

        self.args = self.parser.parse_args()
        return self.args