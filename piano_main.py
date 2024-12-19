import sys
import json
import cv2
import os
from ultralytics import YOLO
import numpy as np

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
                             QDesktopWidget, QLineEdit, QFileDialog, QLabel)
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QPixmap
from PyQt5.QtCore import QRect, Qt, QTimer, QPoint

# 악보 데이터를 저장할 변수
song_data = None

# 악보 파일 로드 함수
def load_song_data(file_path):
    """
    지정된 경로에서 json 형식의 악보 데이터를 로드
    """
    with open(file_path, "r") as f:
        return json.load(f)

class CombinedWindow(QMainWindow):
    def __init__(self):
        """
        메인 윈도우를 초기화
        웹캠 화면, 가상 건반, 버튼을 포함
        """
        super().__init__()
        self.setWindowTitle("Webcam and Virtual Keyboard")
        self.setGeometry(150, 150, 1000, 600)

        # YOLO 모델 로드
        self.model = YOLO("./test_files/best_1_1680.pt")
        self.detected_note = None

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
        self.timer.start(50)

        # 가상 건반 추가
        self.keyboard_view = KeyboardView(self)
        self.layout.addWidget(self.keyboard_view)

        # 악보 파일 선택 버튼
        self.load_button = QPushButton("악보 선택", self)
        self.load_button.clicked.connect(self.load_json_file)
        self.layout.addWidget(self.load_button)

        # 인식된 건반(계이름) 표시 레이블
        self.detected_label = QLabel("인식 안 됨", self)
        self.layout.addWidget(self.detected_label)

        # 악보 데이터 실행 버튼
        self.play_button = QPushButton("악보 연주 시작", self)
        self.play_button.clicked.connect(self.play_notes_from_json)
        self.layout.addWidget(self.play_button)

        # 종료 버튼
        self.exit_button = QPushButton("프로그램 종료", self)
        self.exit_button.clicked.connect(self.close)
        self.layout.addWidget(self.exit_button)

        # 상태 관리 변수 초기화
        self.note_index = 0
        self.timer_notes = QTimer(self)
        self.timer_notes.timeout.connect(self.play_next_note)
        self.is_note_correct = False
        self.allow_note_check = True

    def update_frame(self):
        """
        웹캠 프레임을 업데이트하고 YOLO 모델을 사용해 건반 인식
        인식 결과를 화면에 표시
        """
        ret, frame = self.cap.read()
        if ret:
            results = self.model(frame)
            if len(results) > 0 and len(results[0].boxes) > 0:
                confidence = results[0].boxes.conf.cpu().numpy()
                if len(confidence) > 0:
                    max_conf_idx = np.argmax(confidence)
                    if confidence[max_conf_idx] >= 0.7:
                        class_id = results[0].boxes.cls[max_conf_idx].item()
                        detected_note = results[0].names[int(class_id)]

                        if self.detected_note != detected_note:
                            self.detected_note = detected_note
                            self.detected_label.setText(f"{detected_note} 건반 누름")
                            if self.allow_note_check:
                                self.check_detected_note()
                    else:
                        self.detected_note = None

            # YOLO 모델이 주석을 추가한 프레임을 표시
            annotated_frame = results[0].plot()
            annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            height, width, channel = annotated_frame.shape
            qt_image = QImage(annotated_frame.data, width, height, width * channel, QImage.Format_RGB888)
            self.webcam_label.setPixmap(QPixmap.fromImage(qt_image))

    def check_detected_note(self):
        """
        웹캠에서 인식된 건반이 json 데이터의 의해 지시된 건반 데이터와 일치하는지 체크
        """
        if not song_data or self.detected_note is None:
            return

        correct_note = song_data["song"][self.note_index]["note"]

        if self.detected_note == correct_note:
            self.is_note_correct = True
            self.allow_note_check = False
            self.keyboard_view.set_arrow_position(correct_note, "#00FF00")  # 초록색 화살표
            QTimer.singleShot(300, lambda: self.reset_and_highlight_next(True))
        else:
            self.is_note_correct = False
            self.allow_note_check = False
            self.keyboard_view.set_arrow_position(self.detected_note, "#FF0000")  # 빨간색 화살표
            QTimer.singleShot(300, lambda: self.keyboard_view.reset_highlighted_keys())
            QTimer.singleShot(300, lambda: self.reset_and_highlight_next(False))

    def reset_and_highlight_next(self, is_correct):
        """
        현재 건반 상태를 초기화 및 다음 건반 강조 표시
        """
        self.keyboard_view.reset_highlighted_keys()

        if is_correct:
            self.note_index += 1

        if self.note_index < len(song_data["song"]):
            next_note = song_data["song"][self.note_index]["note"]
            self.keyboard_view.set_arrow_position(next_note, "#0000FF")  # 파란색 화살표
            QTimer.singleShot(500, lambda: self.enable_note_check())
        else:
            self.detected_label.setText("연주 완료!")

    def enable_note_check(self):
        """
        계이름 검사 enable
        """
        self.allow_note_check = True

    def load_json_file(self):
        """
        json 형식의 악보 파일을 선택하고 load
        """
        global song_data
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "악보 선택", "", "JSON Files (*.json)", options=options)
        if file_path:
            song_data = load_song_data(file_path)

    def play_notes_from_json(self):
        """
        JSON 파일에서 계이름 데이터를 읽어와서 표시
        """
        if not song_data:
            return
        self.note_index = 0
        self.detected_note = None
        self.timer_notes.start(1500)

    def play_next_note(self):
        """
        조건이 일치하면
        다음 건반을 지시
        """
        global song_data
        if self.note_index < len(song_data["song"]):
            note_data = song_data["song"][self.note_index]
            note = note_data["note"]

            self.keyboard_view.reset_highlighted_keys()
            self.keyboard_view.set_arrow_position(note, "#0000FF")
        else:
            self.timer_notes.stop()
            self.keyboard_view.reset_highlighted_keys()
    
    def keyPressEvent(self, event):
        """
        키보드 Q를 입력하면 종료
        """
        if event.key() == Qt.Key_Q:
            self.close()

class KeyboardView(QWidget):
    def __init__(self, parent=None):
        """
        가상 건반을 초기화하고
        건반 별로 실제 건반의 색상과 매칭되는 색상 지정
        """
        super().__init__(parent)
        self.setMinimumSize(2000, 400)

        self.keys = [
            {"note": "C", "type": "white", "color": "#CEA6F9"},
            {"note": "C#", "type": "black", "color": "#000000"},
            {"note": "D", "type": "white", "color": "#F5AF64"},
            {"note": "D#", "type": "black", "color": "#000000"},
            {"note": "E", "type": "white", "color": "#0000CD"},
            {"note": "F", "type": "white", "color": "#FFD732"},
            {"note": "F#", "type": "black", "color": "#000000"},
            {"note": "G", "type": "white", "color": "#DF0101"},
            {"note": "G#", "type": "black", "color": "#000000"},
            {"note": "A", "type": "white", "color": "#A5DF00"},
            {"note": "A#", "type": "black", "color": "#000000"},
            {"note": "B", "type": "white", "color": "#6991E1"},
        ]

        self.key_rects = []
        self.highlighted_keys = {}
        self.arrow_position = None
        self.arrow_color = "#0000FF"  # 기본 파란색

    def paintEvent(self, event):
        """
        가상 건반과 화살표 그리기
        """
        painter = QPainter(self)
        self.key_rects = []

        widget_width = self.width()
        total_white_keys = sum(1 for key in self.keys if key["type"] == "white")
        total_width = total_white_keys * 80
        start_x = ((widget_width - total_width) // 2) - 80

        x = start_x

        for key in self.keys:   
            if key["type"] == "white":
                rect = QRect(x + 80, 50, 80, 200)
                color = self.highlighted_keys.get(key["note"], key["color"])
                painter.setBrush(QColor(color))
                painter.setPen(QPen(Qt.black))
                painter.drawRect(rect)
                self.key_rects.append((rect, key["note"]))
                x += 80

        x = start_x
        for key in self.keys:
            if key["type"] == "black":
                rect = QRect(x + 50, 50, 60, 140)
                color = self.highlighted_keys.get(key["note"], key["color"])
                painter.setBrush(QColor(color))
                painter.setPen(QPen(Qt.black))
                painter.drawRect(rect)
                self.key_rects.append((rect, key["note"]))
            if key["type"] == "white":
                x += 80

        if self.arrow_position:
            arrow_rect, arrow_note = self.arrow_position
            arrow_x = arrow_rect.center().x()
            arrow_y = arrow_rect.top() - 30
            painter.setPen(QPen(QColor(self.arrow_color), 3))
            painter.setBrush(QColor(self.arrow_color))
            painter.drawPolygon([
                QPoint(arrow_x - 10, arrow_y),
                QPoint(arrow_x + 10, arrow_y),
                QPoint(arrow_x, arrow_y + 20),
            ])

    def highlight_key(self, note, color):
        """
        실제 건반에 지정된 색상에 맞춰
        가상 키보드에 색상 지정
        """
        self.highlighted_keys[note] = color
        self.update()

    def reset_highlighted_keys(self):
        """
        건반과 화살표 초기화
        """
        self.highlighted_keys = {}
        self.arrow_position = None
        self.update()

    def set_arrow_position(self, note, color):
        """
        악보 데이터에 의해 지시되는 건반 위에 화살표를 표시
        """
        self.arrow_color = color
        for rect, key_note in self.key_rects:
            if key_note == note:
                self.arrow_position = (rect, note)
                break
        self.update()


def main():
    """
    프로그램 진입. 
    QApplication을 초기화하고 CombinedWindow를 실행
    """
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = "/path/to/your/qt/plugins"
    
    app = QApplication(sys.argv)
    combined_window = CombinedWindow()
    combined_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
