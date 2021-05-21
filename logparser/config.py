import configparser
import logging
import os
from pathlib import Path

import geoip2.database
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Settings(object):

    _shared_state = {}

    CONFIG_FILES = [
        'logparser.conf',
        '~/.logparser.conf',
        '/etc/logparser.conf'
    ]

    DEFAULTS = {
        'HOST': 'localhost',
        'FORMAT': 'json',
        'LOG_LEVEL': 'WARN',
        'GEOIP2_DATABASE': 'GeoLite2-Country.mmdb'
    }

    def __init__(self):
        self.__dict__ = self._shared_state

    def __str__(self):
        return str(vars(self))

    def setup(self, args):
        # setup env from .env file
        load_dotenv(Path().cwd() / '.env')

        # read config file
        config = self.read_config(args.config_file)

        # combine settings from args, os.environ, and config
        self.build_settings(args, os.environ, config)

        if self.FORMAT == 'json' and self.CHUNKING:
            raise RuntimeError('--format=json does not work with --chunking')

        # cast CHUNKING to int
        self.CHUNKING = int(self.CHUNKING)

        # split lists
        self.IGNORE_HOST = self.IGNORE_HOST.split() if isinstance(self.IGNORE_HOST, str) else self.IGNORE_HOST
        self.IGNORE_PATH = self.IGNORE_PATH.split() if isinstance(self.IGNORE_PATH, str) else self.IGNORE_PATH

        # setup logging
        self.LOG_LEVEL = self.LOG_LEVEL.upper()
        self.LOG_FILE = Path(self.LOG_FILE).expanduser() if self.LOG_FILE else None
        logging.basicConfig(level=self.LOG_LEVEL, filename=self.LOG_FILE,
                            format='[%(asctime)s] %(levelname)s: %(message)s')

        # setup geoip2.database.Reader
        self.GEOIP2_READER = geoip2.database.Reader(self.GEOIP2_DATABASE) if self.GEOIP2_DATABASE else None

    def read_config(self, config_file_arg):
        config_files = [config_file_arg] + self.CONFIG_FILES
        for config_file in config_files:
            if config_file:
                config = configparser.ConfigParser()
                config.read(config_file)
                if 'default' in config:
                    return config['default']

    def build_settings(self, args, environ, config):
        args_dict = vars(args)
        for key, value in args_dict.items():
            if key not in ['func', 'config_file']:
                attr = key.upper()
                if value is not None:
                    attr_value = value
                elif environ.get(attr):
                    attr_value = environ.get(attr)
                elif config and config.get(key):
                    attr_value = config.get(key)
                else:
                    attr_value = self.DEFAULTS.get(attr)

                setattr(self, attr, attr_value)


settings = Settings()
