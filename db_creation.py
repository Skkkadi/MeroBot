import sqlite3
import pandas as pd

# Подключение к БД
conn = sqlite3.connect('users.db', check_same_thread=False)
cur = conn.cursor()

# Создание таблицы
cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username TEXT NOT NULL,
                permission TEXT NOT NULL,
                team INT,
                station INT,
                chatid INT
            )""")
conn.commit()


# Функция вывода содержимого таблицы
def print_db(db_name):
    cur.execute(f'SELECT * FROM {db_name}')
    users = cur.fetchall()
    print('====================\nСодержимое БД:')
    for user in users:
        print(user)
    print('====================')


# Функция для заполнения таблицы
def parse_excel(path):
    df = pd.read_excel(path, sheet_name='Лист1')
    df.to_sql('users', conn, if_exists='replace', index=False)
    conn.commit()
    print('Данные в БД обновлены')


if input('====================\nОбновить БД? Записи о чатах участников будут потеряны'
         ' и им придется регистрироваться повторно [y/n]: ') == 'y':
    parse_excel('users.xlsx')
else:
    print('Обновление БД пропущено')

print_db('users')
