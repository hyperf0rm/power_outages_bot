from telebot import TeleBot
from dotenv import load_dotenv
import os
from parser import Parser
from psycopg2 import pool
import logging
import sys
from exceptions import MissingEnvironmentVariableException
import time
import threading
from utils import check_env_vars, generate_last_message_hash
from contextlib import contextmanager
import logging_config

load_dotenv()

DB_HOST = os.getenv("DB_HOST")

DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

TOKEN = os.getenv("TOKEN_PROD")
RETRY_PERIOD = int(os.getenv("RETRY_PERIOD"))

logger = logging_config.setup_logging()

bot = TeleBot(token=TOKEN)

cached_outages = {}
outages_lock = threading.Lock()

try:
    db_pool = pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )
    if db_pool:
        logging.info("Connection pool created succesfully")
except Exception as error:
    logging.critical(f"Error creating a connection pool: {error}")
    sys.exit(1)


@contextmanager
def get_db_cursor():
    conn = db_pool.getconn()
    try:
        yield conn.cursor()
        conn.commit()
    except Exception as error:
        logging.error(f"Database error: {error}")
        conn.rollback()
        raise error
    finally:
        db_pool.putconn(conn)


@bot.message_handler(commands=["start", "info"])
def start(message):
    user_id = message.chat.id
    bot_msg = ("После добавления адреса бот будет работать в фоновом режиме "
               "и отправит вам сообщение, если по вашему адресу будет "
               "запланировано отключение.\n\n"

               "Рекомендации:\n"
               "- при добавлении или проверке адреса указывайте его "
               "без дополнительных слов и номера дома. "
               "Например: /add Тиграняна\n"
               "- при добавлении села или другого "
               "небольшого населенного пункта указывайте "
               "только название этого населенного пункта. "
               "Например: /add Шенаван\n\n"

               "Доступные команды:\n"
               "/add - добавить адрес. В формате: /add Тиграняна\n"
               "/delete - удалить адрес.  В формате: /delete Тиграняна\n"
               "/check - проверить адрес. В формате: /check Тиграняна\n"
               "/show - показать ваши добавленные адреса\n"
               "/my - проверить отключения по вашим адресам\n"
               "/info - информация об этом боте"
               )

    try:
        if message.text.startswith("/start"):
            username = message.from_user.username
            logging.info(f"Sending /start message to user {user_id}")
            with get_db_cursor() as cur:
                cur.execute(
                    """INSERT INTO light_bot.users (user_id, username)
                    VALUES (%s, %s)
                    ON CONFLICT ON CONSTRAINT user_id_unique DO NOTHING;""",
                    (user_id, username)
                )
                if cur.rowcount == 1:
                    logging.info(f"User {user_id} activated the bot")

        if message.text.startswith("/info"):
            logging.info(f"Sending /info message to user {user_id}")

        bot.send_message(user_id, bot_msg)
    except Exception as error:
        logging.error(f"Error: {error}")
        bot.send_message(user_id, "Ошибка. Попробуйте снова")


@bot.message_handler(commands=["add"])
def add(message):
    user_id = message.chat.id
    logging.info(f"Sending /add message to user {user_id}")

    if message.text == "/add":
        bot.send_message(user_id, "Укажите адрес, например: /add Бабаяна")
        return

    address = message.text.replace("/add ", "")
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT EXISTS
                (SELECT 1 FROM light_bot.addresses
                WHERE user_id = %s AND address = %s);""",
                (user_id, address)
            )
            if cur.fetchone()[0]:
                bot_msg = f"Адрес {address} уже добавлен"
            else:
                cur.execute(
                    """INSERT INTO light_bot.addresses (user_id, address)
                    VALUES (%s, %s);""",
                    (user_id, address)
                )
                bot_msg = f"Добавлен адрес: {address}"
                logging.info(f"User {user_id} added address {address}")
        bot.send_message(user_id, bot_msg)
    except Exception as error:
        logging.error(f"Error: {error}")
        bot.send_message(user_id, "Ошибка. Попробуйте снова")


@bot.message_handler(commands=["delete"])
def delete(message):
    user_id = message.chat.id
    logging.info(f"Sending /delete message to user {user_id}")

    if message.text == "/delete":
        bot.send_message(user_id, "Укажите адрес, например: /delete Бабаяна")
        return

    address = message.text.replace("/delete ", "")
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """DELETE FROM light_bot.addresses
                WHERE user_id = %s and address = %s
                RETURNING id;""",
                (user_id, address)
            )
            if cur.fetchall():
                bot_msg = f"Удален адрес: {address}"
                logging.info(f"User {user_id} deleted address {address}")
            else:
                bot_msg = "Этот адрес не был вами добавлен"
        bot.send_message(user_id, bot_msg)
    except Exception as error:
        logging.error(f"Error: {error}")
        bot.send_message(user_id, "Ошибка. Попробуйте снова")


@bot.message_handler(commands=["show"])
def show(message):
    user_id = message.chat.id
    logging.info(f"Sending /show message to user {user_id}")

    try:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT address FROM light_bot.addresses
                WHERE user_id = %s;""",
                (user_id,)
            )
            addresses = [address[0] for address in cur.fetchall()]
            if addresses:
                bot_msg = "Добавленные адреса:\n\n" + "\n".join(addresses)
            else:
                bot_msg = "Вы не добавили ни один адрес"
        bot.send_message(user_id, bot_msg)
    except Exception as error:
        logging.error(f"Error: {error}")
        bot.send_message(user_id, "Ошибка. Попробуйте снова")


@bot.message_handler(commands=["my"])
def my(message):
    user_id = message.chat.id
    logging.info(f"Sending /my message to user {user_id}")

    try:
        with get_db_cursor() as cur:
            cur.execute(
                """SELECT address FROM light_bot.addresses
                WHERE user_id = %s;""",
                (user_id,)
            )
            addresses = [address[0] for address in cur.fetchall()]

            with outages_lock:
                outages = cached_outages.copy()

            if not outages:
                logging.warning("No data fetched or empty site")
                bot.send_message(
                    user_id,
                    "Данные об отключениях недоступны, попробуйте позже"
                )
                return

            messages_for_user = []

            for date, addresses_list in outages.items():
                for addr in addresses_list:
                    for user_addr in addresses:
                        if user_addr.lower() in addr.lower():
                            msg = f"{date}\n\n{addr}"
                            if msg not in messages_for_user:
                                messages_for_user.append(msg)

            if not messages_for_user:
                new_message = (
                    "Нет информации об отключениях электроэнергии "
                    "по вашим адресам в ближайшие дни"
                )

            else:
                new_message = "\n\n".join(messages_for_user)

            new_message_hash = generate_last_message_hash(new_message)
            cur.execute(
                """SELECT last_message_hash FROM light_bot.users
                WHERE user_id = %s;""",
                (user_id,)
            )
            last_msg_hash = cur.fetchone()[0]

            if new_message_hash != last_msg_hash:
                cur.execute(
                    """UPDATE light_bot.users
                    SET last_message_hash = %s
                    WHERE user_id = %s;""",
                    (new_message_hash, user_id)
                )
                logging.info(f"Updated last message for user {user_id}")
        bot.send_message(user_id, new_message)
    except Exception as error:
        logging.error(f"Error: {error}")
        bot.send_message(user_id, "Ошибка. Попробуйте снова")


@bot.message_handler(commands=["check"])
def check(message):
    user_id = message.chat.id
    logging.info(f"Sending /check message to user {user_id}")

    if message.text == "/check":
        bot.send_message(user_id, "Добавьте адрес вместе с командой")
        return

    user_address = message.text.replace("/check ", "")
    try:
        with outages_lock:
            outages = cached_outages.copy()

        if not outages:
            logging.warning("No data fetched or empty site")
            bot.send_message(
                user_id,
                "Данные об отключениях недоступны, попробуйте позже"
            )
            return

        messages_for_user = []

        for date, addresses_list in outages.items():
            for addr in addresses_list:
                if user_address.lower() in addr.lower():
                    msg = f"{date}\n\n{addr}"
                    if msg not in messages_for_user:
                        messages_for_user.append(msg)

            if not messages_for_user:
                message = (
                    "Нет информации об отключениях электроэнергии "
                    "по вашим адресам в ближайшие дни"
                )

            else:
                message = "\n\n".join(messages_for_user)

        bot.send_message(user_id, message)
    except Exception as error:
        logging.error(f"Error: {error}")
        bot.send_message(user_id, "Ошибка. Попробуйте снова")


@bot.message_handler()
def msg(message):
    user_id = message.chat.id
    logging.info(f"Sending general message to user {user_id}")
    try:
        bot.send_message(user_id, "Список доступных команд: /info")
    except Exception as error:
        logging.error(f"Error: {error}")


def main():
    logging.info("Starting background job")
    parser = Parser()
    global cached_outages

    while True:
        try:
            logging.info("Fetching data from website")
            outages = parser.parse_website()

            if not outages:
                logging.warning("No data fetched or empty site")
                time.sleep(RETRY_PERIOD)
                continue

            with outages_lock:
                cached_outages = outages
            logging.info("Outages dict updated successfully")

            with get_db_cursor() as cur:
                cur.execute(
                    """SELECT u.user_id, u.last_message_hash, a.address
                    FROM light_bot.users u
                    JOIN light_bot.addresses a ON u.user_id = a.user_id
                    WHERE u.blocked_at IS NULL"""
                )
                users = cur.fetchall()

            user_data = {}

            for row in users:
                uid, last_msg_hash, address = row
                if uid not in user_data:
                    user_data[uid] = {
                        "last_msg_hash": last_msg_hash,
                        "addresses": []
                    }
                user_data[uid]["addresses"].append(address)

            for user_id, data in user_data.items():
                try:
                    logging.info(f"Checking user {user_id} addresses")
                    user_addresses = data["addresses"]
                    last_message_hash = data["last_msg_hash"]

                    messages_for_user = []

                    for date, addresses_list in outages.items():
                        for addr in addresses_list:
                            for user_addr in user_addresses:
                                if user_addr.lower() in addr.lower():
                                    msg = f"{date}\n\n{addr}"
                                    if msg not in messages_for_user:
                                        messages_for_user.append(msg)

                    if not messages_for_user:
                        new_message = (
                            "Нет информации об отключениях электроэнергии "
                            "по вашим адресам в ближайшие дни"
                        )

                    else:
                        new_message = "\n\n".join(messages_for_user)

                    new_message_hash = generate_last_message_hash(new_message)

                    if new_message_hash != last_message_hash:
                        logging.info(
                            f"Starting sending main message to user {user_id}"
                        )
                        with get_db_cursor() as cur:
                            cur.execute(
                                """UPDATE light_bot.users
                                SET last_message_hash = %s
                                WHERE user_id = %s;""",
                                (new_message_hash, user_id)
                            )
                        logging.info(
                            f"Updated last message for user {user_id}"
                        )
                        bot.send_message(user_id, new_message)
                except Exception as error:
                    logging.error(
                        f"Error sending message to user {user_id}: {error}"
                    )

        except Exception as error:
            logging.error(f"Background job error: {error}")

        finally:
            time.sleep(RETRY_PERIOD)


@bot.my_chat_member_handler()
def handle_user_status(update):
    new_status = update.new_chat_member.status
    user_id = update.chat.id
    try:
        if new_status == "kicked":
            logging.warning(f"User {user_id} has blocked the bot")
            with get_db_cursor() as cur:
                cur.execute("""UPDATE light_bot.users
                            SET blocked_at = NOW()
                            WHERE user_id = %s;""",
                            (user_id,)
                            )
        elif new_status == "member":
            old_status = update.old_chat_member.status
            if old_status == "kicked":
                logging.info(
                    f"User {user_id} has unblocked and restarted the bot"
                )
                with get_db_cursor() as cur:
                    cur.execute("""UPDATE light_bot.users
                                SET blocked_at = NULL
                                WHERE user_id = %s;""",
                                (user_id,)
                                )
    except Exception as error:
        logging.error(f"Error: {error}")


if __name__ == "__main__":

    if not check_env_vars():
        raise MissingEnvironmentVariableException(
            "Missing required environment variable")

    thread = threading.Thread(target=main)
    thread.daemon = True
    thread.start()

    logging.info("Starting bot polling")
    bot.infinity_polling()
