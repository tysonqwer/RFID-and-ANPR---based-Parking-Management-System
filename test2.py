import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import Qt
import sqlite3
from license_reader import WebcamUI

class LoginApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login Application")
        self.setFixedSize(400, 300)
        self.rfid_window = None
        # Initialize database
        self.init_db()
        
        # Create main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout()
        self.main_widget.setLayout(self.layout)
        
        # Add title
        self.title_label = QLabel("Login")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        self.layout.addWidget(self.title_label)
        
        # Username field
        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)
        
        # Password field
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)
        
        # Buttons layout
        self.buttons_layout = QHBoxLayout()
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)
        self.buttons_layout.addWidget(self.login_button)
        
        # Register button
        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self.handle_register)
        self.buttons_layout.addWidget(self.register_button)
        
        self.layout.addLayout(self.buttons_layout)
        
        # Add some spacing
        self.layout.addSpacing(20)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.status_label)
    
    def init_db(self):
        """Initialize the database with a users table if it doesn't exist"""
        self.conn = sqlite3.connect('users.db')
        self.cursor = self.conn.cursor()
        
        # Create table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        self.conn.commit()
        
        self.cursor.execute("SELECT COUNT(*) FROM users")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                              ("admin", "admin123"))
            self.conn.commit()
    
    def handle_login(self):
        """Handle login button click"""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return
        
        self.cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                          (username, password))
        user = self.cursor.fetchone()
        
        if user:
            self.opencv_window = WebcamUI()
            self.opencv_window.show()
            self.hide()
        else:
            QMessageBox.warning(self, "Login Failed", 
                              "Invalid username or password")
            self.status_label.setText("Login failed")
    
    def handle_register(self):
        """Handle register button click"""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            self.status_label.setText("Please enter both username and password")
            return
        
        try:
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                               (username, password))
            self.conn.commit()
            QMessageBox.information(self, "Registration Successful", 
                                  "Account created successfully!")
            self.status_label.setText("Registration successful")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Registration Failed", 
                              "Username already exists")
            self.status_label.setText("Registration failed - username exists")
    
    def closeEvent(self, event):
        """Close database connection when application closes"""
        self.conn.close()
        self.cursor.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_app = LoginApp()
    login_app.show()
    sys.exit(app.exec())
