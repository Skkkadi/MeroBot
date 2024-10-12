import threading
import sqlite3

# Функция добавления нового пользователя в БД
def commands():
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

input_thread = threading.Thread(target=commands)
input_thread.daemon = True
input_thread.start()