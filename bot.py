from telebot import TeleBot
from dotenv import load_dotenv
import os
from parser import Parser
from psycopg2 import connect, Error

load_dotenv()

token = os.getenv("TOKEN")
bot = TeleBot(token=token)

host = os.getenv("HOST")
db = os.getenv("DATABASE")
user = os.getenv("USER")
password = os.getenv("PASSWORD")

try:
    conn = connect(
        host=host,
        database=db,
        user=user,
        password=password
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
    if cursor.rowcount == 1:
        bot.send_message(user_id, "Бот активирован")


@bot.message_handler(commands=["add"])
def add(message):
    user_id = message.chat.id
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

@bot.message_handler(commands=["check"])
def check(message):
    user_id = message.chat.id
    "checks if address is fucked in the next few days"
    pass

@bot.message_handler()
def parse(message):
    user_id = message.chat.id
    address = message.text
    parser = Parser(address)
    result = parser.parse_website()
    bot.send_message(user_id, text=result)


bot.infinity_polling()
