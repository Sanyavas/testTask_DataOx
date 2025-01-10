import logging
import os

# ANSI escape codes for colors
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
GREEN = '\033[92m'


class ColorFormatter(logging.Formatter):
    """ Custom formatter to add color to log levels """

    def format(self, record):
        color = ''
        if hasattr(record, 'custom_color') and record.custom_color:
            if record.levelno == logging.INFO:
                color = GREEN
        elif record.levelno == logging.WARNING:
            color = YELLOW
        elif record.levelno == logging.ERROR or record.levelno == logging.CRITICAL:
            color = RED

        record.msg = f'{color}{record.msg}{RESET}'
        return super().format(record)


_format = "[%(levelname)s] %(asctime)s - %(name)s - %(funcName)s(%(lineno)d) - %(message)s"

log_dir = 'logs'
# створення
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
file = os.path.join(log_dir, 'logs.log')

file_handler = logging.FileHandler(file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(_format))

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
# Use the custom ColorFormatter for the stream handler
stream_handler.setFormatter(ColorFormatter(_format))


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger