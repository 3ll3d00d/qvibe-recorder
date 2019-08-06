import logging
import os
from logging import handlers
from os import environ, path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'port': 10002,
    'debugLogging': False,
    'samplesPerBatch': 8,
    'accelerometers': [
        {
            'name': 'mpu6050',
            'type': 'mpu6050',
            'fs': 500,
            'io': {
                'type': 'smbus',
                'busId': 1
            }
        }
    ]
}


class Config:
    def __init__(self, default_port=10001):
        self.config = self.__load_config()
        self.__port = self.config.get('port', default_port)

    @property
    def default_hostname(self):
        import socket
        return socket.getfqdn()

    def is_debug_logging(self):
        """
        :return: if debug logging mode is on, defaults to False.
        """
        return self.config.get('debugLogging', False)

    @property
    def port(self):
        """
        :return: the port to listen on, defaults to 10001
        """
        return self.__port

    def __load_config(self):
        """
        loads configuration from some predictable locations.
        :return: the config.
        """
        config_path = path.join(self.config_path, "qvibe-recorder.yml")
        if os.path.exists(config_path):
            logger.warning(f"Loading config from {config_path}")
            with open(config_path, 'r') as yml:
                return yaml.load(yml, Loader=yaml.FullLoader)
        self.__store_config(DEFAULT_CONFIG, config_path)
        return DEFAULT_CONFIG

    def __store_config(self, config, config_path):
        """
        Writes the config to the configPath.
        :param config a dict of config.
        :param config_path the path to the file to write to, intermediate dirs will be created as necessary.
        """
        logger.info(f"Writing to {config_path}")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with (open(config_path, 'w')) as yml:
            yaml.dump(config, yml, default_flow_style=False)

    @property
    def config_path(self):
        """
        Gets the currently configured config path.
        :return: the path, raises ValueError if it doesn't exist.
        """
        conf_home = environ.get('QVIBE_CONFIG_HOME')
        return conf_home if conf_home is not None else path.join(path.expanduser("~"), '.qvibe')

    def configure_logger(self):
        """
        Configures the python logging system to log to a debug file and to stdout for warn and above.
        :return: the base logger.
        """
        base_log_level = logging.DEBUG if self.is_debug_logging() else logging.INFO
        # root logger
        logger = logging.getLogger('qvibe')
        logger.setLevel(base_log_level)
        # file handler
        fh = handlers.RotatingFileHandler(path.join(self.config_path, "qvibe-recorder.log"),
                                          maxBytes=10 * 1024 * 1024, backupCount=10)
        fh.setLevel(base_log_level)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARN)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger
