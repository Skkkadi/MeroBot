print('====================\nЗапуск бота')

import config
from db_creation import *
from SMM_texts import *
import threading
import telebot
from telebot import types

bot = telebot.TeleBot(config.TOKEN)


# Функция проверяющая права пользователя
def check_permissions(username):
    try:
        info = cur.execute('SELECT * FROM users WHERE username=? AND permission="user"', (f'@{username}',))
        if info.fetchone() is not None:
            return 1  # Пользователь имеет права участника
        else:
            info = cur.execute('SELECT * FROM users WHERE username=? AND permission="admin"', (f'@{username}',))
            if info.fetchone() is not None:
                return 2  # Пользователь имеет права организатора
            else:
                info = cur.execute('SELECT * FROM users WHERE username=? AND permission="curator"', (f'@{username}',))
                if info.fetchone() is not None:
                    return 3  # Пользователь имеет права куратора
                else:
                    return 0  # Пользователя нет в БД
    except Exception as e:
        print('Непредвиденная ошибка при попытке узнать права пользователя:')
        print(e)


# Функция добавления нового пользователя в БД
def add_user():
    while True:
        command = input()
        if command == 'adduser':
            username = input('Введите имя пользователя (с @): ')
            permission = input('Введите разрешения (user/curator/admin): ')
            try:
                team = int(input('Введите номер команды (для участника): '))
            except:
                team = None
            try:
                station = int(input('Введите номер станции (для куратора): '))
            except:
                station = None
            try:
                chat_id = int(input('Введите Chat ID пользователя (если известен): '))
            except:
                chat_id = None
            params = (None, username, permission, team, station, chat_id)
            if input('Вы уверены? [y/n]: ') == 'y':
                cur.execute('DELETE FROM users WHERE username=?', (username,))
                cur.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)', params)
                conn.commit()
                cur.execute('SELECT * FROM users WHERE username=?', (username,))
                check = cur.fetchone()
                print(f'В БД добавлена новая запись: {check}')
            else:
                print('Добавление отменено')
        elif command == 'deleteuser':
            username = input('Введите имя пользователя (с @): ')
            if input('Вы уверены? [y/n] ') == 'y':
                try:
                    cur.execute('DELETE FROM users WHERE username=?', (username,))
                    conn.commit()
                    print(f'Пользователь {username} успешно удален из БД')
                except Exception as e:
                    print('Ошибка при удалении пользователя:')
                    print(e)
            else:
                print('Удаление отменено')
        elif command == 'printdb':
            try:
                print_db('users')
            except Exception as e:
                print('Ошибка при выводе БД:')
                print(e)
        else:
            print('Некорректная команда')


# Функция отправки списка участников команды
def send_team(user_chatid):
    try:
        cur.execute(f'SELECT team FROM users WHERE chatid={user_chatid}')
        user_team = cur.fetchone()

        if user_team is None:
            bot.send_message(user_chatid, 'Похоже, что организаторы забыли добавить тебя в команду '
                                          'ты можешь обратиться к ним за помощью', parse_mode='html')
        else:
            c = conn.cursor()
            c.row_factory = lambda cursor, row: row[0]
            c.execute(f'SELECT username FROM users WHERE team={user_team[0]}')
            team_list = c.fetchall()

            bot.send_message(user_chatid, f'{team_list_text}\n\n' + '\n'.join(team_list), parse_mode='html')
    except Exception as e:
        print('Непредвиденная ошибка при отправке списка команды:')
        print(e)


# Функция отправки участнику изображения карты (и команды)
def send_map(user_chatid):
    try:
        cur.execute(f'SELECT team FROM users WHERE chatid={user_chatid}')
        user_team = cur.fetchone()

        if user_team is None:
            return

        try:
            map_image = open(f'./files/{int(user_team[0])}.{config.map_extension}', 'rb')
        except FileNotFoundError:
            bot.send_message(user_chatid, 'Похоже что организаторы не добавили карту для твоей команды, '
                                          'ты можешь обратиться к ним за помощью')
            print(f'Команда {int(user_team[0])} не получила карту')
        else:
            try:
                team_image = open(f'./files/team{int(user_team[0])}.{config.teams_extension}', 'rb')
            except:
                bot.send_message(user_chatid, 'Похоже что организаторы не добавили изображение команды '
                                              'для твоей команды, ты можешь обратиться к ним за помощью')
                print(f'Команда {int(user_team[0])} не получила изображение с командой')
            else:
                bot.send_media_group(user_chatid, [
                    telebot.types.InputMediaPhoto(map_image, caption=map_caption_text, parse_mode='html'),
                    telebot.types.InputMediaPhoto(team_image)
                ])
                map_image.close()
                team_image.close()
    except Exception as e:
        print('Непредвиденная ошибка при отправке карты:')
        print(e)


# Функция приема письма от участника
def gain_letter(user_chatid, username):
    try:
        bot.send_message(user_chatid, message_before_gain_letter, parse_mode='html')

        def receive_letter(message):
            if message.chat.id == user_chatid:
                letter_text = message.text
                file = open(f'./letters/Letter from {username}.txt', 'w', encoding='utf-8')
                file.write(letter_text)
                file.close()
                bot.send_message(user_chatid, message_after_gain_letter, parse_mode='html')
                bot.delete_message(message.chat.id, message.message_id)
                print(f'Получено письмо от пользователя {username}')

        bot.register_next_step_handler_by_chat_id(user_chatid, receive_letter)
    except Exception as e:
        print('Непредвиденная ошибка при получении письма:')
        print(e)


# Отправление клавиатуры куратору
def send_curator_keyboard(chatid):
    try:
        cur.execute(f'SELECT station FROM users WHERE chatid={chatid}')
        curator_station = cur.fetchone()

        keyboard = types.InlineKeyboardMarkup(row_width=4)
        buttons = [types.InlineKeyboardButton(str(i), callback_data=f"team_{i}") for i in
                   range(1, config.team_quantity + 1)]
        keyboard.add(*buttons)

        bot.send_message(chatid, curator_keyboard_message, reply_markup=keyboard, parse_mode='html')
    except Exception as e:
        print('Непредвиденная ошибка при отправке клавиатуры куратору:')
        print(e)


# Команда /start, регистрирует пользователя, записывая его chatid в БД и уведомляет о правах
@bot.message_handler(commands=['start'])
def welcome(message):
    # Внесение ID чата пользователя в БД
    try:
        cur.execute(f'UPDATE users SET chatid={message.chat.id} WHERE username="@{message.from_user.username}"')
        conn.commit()
        print(f'Данные БД обновлены: добавлен chatid = {message.chat.id} у пользователя @{message.from_user.username}')
    except Exception as e:
        print('Ошибка при регистрации:')
        print(e)
    # Проверка разрешений пользователя
    user_permissions = check_permissions(message.from_user.username)
    if user_permissions == 1:  # Если пользователь является участником
        bot.send_message(message.chat.id, welcome_message_for_user, parse_mode='html')
    elif user_permissions == 2:  # Если пользователь является организатором
        bot.send_message(message.chat.id, welcome_message_for_admin, parse_mode='html')
    elif user_permissions == 3:  # Если пользователь является куратором
        bot.send_message(message.chat.id, welcome_message_for_curator, parse_mode='html')
        cur.execute(f'SELECT station FROM users WHERE chatid={message.chat.id}')
        curator_station = cur.fetchone()
        if curator_station is None:
            bot.send_message(message.chat.id, 'Похоже что ты не закреплен за станцией, '
                                              'ты можешь обратиться к организаторам за помощью')
        else:
            bot.send_message(message.chat.id, f'Твоя станция: {int(curator_station[0])}', parse_mode='html')
    else:  # Если его нет в БД
        bot.send_message(message.chat.id, welcome_message_for_unknown, parse_mode='html')


# Команда /startmero, запускает рассылку и уведомляет пользователя о его команде и начале мероприятия
@bot.message_handler(commands=['startmero'])
def startmero(message):
    if check_permissions(message.from_user.username) == 2:
        print(f'Была запущена рассылка организатором {message.from_user.username}')

        # Оповещает других организаторов
        bot.send_message(message.chat.id, 'Оповещаю других организаторов')
        unregistered_users = 0
        cur.execute('SELECT chatid FROM users WHERE permission="admin"')
        chatids = cur.fetchall()
        for chat in chatids:
            cur.execute(f'SELECT username FROM users WHERE chatid="{chat[0]}"')
            this_user = cur.fetchone()
            if chat[0] is None:
                unregistered_users += 1
                continue
            else:
                bot.send_message(chat[0], f'Организатором @{message.from_user.username} было начато мероприятие')
        else:
            bot.send_message(message.chat.id, 'Все организаторы оповещены')
            if unregistered_users != 0:
                bot.send_message(message.chat.id, f'<u><b>{unregistered_users} организаторов не '
                                                  f'получили сообщения</b></u>', parse_mode='html')

        # Рассылка участникам
        bot.send_message(message.chat.id, 'Начинаю рассылку участникам')
        unregistered_users = 0
        cur.execute('SELECT chatid FROM users WHERE permission="user"')
        chatids = cur.fetchall()
        # try:
        #    video = open(f'./files/{config.video_filename}', 'rb')
        # except Exception as e:
        #    print('Ошибка при открытии видео:')
        #    print(e)
        for chat in chatids:
            cur.execute(f'SELECT username FROM users WHERE chatid="{chat[0]}"')
            this_user = cur.fetchone()
            if chat[0] is None:
                unregistered_users += 1
                continue
            else:
                # Отправляет уведомление о начале мероприятия
                bot.send_message(int(chat[0]), mero_start_text, parse_mode='html')
                # Отправляет список участников команды пользователя
                send_team(int(chat[0]))
                # Отправляет карту, по которой следует команда
                send_map(int(chat[0]))
                # Отправляет видео
                # try:
                #    bot.send_video(int(chat[0]), video, timeout=120)
                # except:
                #    pass
        else:
            bot.send_message(message.chat.id, 'Участники получили сообщения')
            if unregistered_users != 0:
                bot.send_message(message.chat.id, f'<u><b>{unregistered_users} пользователей не '
                                                  f'получили сообщения</b></u>', parse_mode='html')

        # Отправляет клавиатуру с командами кураторам
        bot.send_message(message.chat.id, 'Начинаю рассылку кураторам станций')
        unregistered_users = 0
        cur.execute('SELECT chatid FROM users WHERE permission="curator"')
        chatids = cur.fetchall()
        for chat in chatids:
            cur.execute(f'SELECT username FROM users WHERE chatid="{chat[0]}"')
            this_user = cur.fetchone()
            if chat[0] is None:
                unregistered_users += 1
                continue
            else:
                send_curator_keyboard(int(chat[0]))
        else:
            bot.send_message(message.chat.id, 'Кураторы получили клавиатуру с командами')
            if unregistered_users != 0:
                bot.send_message(message.chat.id, f'<u><b>{unregistered_users} пользователей не '
                                                  f'получили сообщения</b></u>', parse_mode='html')
        bot.send_message(message.chat.id, '<b>Рассылка окончена!</b>', parse_mode='html')
        # video.close()

    else:
        bot.send_message(message.chat.id, 'У тебя нет прав организатора для этого')
        print(f'Пользователь {message.from_user.username} попытался начать мероприятие, откуда он знает команду?')


# Команда /startletters начинает прием писем от участников
@bot.message_handler(commands=['startletters'])
def adduser(message):
    if check_permissions(message.from_user.username) == 2:
        print(f'Был запущен прием писем организатором {message.from_user.username}')
        # Оповещает других организаторов
        bot.send_message(message.chat.id, 'Оповещаю других организаторов')
        unregistered_users = 0
        cur.execute('SELECT chatid FROM users WHERE permission="admin"')
        chatids = cur.fetchall()
        for chat in chatids:
            cur.execute(f'SELECT username FROM users WHERE chatid="{chat[0]}"')
            this_user = cur.fetchone()
            if chat[0] is None:
                unregistered_users += 1
                continue
            else:
                bot.send_message(chat[0], f'Организатором {message.from_user.username} был начат '
                                          f'прием писем')
        else:
            bot.send_message(message.chat.id, 'Все организаторы оповещены')
            if unregistered_users != 0:
                bot.send_message(message.chat.id, f'<u><b>{unregistered_users} организаторов не '
                                                  f'получили сообщения</b></u>', parse_mode='html')

        bot.send_message(message.chat.id, 'Начинаю рассылку участникам')
        unregistered_users = 0
        cur.execute('SELECT chatid FROM users WHERE permission="user"')
        chatids = cur.fetchall()
        for chat in chatids:
            cur.execute(f'SELECT username FROM users WHERE chatid="{chat[0]}"')
            this_user = cur.fetchone()
            if chat[0] == None:
                unregistered_users += 1
                continue
            else:
                # Выполняет прием письма
                gain_letter(int(chat[0]), this_user[0])
        else:
            bot.send_message(message.chat.id, 'Рассылка окончена, зарегистрированные '
                                              ' пользователи получили сообщение')
            if unregistered_users != 0:
                bot.send_message(message.chat.id, f'<u><b>{unregistered_users} участников не '
                                                  f'получили сообщение</b></u>', parse_mode='html')
    else:
        bot.send_message(message.chat.id, 'У тебя нет прав организатора для этого')
        print(f'Пользователь {message.from_user.username} попытался начать прием писем, откуда он знает команду?')


# Обработчик нажатия на кнопки из клавиатуры куратора
@bot.callback_query_handler(func=lambda call: call.data.startswith('team_'))
def handle_team_button(call):
    try:
        cur.execute(f'SELECT station FROM users WHERE chatid={call.message.chat.id}')
        curator_station = cur.fetchone()
        station_number = int(curator_station[0])
        team_number = call.data.split('_')[1]

        # Отправляет оповещение организаторам
        cur.execute('SELECT chatid FROM users WHERE permission="admin"')
        chatids = cur.fetchall()
        for chat in chatids:
            if chat[0] == None:
                continue
            else:
                bot.send_message(int(chat[0]), f"Команда {team_number} прошла через станцию {station_number}")
        bot.send_message(call.message.chat.id, f'Сообщение о команде {team_number} отправлено организаторам')
        print(f"Команда {team_number} была зарегистрирована на станции {station_number}")
    except Exception as e:
        print('Непредвиденная ошибка при отправлении уведомления от куратора:')
        print(e)


input_thread = threading.Thread(target=add_user)
input_thread.daemon = True
input_thread.start()

print('Бот запущен\n====================')
bot.polling(none_stop=True)
