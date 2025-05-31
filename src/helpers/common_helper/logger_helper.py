import logging
import os
import sys


class LoggerHelper:

    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)

        # Set log level based on env variable or default to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.logger.setLevel(log_level)

        # Avoid duplicate handlers in AWS Lambda cold starts
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.propagate = False

    def get_logger(self) -> logging.Logger:
        return self.logger
