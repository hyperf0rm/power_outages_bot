import logging
from dotenv import load_dotenv
import os
import sys

load_dotenv()

TOKEN = os.getenv("TOKEN")

RETRY_PERIOD = int(os.getenv("RETRY_PERIOD"))

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout
)


def check_env_vars():
    """Check environment variables existence."""
    logging.info("Checking environmental vars existence")
    env_variables = {
        "TELEGRAM_TOKEN": TOKEN,
        "RETRY_PERIOD": RETRY_PERIOD,
        "DB_HOST": DB_HOST,
        "DATABASE": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD
    }

    var_found = True

    for var_name, var in env_variables.items():
        if not var:
            logging.critical(
                f"Missing required environment variable: {var_name}")
            var_found = False
    return var_found
