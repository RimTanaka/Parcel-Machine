import serial
import sqlite3
import time
import telebot
from telebot import types

# Установите правильный порт для вашего Arduino
arduino_port = '/dev/ttyUSB0'  # Пример порта для Linux, на Windows это может быть что-то вроде 'COM3'

# Открытие соединения с Arduino через Serial
arduino = serial.Serial(arduino_port, 9600, timeout=1)

#Token взять из bot-father
bot = telebot.TeleBot('bot_token')

# Подключение к базе данных SQLite
conn = sqlite3.connect('postomat.db')
cursor = conn.cursor()

# Создание таблицы пользователей, если она не существует
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY, chat_id INTEGER, username TEXT, role TEXT, reserved_door INTEGER)''')
conn.commit()

# Роли пользователей
SUPER_ADMIN = "super_admin"
ADMIN = "admin"
BUYER = "buyer"

# Переменные, которые будут хранить chat_id главного администратора и список зарезервированных дверей
super_admin_chat_id = None

# Функция для отправки сообщения об ошибке
def send_error_message(message, text):
    bot.reply_to(message, f"Ошибка: {text}")

# Обработчик команды /getsuperadmin
@bot.message_handler(commands=['getsuperadmin'])
def get_super_admin(message):
    global super_admin_chat_id
    if super_admin_chat_id is None:
        super_admin_chat_id = message.chat.id
        cursor.execute('''INSERT INTO users (chat_id, username, role) VALUES (?, ?, ?)''', (message.chat.id, message.from_user.username, SUPER_ADMIN))
        conn.commit()
        bot.reply_to(message, "Вы назначены главным администратором почтомата.")
    else:
        send_error_message(message, "Главный администратор уже назначен.")

# Обработчик входящих сообщений
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    user_role = get_user_role(message.chat.id)
    if user_role == SUPER_ADMIN:
        handle_super_admin_message(message)
    elif user_role == ADMIN:
        handle_admin_message(message)
    elif user_role == BUYER:
        handle_buyer_message(message)
    else:
        send_error_message(message, "Ваша роль неопределена.")

# Обработчик сообщений главного администратора
def handle_super_admin_message(message):
    if message.text.startswith('/addadmin'):
        add_admin(message)
    elif message.text.startswith('/removeadmin'):
        remove_admin(message)
    elif message.text.startswith('/opendoor'):
        open_specific_door(message)

# Функция для удаления администратора
def remove_admin(message):
    try:
        admin_username = message.text.split()[1]
        cursor.execute('''DELETE FROM users WHERE username = ? AND role = ?''', (admin_username, ADMIN))
        conn.commit()
        bot.reply_to(message, f"Пользователь {admin_username} удален из списка администраторов.")
    except IndexError:
        send_error_message(message, "Некорректный ввод. Используйте /removeadmin @username.")

# Функция для открытия нужной ячейки
def open_specific_door(message):
    try:
        door_number = int(message.text.split()[1])
        arduino.write(f"OPEN_DOOR {door_number}\n".encode())  # Отправка команды на Arduino
        bot.reply_to(message, f"Открываю дверь {door_number}...")
    except (IndexError, ValueError):
        send_error_message(message, "Некорректный ввод. Используйте /opendoor номер_двери.")

# Функция для добавления обычного администратора
def add_admin(message):
    try:
        admin_username = message.text.split()[1]
        cursor.execute('''INSERT INTO users (chat_id, username, role) VALUES (?, ?, ?)''', (message.chat.id, admin_username, ADMIN))
        conn.commit()
        bot.reply_to(message, f"Пользователь {admin_username} назначен обычным администратором.")
    except IndexError:
        send_error_message(message, "Некорректный ввод. Используйте /addadmin @username.")

# Обработчик сообщений обычных администраторов
def handle_admin_message(message):
    if message.text.startswith('/open'):
        open_door(message)
    elif message.text.startswith('/reserve'):
        reserve_door(message)
    # Другие команды для обычных администраторов

# Обработчик сообщений покупателей
def handle_buyer_message(message):
    if message.text.startswith('/openmydoor'):
        open_reserved_door(message)
    else:
        send_error_message(message, "У вас нет прав для выполнения этой команды.")

# Код для управления почтоматом
def open_door(message):
    try:
        door_number = int(message.text.split()[1])
        arduino.write(f"OPEN_DOOR {door_number}\n".encode())  # Отправка команды на Arduino
        bot.reply_to(message, f"Открываю дверь {door_number}...")
    except (IndexError, ValueError):
        send_error_message(message, "Некорректный ввод. Используйте /open номер_двери.")

# Резервирование двери для покупателя
def reserve_door(message):
    try:
        door_number = int(message.text.split()[1])
        cursor.execute('''UPDATE users SET reserved_door = ? WHERE chat_id = ?''', (door_number, message.chat.id))
        conn.commit()
        bot.reply_to(message, f"Вы зарезервировали дверь {door_number}.")
    except (IndexError, ValueError):
        send_error_message(message, "Некорректный ввод. Используйте /reserve номер_двери.")

# Открытие зарезервированной двери для покупателя
def open_reserved_door(message):
    user_reserved_door = get_user_reserved_door(message.chat.id)
    if user_reserved_door is not None:
        arduino.write(f"OPEN_DOOR {user_reserved_door}\n".encode())  # Отправка команды на Arduino для открытия зарезервированной двери
        bot.reply_to(message, f"Открываю вашу зарезервированную дверь {user_reserved_door}...")
    else:
        send_error_message(message, "У вас не зарезервирована ни одна дверь.")

# Получение роли пользователя из базы данных
def get_user_role(chat_id):
    cursor.execute('''SELECT role FROM users WHERE chat_id = ?''', (chat_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Получение зарезервированной двери пользователя из базы данных
def get_user_reserved_door(chat_id):
    cursor.execute('''SELECT reserved_door FROM users WHERE chat_id = ?''', (chat_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Основной код бота
bot.polling()
