
import logging
import sys
from abc import ABC

import coloredlogs

from ..configs import Settings

__all__ = ['Logging']


class Logging(ABC):
    def __init__(self):        
        self.settings = Settings()
        
        # helpers.__init__(self)
        logger = self.setup_logging()
        self.color_logs()
        
        self.critical = logger.critical
        self.error = logger.error
        self.warning = logger.warning
        self.info = logger.info
        self.debug = logger.debug
    
    def setup_logging(self):
        logging.basicConfig(
            format='[%(levelname)s] %(message)s',
            level=logging.INFO,
            stream=sys.stdout)
        self.log = logging.getLogger(__name__)   
        self.log.setLevel(self.settings.args.log_level.upper())
        return self.log
    
    def color_logs(self):
        coloredlogs.install(fmt='[%(levelname)s] %(message)s', level=self.settings.args.log_level.upper(), logger=self.log)

    def save_logs(self, path):
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        fh = logging.FileHandler(path)
        fh.setLevel(self.settings.args.log_level.upper())
        fh.setFormatter(formatter)
        self.log.addHandler(fh)
        return self.log