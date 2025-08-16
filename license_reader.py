from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMessageBox
from PyQt6.QtGui import QImage, QPixmap
from ultralytics import YOLO
import cv2
import sqlite3
import serial
import time
from functions import get_result
import numpy as np

# ------------------ Worker Thread ------------------
class DetectionWorker(QThread):
    result_ready = pyqtSignal(object, object)  # box coords, result text, RFID

    def __init__(self, frame, model, serial_port):
        super().__init__()
        self.frame = frame
        self.model = model
        self.serial_port = serial_port
    def safe_crop(self,img, x1, y1, x2, y2):
        h, w = img.shape[:2]
        # clamp coordinates inside image bounds
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(w, int(x2))
        y2 = min(h, int(y2))
        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"Invalid crop region: ({x1}, {y1}), ({x2}, {y2})")
        crop = img[y1:y2, x1:x2]
        return np.ascontiguousarray(crop)
    
    def run(self):
        detections = self.model(self.frame)[0]
        for lpdetection in detections.boxes.data.tolist():
            x1, y1, x2, y2, conf, class_id = lpdetection
            try:
                lp_crop = self.safe_crop(self.frame, x1, y1, x2, y2)
                if lp_crop is None or lp_crop.size == 0:
                    raise ValueError(f"empty crop at {x1}, {y1}), ({x2}, {y2})")
                result = str(get_result(lp_crop))
            except Exception as e:
                print("OCR error:", e)
                result = "OCR_ERROR"
            self.result_ready.emit((x1, y1, x2, y2), result)
            break  # only handle one plate for now

# ------------------ Main GUI ------------------
class WebcamUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("License Plate Detection")
        self.setGeometry(100, 100, 800, 600)

        # Labels
        self.image_label = QLabel()
        self.image_label.setFixedSize(860, 420)
        self.result_label = QLabel("Detected plate: ...")
        self.result_label.setStyleSheet("font-size: 18px; color: green;")
        self.rfid_label = QLabel("RFID: ...")
        self.rfid_label.setStyleSheet("font-size: 18px; color: green;")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.result_label)
        layout.addWidget(self.rfid_label)
        self.setLayout(layout)


        # Frame update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # Webcam setup
        self.frame_count = 0
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        time.sleep(2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 860)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 420)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        if not self.cap.isOpened():
            print("Error: Could not open video source.")
            exit()

        # Load model
        self.license_plate_detector = YOLO('C:/.env1/license_plate_detector.pt')

        # Init DB
        self.init_db()

        # Serial port
        try:
            self.serial_port = serial.Serial('COM3', 9600, timeout=1)
        except serial.SerialException as e:
            print(f"Serial port error: {e}")
            self.serial_port = None

        self.latest_rfid = ""  
        
        # RFID reading timer
        self.rfid_timer = QTimer()
        self.rfid_timer.timeout.connect(self.read_rfid)  
        self.rfid_timer.start(200)  # read every 200ms

        # Thread worker
        self.worker = None

    def read_rfid(self):  
        """Continuously read RFID from serial and update label."""
        if self.serial_port and self.serial_port.in_waiting:
            try:
                line = self.serial_port.readline().decode('utf-8').strip()
                if line:
                    self.latest_rfid = line
                    self.rfid_label.setText(f"RFID: {line}")
                    QTimer.singleShot(8000, lambda: (self.rfid_label.setText("RFID: "), setattr(self, 'latest_rfid', "")))
            except Exception as e:
                print("RFID read error:", e)

    def update_frame(self):
        ret, frame = self.cap.read()
        self.frame_count += 1
        if not ret:
            return

        self.current_frame = frame

        # Start detection every 10 frames (about 3 fps)
        if self.frame_count % 10 == 0 and self.worker is None:
            self.worker = DetectionWorker(frame.copy(), self.license_plate_detector, self.serial_port)
            self.worker.result_ready.connect(self.handle_detection_result)
            self.worker.finished.connect(lambda: setattr(self, 'worker', None))
            self.worker.start()

        # Display frame
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.image_label.setPixmap(pixmap)

    def handle_detection_result(self, box, result):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(self.current_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

        self.result_label.setText(f"Detected plate: {str(result)}")

        if self.serial_port:
            self.check_if_in_db(str(result), self.latest_rfid)

    def init_db(self):
        try:
            self.con = sqlite3.connect('license_plate1.db')
            self.cur = self.con.cursor()
            self.cur.execute('''
                CREATE TABLE IF NOT EXISTS license_plate1 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    LicensePlate TEXT NOT NULL,
                    RFID TEXT NOT NULL
                )
            ''')
            self.cur.execute("SELECT COUNT(*) FROM license_plate1")
            if self.cur.fetchone()[0] == 0:
                self.cur.execute("INSERT INTO license_plate1 (LicensePlate, RFID) VALUES (?, ?)", ("123ABC", "213213"))
                self.con.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")

    def check_if_in_db(self, result, line):
        if not result or result in ["None", "OCR_ERROR", "[]"] or not line:
            return
        if len(result) >= 2:
            self.cur.execute("SELECT * FROM license_plate1 WHERE LicensePlate = ? AND RFID = ?", (result, line))
            if self.cur.fetchone():
                self.serial_port.write(b'y')
            else:
                reply = QMessageBox.question(
                    self,
                    "Confirm Action",
                    "Do you want to save this ID?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.cur.execute('INSERT INTO license_plate1 (LicensePlate, RFID) VALUES (?, ?)', (str(result), str(line)))
                    self.con.commit()
        
            

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        if self.con:
            self.cur.close()
            self.con.close()
        event.accept()
