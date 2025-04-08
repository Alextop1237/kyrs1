import sqlite3

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# Создаём таблицу пользователей
users=('''
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    FOREIGN KEY(role_id) REFERENCES Roles(id)
    FOREIGN KEY(status_id) REFERENCES Status(id)
)
''')


history=("""
CREATE TABLE IF NOT EXISTS History (
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER NOT NULL,
encrypt_id INTEGER NOT NULL,
before TEXT NOT NULL,
after TEXT NOT NULL,   
FOREIGN KEY(encrypt_id) REFERENCES Encrypts(id),    
FOREIGN KEY(user_id) REFERENCES Users(id)
)
""")

all_encrypt=("""
CREATE TABLE IF NOT EXISTS Encrypts(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL
)
""")



cursor.execute('''CREATE TABLE IF NOT EXISTS Roles
               (id INTEGER PRIMARY KEY,
               name TEXT NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Status
               (id INTEGER PRIMARY KEY,
               name TEXT NOT NULL)''')

cursor.execute("INSERT INTO Roles (name) VALUES ('Админ')")
cursor.execute("INSERT INTO Roles (name) VALUES ('Пользователь')")
cursor.execute("INSERT INTO Status (name) VALUES ('Активен')")
cursor.execute("INSERT INTO Status (name) VALUES ('Заморожен')")


# Добавляем тестового пользователя
cursor.execute(users)

users_sql="""INSERT INTO users (name, login, password, role_id, status_id) 
VALUES 
('bf', '1', '3', 1, 1),
('ty', '2', '4', 2, 1)
"""
cursor.execute(all_encrypt)
cursor.execute(history)
cursor.execute(users_sql)
cursor.execute("INSERT INTO Encrypts (name) VALUES ('hex')")
cursor.execute("INSERT INTO Encrypts (name) VALUES ('ascii')")
cursor.execute("INSERT INTO Encrypts (name) VALUES ('cesar')")
cursor.execute("INSERT INTO History (user_id, encrypt_id, before, after) VALUES (1, 1, 'gg', 'hh')")
conn.commit()
conn.close()