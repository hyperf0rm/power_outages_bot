from telebot import TeleBot
from dotenv import load_dotenv
import os
from parser import Parser
from psycopg2 import connect, pool
import logging
import sys
from exceptions import MissingEnvironmentVariableException
import time
import threading
from utils import check_env_vars
from contextlib import contextmanager

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

TOKEN = os.getenv("TOKEN")
RETRY_PERIOD = int(os.getenv("RETRY_PERIOD"))

bot = TeleBot(token=TOKEN)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout
)

try:
    db_pool = pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=3,
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

'''try:
    logging.debug("Starting connecting to the database")
    conn = connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    logging.debug("Connected to PostgreSQL successfully!")
except Error as error:
    logging.critical(f"Error connecting to PostgreSQL: {error}")'''

@contextmanager
def get_db_cursor():
    conn = db_pool.getconn()
    try:
        yield conn.cursor()
        conn.commit()
    except Exception as error:
        logging.error(f"Error in connection pool: {error}")
        conn.rollback()
        raise error
    finally:
        db_pool.putconn(conn)


@bot.message_handler(commands=["start", "info"])
def start(message):
    user_id = message.chat.id
    bot_msg = """Что умеет этот бот:\n
/add - добавить адрес. В формате: /add Бабаяна
/delete - удалить адрес.  В формате: /delete Бабаяна
/check - проверить конкретный адрес. В формате: /check Бабаяна
/show - показать ваши добавленные адреса
/my - проверить отключения по вашим адресам
/info - информация об этом боте"""

    try:
        if message.text.startswith("/start"):

            logging.info(f"Sending /start message to user {user_id}")
            query = """INSERT INTO light_bot.users (user_id)
                       VALUES (%s)
                       ON CONFLICT ON CONSTRAINT user_id_unique DO NOTHING;"""
            with get_db_cursor() as cur:
                cur.execute(query, (user_id,))

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
        bot.send_message(user_id, "Добавьте адрес вместе с командой")
        return
    address = message.text.replace("/add ", "")
    cursor = conn.cursor()
    cursor.execute("""SELECT EXISTS
                   (SELECT 1 FROM light_bot.addresses
                   WHERE user_id = %s AND address = %s);""",
                   (user_id, address))
    exists = cursor.fetchone()[0]
    if exists:
        bot_msg = f"Адрес {address} уже добавлен"
    else:
        query = """INSERT INTO light_bot.addresses (user_id, address)
                   VALUES (%s, %s);"""
        cursor.execute(query, (user_id, address))
        conn.commit()
        bot_msg = f"Добавлен адрес: {address}"
    bot.send_message(user_id, bot_msg)


@bot.message_handler(commands=["delete"])
def delete(message):
    user_id = message.chat.id
    logging.info(f"Sending /delete message to user {user_id}")
    if message.text == "/delete":
        bot.send_message(user_id, "Добавьте адрес вместе с командой")
        return
    address = message.text.replace("/delete ", "")
    cursor = conn.cursor()
    cursor.execute("""DELETE FROM light_bot.addresses
                   WHERE user_id = %s and address = %s
                   RETURNING id;""",
                   (user_id, address))
    exists = cursor.fetchall()
    conn.commit()
    if exists:
        bot_msg = f"Удален адрес: {address}"
    else:
        bot_msg = "Этот адрес не был вами добавлен"
    bot.send_message(user_id, bot_msg)


@bot.message_handler(commands=["show"])
def show(message):
    user_id = message.chat.id
    logging.info(f"Sending /show message to user {user_id}")
    cur = conn.cursor()
    query = """SELECT address FROM light_bot.addresses
               WHERE user_id = %s;"""
    cur.execute(query, (user_id,))
    addresses = [address[0] for address in cur.fetchall()]
    if addresses:
        bot_msg = "Добавленные адреса:\n\n" + "\n".join(addresses)
    else:
        bot_msg = "Вы не добавили ни один адрес"
    bot.send_message(user_id, bot_msg)


@bot.message_handler(commands=["my"])
def my(message):
    user_id = message.chat.id
    logging.info(f"Sending /my message to user {user_id}")
    cur = conn.cursor()
    query = """SELECT address FROM light_bot.addresses
               WHERE user_id = %s;"""
    cur.execute(query, (user_id,))
    addresses = [address[0] for address in cur.fetchall()]
    parser = Parser()

    outages = parser.parse_website()
    if not outages:
        logging.warning("No data fetched or empty site")

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
            "по вашим адресам в ближайшие дни")

    else:
        for i in range(len(messages_for_user)):
            new_message = "\n\n".join(messages_for_user)

    query = """SELECT last_message FROM light_bot.users
                WHERE user_id = %s;"""
    cur.execute(query, (user_id,))
    last_msg = cur.fetchone()[0]

    if new_message != last_msg:
        query = """UPDATE light_bot.users
                   SET last_message = %s
                   WHERE user_id = %s;"""
        cur.execute(query, (new_message, user_id))
        conn.commit()
    bot.send_message(user_id, new_message)


@bot.message_handler(commands=["check"])
def check(message):
    user_id = message.chat.id
    logging.info(f"Sending /check message to user {user_id}")
    if message.text == "/check":
        bot.send_message(user_id, "Добавьте адрес вместе с командой")
        return
    address = message.text.replace("/check ", "")
    parser = Parser([address])
    result = parser.parse_website()
    bot.send_message(user_id, result)


@bot.message_handler()
def msg(message):
    user_id = message.chat.id
    logging.info(f"Sending general message to user {user_id}")
    bot.send_message(user_id, "Список доступных команд: /start")


def main():
    logging.info("Starting background check")
    parser = Parser()

    while True:
        try:
            logging.info("Fetching data from website")
            outages = parser.parse_website()

            if not outages:
                logging.warning("No data fetched or empty site")
                time.sleep(RETRY_PERIOD)
                continue

            conn_bg = connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )

            cur = conn_bg.cursor()
            query = """SELECT u.user_id, u.last_message, a.address
                       FROM light_bot.users u
                       JOIN light_bot.addresses a ON u.user_id = a.user_id"""
            cur.execute(query)
            users = cur.fetchall()

            user_data = {}

            for row in users:
                uid, last_msg, address = row
                if uid not in user_data:
                    user_data[uid] = {"last_msg": last_msg, "addresses": []}
                user_data[uid]["addresses"].append(address)

            for user_id, data in user_data.items():
                logging.info(f"Checking user {user_id} addresses")
                user_addresses = data["addresses"]
                last_message = data["last_msg"]

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
                        "по вашим адресам в ближайшие дни")

                else:
                    for i in range(len(messages_for_user)):
                        new_message = "\n\n".join(messages_for_user)

                if new_message != last_message:
                    logging.info(
                        f"Starting sending main message to user {user_id}")
                    cur = conn_bg.cursor()
                    query = """UPDATE light_bot.users
                               SET last_message = %s
                               WHERE user_id = %s;"""
                    cur.execute(query, (new_message, user_id))
                    conn_bg.commit()
                    bot.send_message(user_id, new_message)

        except Exception as error:
            logging.error(f"Main loop error: {error}")

        finally:
            cur.close()
            conn_bg.close()
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":

    if not check_env_vars():
        raise MissingEnvironmentVariableException(
            "Missing required environment variable")

    thread = threading.Thread(target=main)
    thread.daemon = True
    thread.start()

    logging.info("Starting bot polling")
    bot.infinity_polling()
