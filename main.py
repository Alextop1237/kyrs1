import sys
import sqlite3
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

class AuthApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Инициализация базы данных
        self.conn = sqlite3.connect('data.db')
        self.cursor = self.conn.cursor()

    def initUI(self):
        self.setWindowTitle('Авторизация')

        layout = QVBoxLayout()

        # Поле для логина
        self.username_label = QLabel('Логин:')
        self.username_input = QLineEdit()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)

        # Поле для пароля
        self.password_label = QLabel('Пароль:')
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        # Кнопка для авторизации
        self.login_button = QPushButton('Войти')
        self.login_button.clicked.connect(self.authenticate)
        self.login_button.setObjectName("login")
        layout.addWidget(self.login_button)

        self.exit_button = QPushButton('Выход')
        self.exit_button.clicked.connect(self.open_change_window)
        self.exit_button.setObjectName("exit")
        layout.addWidget(self.exit_button)
    
        self.setLayout(layout)

        # with open("style.css", "r") as style:
        #     style2 = style.read()
        #     self.setStyleSheet(style2)


    def authenticate(self):
        self.ua = ua()
        login = self.username_input.text()
        password = self.password_input.text()


        # Проверка логина и пароля в базе данных
        self.cursor.execute("SELECT * FROM users WHERE login=? AND password=?", (login, password))
        result = self.cursor.fetchone()

        # Проверка результата
        if result:
            user = result
            role_id = user[4]  # Предполагаем, что role_id находится в 5-ом столбце
            status = user[5]  # Предполагаем, что статус находится в 6-ом столбце
            id = user[0]

            if status == 1:  # Статус активен
                if role_id == 1:
                    self.close()
                    self.ua.show()
                elif role_id == 2:
                    self.change = ch(id)
                    self.close()
                    self.change.show()
            elif status == 2:  # Статус заморожен
                    if role_id == 1:
                        QMessageBox.warning(self, 'Возникла ошибка', 'Админ был заморожен')
                    elif role_id == 2:
                        QMessageBox.warning(self, 'Возникла ошибка', 'Пользователь был заморожен')
        else:
            QMessageBox.warning(self, 'Возникла ошибка', 'Неверный логин или пароль')
        

    def closeEvent(self, event):
        self.conn.close()  # Закрываем соединение с БД при выходе


    def open_change_window(self):        
        msg = QMessageBox(self)
        msg.setWindowTitle("Выход")
        msg.setIcon(QMessageBox.Question)
        msg.setText("Вы действительно хотите выйти ?")

        buttonAceptar  = msg.addButton("Да, хочу", QMessageBox.YesRole)    
        buttonCancelar = msg.addButton("Отменить", QMessageBox.RejectRole) 
        msg.setDefaultButton(buttonAceptar)
        msg.exec_()

        if msg.clickedButton() == buttonAceptar:
            self.close()
        elif msg.clickedButton() == buttonCancelar:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AuthApp()
    ex.resize(300, 200)
    ex.show()
    sys.exit(app.exec_())