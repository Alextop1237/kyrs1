import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QTableView, QPushButton, QTabWidget, QAction, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import psycopg2
from psycopg2 import sql

class DatabaseManager:
    def __init__(self):
        self.connection = psycopg2.connect(
            host="localhost",
            port="5432",
            database="measures",
            user="postgres",
            password="student"
        )
        self.cursor = self.connection.cursor()

    def execute_query(self, query, params=None, fetch=False):
        try:
            self.cursor.execute(query, params)
            if fetch:
                return self.cursor.fetchall()
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            QMessageBox.critical(None, "Ошибка базы данных", str(e))
            return False
    
    def get_table_data(self, table_name):
        query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
        return self.execute_query(query, fetch=True)
    
    def get_columns(self, table_name):
        query = sql.SQL("SELECT column_name FROM information_schema.columns WHERE table_name = {}").format(
            sql.Literal(table_name))
        result = self.execute_query(query, fetch=True)
        return [col[0] for col in result] if result else []

    def close(self):
        self.cursor.close()
        self.connection.close()

class ReadOnlyTableTab(QWidget):
    def __init__(self, db, table_name, parent=None):
        super().__init__(parent)
        self.db = db
        self.table_name = table_name
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.model = QStandardItemModel()
        self.table_view.setModel(self.model)
        
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_data)
        
        self.layout.addWidget(self.table_view)
        self.layout.addWidget(self.refresh_btn)
    
    def load_data(self):
        data = self.db.get_table_data(self.table_name)
        columns = self.db.get_columns(self.table_name)
        
        self.model.clear()
        self.model.setHorizontalHeaderLabels(columns)
        
        if not data:
            return
        
        for row in data:
            items = []
            for value in row:
                item = QStandardItem(str(value) if value is not None else "")
                item.setEditable(False)
                items.append(item)
            self.model.appendRow(items)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Просмотр базы данных measures")
        self.setGeometry(100, 100, 800, 600)
        
        self.db = DatabaseManager()
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        tables = ['area', 'topology', 'measure', 'ticket', 'roles', 'users']
        for table in tables:
            tab = ReadOnlyTableTab(self.db, table)
            self.tab_widget.addTab(tab, table)
    
    def closeEvent(self, event):
        self.db.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())