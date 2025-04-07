import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTableView, QPushButton, QTabWidget, QLabel, QLineEdit, 
                             QDateEdit, QComboBox, QMessageBox, QFormLayout, QDialog)
from PyQt5.QtCore import Qt, QDate
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
    
    def insert_record(self, table_name, data):
        columns = self.get_columns(table_name)
        if not columns:
            return False
        
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(map(sql.Identifier, columns[1:])),
            sql.SQL(', ').join(sql.Placeholder() * (len(columns)-1))
        )
        return self.execute_query(query, data)
    
    def update_record(self, table_name, record_id, data):
        columns = self.get_columns(table_name)
        if not columns or len(columns[1:]) != len(data):
            return False
        
        set_clause = sql.SQL(', ').join(
            sql.SQL("{} = {}").format(sql.Identifier(col), sql.Placeholder())
            for col in columns[1:]
        )
        query = sql.SQL("UPDATE {} SET {} WHERE id = {}").format(
            sql.Identifier(table_name),
            set_clause,
            sql.Literal(record_id)
        )
        return self.execute_query(query, data)
    
    def delete_record(self, table_name, record_id):
        query = sql.SQL("DELETE FROM {} WHERE id = {}").format(
            sql.Identifier(table_name),
            sql.Literal(record_id)
        )
        return self.execute_query(query)
    
    def get_foreign_keys(self, table_name):
        query = """
        SELECT 
            tc.constraint_name, 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE 
            tc.constraint_type = 'FOREIGN KEY' AND 
            tc.table_name = %s
        """
        return self.execute_query(query, (table_name,), fetch=True)
    
    def get_referenced_data(self, table_name, column_name):
        if table_name == 'roles':
            query = sql.SQL("SELECT id, user_role FROM {}").format(sql.Identifier(table_name))
        else:
            query = sql.SQL("SELECT id, name FROM {}").format(sql.Identifier(table_name))
        result = self.execute_query(query, fetch=True)
        return {str(row[0]): row[1] for row in result} if result else {}

    def close(self):
        self.cursor.close()
        self.connection.close()

class EditDialog(QDialog):
    def __init__(self, db, table_name, record=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.table_name = table_name
        self.record = record
        self.setWindowTitle(f"Редактирование {table_name}")
        self.setModal(True)
        
        self.layout = QFormLayout(self)
        self.fields = {}
        self.setup_ui()
    
    def setup_ui(self):
        columns = self.db.get_columns(self.table_name)
        if not columns:
            return
        
        foreign_keys = {fk[2]: (fk[3], fk[4]) for fk in self.db.get_foreign_keys(self.table_name)}
        
        for i, column in enumerate(columns[1:]):
            if column in foreign_keys:
                ref_table, ref_column = foreign_keys[column]
                data = self.db.get_referenced_data(ref_table, ref_column)
                combo = QComboBox()
                combo.addItem("", None)
                for id_val, name in data.items():
                    combo.addItem(name, id_val)
                self.fields[column] = combo
                self.layout.addRow(column, combo)
                
                if self.record and self.record[i+1]:
                    index = combo.findData(str(self.record[i+1]))
                    if index >= 0:
                        combo.setCurrentIndex(index)
            else:
                if column.lower() == 'date':
                    field = QDateEdit()
                    field.setCalendarPopup(True)
                    if self.record and self.record[i+1]:
                        field.setDate(QDate.fromString(self.record[i+1].strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                else:
                    field = QLineEdit()
                    if self.record and self.record[i+1]:
                        field.setText(str(self.record[i+1]))
                self.fields[column] = field
                self.layout.addRow(column, field)
        
        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        
        self.layout.addRow(buttons)
    
    def get_data(self):
        data = []
        for column, field in self.fields.items():
            if isinstance(field, QComboBox):
                value = field.currentData()
            elif isinstance(field, QDateEdit):
                value = field.date().toString("yyyy-MM-dd")
            else:
                value = field.text()
            data.append(value)
        return data

class ReadOnlyTableTab(QWidget):
    """Вкладка только для просмотра данных"""
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

class EditableTableTab(QWidget):
    """Вкладка с возможностью редактирования"""
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
        
        buttons = QHBoxLayout()
        
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_record)
        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.clicked.connect(self.edit_record)
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_record)
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_data)
        
        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.edit_btn)
        buttons.addWidget(self.delete_btn)
        buttons.addWidget(self.refresh_btn)
        
        self.layout.addWidget(self.table_view)
        self.layout.addLayout(buttons)
    
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
    
    def get_selected_row_id(self):
        selection = self.table_view.selectionModel()
        if not selection.hasSelection():
            return None
        return self.model.item(selection.selectedRows()[0].row(), 0).text()
    
    def add_record(self):
        dialog = EditDialog(self.db, self.table_name)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if self.db.insert_record(self.table_name, data):
                self.load_data()
    
    def edit_record(self):
        record_id = self.get_selected_row_id()
        if not record_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для редактирования")
            return
        
        row = self.table_view.selectionModel().selectedRows()[0].row()
        record_data = [self.model.item(row, col).text() for col in range(self.model.columnCount())]
        
        dialog = EditDialog(self.db, self.table_name, record_data)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            if self.db.update_record(self.table_name, record_id, new_data):
                self.load_data()
    
    def delete_record(self):
        record_id = self.get_selected_row_id()
        if not record_id:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления")
            return
        
        reply = QMessageBox.question(
            self, 'Подтверждение', 
            f'Вы уверены, что хотите удалить запись с ID {record_id}?', 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_record(self.table_name, record_id):
                self.load_data()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление базой данных measures")
        self.setGeometry(100, 100, 800, 600)
        
        self.db = DatabaseManager()
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Создаем вкладки
        tables = ['area', 'topology', 'measure', 'ticket', 'roles', 'users']
        for table in tables:
            if table == 'measure':
                # Только для measures делаем редактируемую вкладку
                tab = EditableTableTab(self.db, table)
            else:
                # Для остальных таблиц - только просмотр
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