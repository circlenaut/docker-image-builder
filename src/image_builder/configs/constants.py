import re
import sys
from abc import ABC

__all__ = ['Constants']


class Constants(ABC):
    def __init__(self):
        self.IS_WINDOWS_PLATFORM = (sys.platform == 'win32')
        self._SEP = re.compile('/|\\\\') if self.IS_WINDOWS_PLATFORM else re.compile('/')
        self._cache = {}
        self._MAXCACHE = 100