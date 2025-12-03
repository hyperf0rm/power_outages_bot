from telebot import TeleBot
from dotenv import load_dotenv
import os
from parser import Parser
from psycopg2 import connect, Error
import logging
import sys
from exceptions import MissingEnvironmentVariableException

load_dotenv()

TOKEN = os.getenv("TOKEN")

RETRY_PERIOD = os.getenv("RETRY_PERIOD")

DB_HOST = os.getenv("DB_HOST")
DB = os.getenv("DATABASE")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def check_env_vars():
    """Check environment variables existence."""
    env_variables = {
        "TELEGRAM_TOKEN": TOKEN,
        "RETRY_PERIOD": RETRY_PERIOD,
        "DB_HOST": DB_HOST,
        "DATABASE": DB,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD
    }
    
    var_found = True

    for var_name, var in env_variables.items():
        if not var:
            logging.critical(f'Missing required environment variable: {var_name}. Bot stopped.')
            var_found = False
    return var_found


try:
    conn = connect(
        host=DB_HOST,
        database=DB,
        user=DB_USER,
        password=DB
    )
    print("Connected to PostgreSQL successfully!")
except Error as e:
    print(f"Error connecting to PostgreSQL: {e}")


@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    query = """INSERT INTO light_bot.users (user_id)
               VALUES (%s)
               ON CONFLICT ON CONSTRAINT user_id_unique DO NOTHING;"""
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    conn.commit()
    # if cursor.rowcount == 1:
    bot_msg = """Что умеет этот бот:\n
    /add - добавить адрес\n
    /delete - удалить адрес\n
    /show - показать ваши добавленные адреса\n
    /my - проверить отключения по вашим адресам\n
    /check - проверить конкретный адрес\n
    /start - информация об этом боте"""
    bot.send_message(user_id, bot_msg)


@bot.message_handler(commands=["add"])
def add(message):
    user_id = message.chat.id
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
    cur = conn.cursor()
    query = """SELECT address FROM light_bot.addresses
               WHERE user_id = %s;"""
    cur.execute(query, (user_id,))
    addresses = cur.fetchall()
    if addresses:
        list = [address[0] for address in addresses]
        bot_msg = "Добавленные адреса:\n" + "\n".join(list)
    else:
        bot_msg = "Вы не добавили ни один адрес"
    bot.send_message(user_id, bot_msg)


@bot.message_handler(commands=["my"])
def check(message):
    user_id = message.chat.id
    cur = conn.cursor()
    query = """SELECT address FROM light_bot.addresses
               WHERE user_id = %s;"""
    cur.execute(query, (user_id,))
    addresses = cur.fetchall()
    list = [address[0] for address in addresses]
    parser = Parser(list)
    result = parser.parse_website()
    bot.send_message(user_id, result)


@bot.message_handler(commands=["check"])
def parse(message):
    user_id = message.chat.id
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
    bot.send_message(user_id, "Список доступных команд: /start")

def main():


    


bot.infinity_polling()
