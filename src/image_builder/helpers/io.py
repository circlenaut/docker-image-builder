import os
from abc import ABC

from pathlib import Path, PurePath

from ..configs import Settings
from ..internal import Logging

__all__ = ['IO']


class InputOutput(ABC):
    def __init__(self):
        self.logger = Logging()
        self.settings = Settings()
    
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

    def in_list(self, e, lst):
        if e in lst:
            return True
        else:
            return False

    def is_type_path(self, entry):
        spl = entry.split(os.sep)
        s = PurePath(entry).suffix
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