import sys
import json
import cv2
import os
from ultralytics import YOLO
import numpy as np

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
                             QDesktopWidget, QLineEdit, QFileDialog, QLabel)
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QPixmap
from PyQt5.QtCore import QRect, Qt, QTimer

# 노래 데이터를 저장할 변수
song_data = None

# JSON 파일 로드 함수
def load_song_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

# PyQt5 통합된 창 (웹캠과 가상 키보드)
class CombinedWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Webcam and Virtual Keyboard")
        self.setGeometry(150, 150, 1000, 600)

        # YOLO 모델 로드
        self.model = YOLO("./test_files/best_1_1680.pt")
        self.detected_note = None  # YOLO로 감지된 음표를 저장할 변수

        # 중앙 위젯과 레이아웃 설정
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # 웹캠 레이아웃
        self.webcam_layout = QVBoxLayout()
        self.webcam_label = QLabel(self)
        self.webcam_label.setFixedSize(640, 480)
        self.webcam_layout.addWidget(self.webcam_label)
        self.webcam_layout.setAlignment(Qt.AlignCenter)
        self.layout.addLayout(self.webcam_layout)

        # OpenCV 캡처 초기화
        self.cap = cv2.VideoCapture(0)

        # QTimer로 프레임 업데이트
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # 가상 키보드 추가
        self.keyboard_view = KeyboardView(self)
        self.layout.addWidget(self.keyboard_view)

        # JSON 파일 선택 버튼 추가
        self.load_button = QPushButton("Load JSON File", self)
        self.load_button.clicked.connect(self.load_json_file)
        self.layout.addWidget(self.load_button)

        # 검출된 음표 표시 레이블
        self.detected_label = QLabel("Detected Note: None", self)
        self.layout.addWidget(self.detected_label)

        # JSON 데이터 실행 버튼 추가
        self.play_button = QPushButton("Play Notes", self)
        self.play_button.clicked.connect(self.play_notes_from_json)
        self.layout.addWidget(self.play_button)

        # 종료 버튼 추가
        self.exit_button = QPushButton("Exit", self)
        self.exit_button.clicked.connect(self.close)
        self.layout.addWidget(self.exit_button)

        self.note_index = 0  # 현재 계이름의 인덱스
        self.timer_notes = QTimer(self)
        self.timer_notes.timeout.connect(self.play_next_note)
        self.is_note_correct = False

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # YOLO로 객체 감지 수행
            results = self.model(frame)
            
            # YOLO 결과 처리
            if len(results) > 0 and len(results[0].boxes) > 0:
                # 가장 높은 confidence를 가진 결과 선택
                confidence = results[0].boxes.conf.cpu().numpy()
                if len(confidence) > 0:
                    max_conf_idx = np.argmax(confidence)
                    class_id = results[0].boxes.cls[max_conf_idx].item()
                    detected_note = results[0].names[int(class_id)]
                    
                    # 감지된 음표가 변경되었을 때만 업데이트
                    if self.detected_note != detected_note:
                        self.detected_note = detected_note
                        self.detected_label.setText(f"Detected Note: {detected_note}")
                        self.check_detected_note()

            # 프레임 표시
            annotated_frame = results[0].plot()
            annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            height, width, channel = annotated_frame.shape
            qt_image = QImage(annotated_frame.data, width, height, width * channel, QImage.Format_RGB888)
            self.webcam_label.setPixmap(QPixmap.fromImage(qt_image))

    def check_detected_note(self):
        if not song_data or self.detected_note is None:
            return

        correct_note = song_data["song"][self.note_index]["note"]

        if self.detected_note == correct_note:
            self.is_note_correct = True
            self.note_index += 1
            self.keyboard_view.reset_highlighted_keys()

            if self.note_index < len(song_data["song"]):
                next_note = song_data["song"][self.note_index]["note"]
                self.keyboard_view.highlight_key(next_note, "blue")
            else:
                self.detected_label.setText("All notes played!")
        else:
            self.is_note_correct = False

    def load_json_file(self):
        global song_data
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)", options=options)
        if file_path:
            song_data = load_song_data(file_path)

    def play_notes_from_json(self):
        if not song_data:
            return
        self.note_index = 0
        self.detected_note = None
        self.timer_notes.start(1500)

    def play_next_note(self):
        global song_data
        if self.note_index < len(song_data["song"]):
            note_data = song_data["song"][self.note_index]
            note = note_data["note"]

            self.keyboard_view.reset_highlighted_keys()
            self.keyboard_view.highlight_key(note, "blue")
            QTimer.singleShot(500, self.keyboard_view.reset_highlighted_keys)
        else:
            self.timer_notes.stop()
            self.keyboard_view.reset_highlighted_keys()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Q:
            self.close()

# KeyboardView 클래스는 변경 없음


# 가상 키보드 클래스
class KeyboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(2000, 400)

        # 건반 데이터 (C ~ B)
        self.keys = [
            {"note": "C", "type": "white"},
            {"note": "C#", "type": "black"},
            {"note": "D", "type": "white"},
            {"note": "D#", "type": "black"},
            {"note": "E", "type": "white"},
            {"note": "F", "type": "white"},
            {"note": "F#", "type": "black"},
            {"note": "G", "type": "white"},
            {"note": "G#", "type": "black"},
            {"note": "A", "type": "white"},
            {"note": "A#", "type": "black"},
            {"note": "B", "type": "white"},
        ]

        self.key_rects = []
        self.highlighted_keys = {}

    def paintEvent(self, event):
        painter = QPainter(self)
        self.key_rects = []

        widget_width = self.width()
        total_white_keys = sum(1 for key in self.keys if key["type"] == "white")
        total_width = total_white_keys * 80
        start_x = ((widget_width - total_width) // 2) - 80

        x = start_x

        # 흰 건반 그리기
        for key in self.keys:
            if key["type"] == "white":
                rect = QRect(x+80, 50, 80, 200)
                color = self.highlighted_keys.get(key["note"], Qt.white)
                painter.setBrush(QColor(color))
                painter.setPen(QPen(Qt.black))
                painter.drawRect(rect)
                self.key_rects.append((rect, key["note"]))
                x += 80

        # 검은 건반 그리기
        x = start_x
        for key in self.keys:
            if key["type"] == "black":
                rect = QRect(x + 50, 50, 60, 140)
                color = self.highlighted_keys.get(key["note"], Qt.black)
                painter.setBrush(QColor(color))
                painter.setPen(QPen(Qt.black))
                painter.drawRect(rect)
                self.key_rects.append((rect, key["note"]))
            if key["type"] == "white":
                x += 80

    def mousePressEvent(self, event):
        for rect, note in self.key_rects:
            if rect.contains(event.pos()):
                self.handle_note_action(note)
                break

    def handle_note_action(self, note):
        print(f"Key pressed: {note}")

    def highlight_key(self, note, color):
        self.highlighted_keys[note] = color
        self.update()

    def reset_highlighted_keys(self):
        self.highlighted_keys = {}
        self.update()
        
def main():
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = "/path/to/your/qt/plugins"
    
    app = QApplication(sys.argv)
    combined_window = CombinedWindow()
    combined_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()