import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    LOG_DIR = "logs"
    LOG_FILE_NAME = "bot.log"
    LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)

    MAX_FILE_SIZE = 10*1024*1024
    BACKUP_COUNT = 5

    os.makedirs(LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=MAX_FILE_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
        )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    return root_logger
