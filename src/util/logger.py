import logging
import os

from .config import Config
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

class Logger:
    """Logger singleton. Configures the logging and is then used throughout the application."""

    _instance = None
    logger = None
    SCRIPT_DIR = os.path.dirname(__file__)
    LOG_FILE_PATH = os.path.join(SCRIPT_DIR, "../../app.log")

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        """Initialize the logger only if it's not already initialized."""
        if not self.logger:
            logger = logging.getLogger('root')
            config_log_level = Config().get_log_level()
            self.log_level = config_log_level
            logger.setLevel(self.map_log_level(config_log_level))
            self.logger = logger
            self.set_file_handlers()
            logger.info("Logger has been initialized.")

    def map_log_level(self, log_level):
        if log_level == "debug":
            return logging.DEBUG
        elif log_level == "info":
            return logging.INFO
        elif log_level == "warning":
            return logging.WARNING
        elif log_level == "error":
            return logging.ERROR
        elif log_level == "critical":
            return logging.CRITICAL

    def get_log_level(self):
        return self.log_level

    def set_file_handlers(self):
        """Sets up file handlers with log rotation."""
        if self.logger.hasHandlers():
            self.logger.handlers = []
        # Use RotatingFileHandler for size-based rotation
        size_handler = RotatingFileHandler(self.LOG_FILE_PATH, maxBytes=1e8, backupCount=4)
        size_handler.setLevel(self.map_log_level(self.log_level))
        logging_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s  [File: %(filename)s, Line: %(lineno)d, Function: %(funcName)s]'
        size_handler.setFormatter(logging.Formatter(logging_format))
        # Add handlers to the logger
        self.logger.addHandler(size_handler)

    def debug(self, message):
        self.logger.debug(message, stacklevel=2)

    def info(self, message):
        self.logger.info(message, stacklevel=2)

    def warning(self, message):
        self.logger.warning(message, stacklevel=2)

    def error(self, message):
        self.logger.error(message, stacklevel=2)

    def critical(self, message):
        self.logger.critical(message, stacklevel=2)

    def exception(self, message):
        self.logger.exception(message, stacklevel=2)

