import sys
import json
import cv2
import os

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
                             QDesktopWidget, QLineEdit, QFileDialog, QLabel)
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QPixmap
from PyQt5.QtCore import QRect, Qt, QTimer

# 노래 데이터를 저장할 변수
song_data = None

# JSON 파일 로드 함수
def load_song_data(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
        # note와 octave를 합친 형식으로 변환
        for note_data in data["song"]:
            note_data["full_note"] = f"{note_data['note']}{note_data['octave']}"
        return data

# PyQt5 통합된 창 (웹캠과 가상 키보드)
class CombinedWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Webcam and Virtual Keyboard")
        self.setGeometry(150, 150, 1000, 600)

        # 중앙 위젯과 레이아웃 설정
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # 웹캠 레이아웃 (중앙 정렬을 위해)
        self.webcam_layout = QVBoxLayout()
        self.webcam_label = QLabel(self)
        self.webcam_label.setFixedSize(640, 480)  # 웹캠 Size 설정
        self.webcam_layout.addWidget(self.webcam_label)
        self.webcam_layout.setAlignment(Qt.AlignCenter)  # 웹캠을 가운데 정렬
        self.layout.addLayout(self.webcam_layout)

        # OpenCV 캡처 초기화
        self.cap = cv2.VideoCapture(0)

        # QTimer로 프레임 업데이트
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 약 30fps로 업데이트

        # 가상 키보드 추가
        self.keyboard_view = KeyboardView(self)
        self.layout.addWidget(self.keyboard_view)

        # JSON 파일 선택 버튼 추가
        self.load_button = QPushButton("Load JSON File", self)
        self.load_button.clicked.connect(self.load_json_file)
        self.layout.addWidget(self.load_button)

        # 계이름 입력란 추가
        self.note_input = QLineEdit(self)
        self.note_input.setPlaceholderText("Enter note name (e.g. C4)")
        self.layout.addWidget(self.note_input)

        # 계이름 확인 버튼 추가
        self.check_button = QPushButton("Check Note", self)
        self.check_button.clicked.connect(self.check_note)
        self.layout.addWidget(self.check_button)

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

        self.is_note_correct = False  # 계이름 맞는지 여부를 추적

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            qt_image = QImage(frame.data, width, height, width * channel, QImage.Format_RGB888)
            self.webcam_label.setPixmap(QPixmap.fromImage(qt_image))

    def load_json_file(self):
        global song_data
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)", options=options)
        if file_path:
            song_data = load_song_data(file_path)

    def play_notes_from_json(self):
        if not song_data:
            return
        self.note_index = 0  # 첫 번째 계이름으로 초기화
        self.note_input.clear()  # 이전 계이름 입력 지우기
        self.timer_notes.start(1500)  # 1500ms 간격으로 실행

    def play_next_note(self):
        global song_data
        if self.note_index < len(song_data["song"]):
            note_data = song_data["song"][self.note_index]
            note = note_data["full_note"]

            # 기존 파란색 건반 초기화
            self.keyboard_view.reset_highlighted_keys()

            # 파란색 하이라이트 후 대기
            self.keyboard_view.highlight_key(note, "blue")
            QTimer.singleShot(500, self.keyboard_view.reset_highlighted_keys)  # 500ms 후 초기화
        else:
            self.timer_notes.stop()
            self.keyboard_view.reset_highlighted_keys()  # 건반 초기화

    def check_note(self):
        global song_data
        if not song_data:
            return

        # 사용자 입력 계이름
        user_note = self.note_input.text().strip()
        correct_note = song_data["song"][self.note_index]["full_note"]

        # 계이름 비교
        if user_note == correct_note:
            self.is_note_correct = True
            self.note_index += 1  # 맞으면 다음 계이름으로 이동
            self.keyboard_view.reset_highlighted_keys()  # 현재 계이름 하이라이트 초기화

            # 계이름을 맞히면 그 다음 계이름을 표시
            if self.note_index < len(song_data["song"]):
                next_note = song_data["song"][self.note_index]["full_note"]
                self.keyboard_view.highlight_key(next_note, "blue")
            else:
                self.note_input.setText("All notes played!")  # 모든 계이름을 맞히면 메시지 표시
        else:
            self.is_note_correct = False
            self.note_input.setText("Incorrect. Try again!")  # 틀렸으면 계속 시도

    def keyPressEvent(self, event):
        # 'q' 키가 눌리면 프로그램 종료
        if event.key() == Qt.Key_Q:
            self.close()

        # 'Enter' 키가 눌리면 계이름 확인
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.check_note()  # Enter 키가 눌리면 계이름 확인

# 가상 키보드 클래스
class KeyboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(2000, 400)  # 가상 키보드 크기 2배로 설정

        # 건반 데이터 (C3 ~ C5)
        self.keys = []
        for octave in range(3, 5):
            self.keys.extend([
                {"note": f"C{octave}", "type": "white"},
                {"note": f"C#{octave}", "type": "black"},
                {"note": f"D{octave}", "type": "white"},
                {"note": f"D#{octave}", "type": "black"},
                {"note": f"E{octave}", "type": "white"},
                {"note": f"F{octave}", "type": "white"},
                {"note": f"F#{octave}", "type": "black"},
                {"note": f"G{octave}", "type": "white"},
                {"note": f"G#{octave}", "type": "black"},
                {"note": f"A{octave}", "type": "white"},
                {"note": f"A#{octave}", "type": "black"},
                {"note": f"B{octave}", "type": "white"},
            ])

        self.key_rects = []
        self.highlighted_keys = {}

    def paintEvent(self, event):
        painter = QPainter(self)
        self.key_rects = []

        # 창 너비 기준으로 중앙 정렬 계산
        widget_width = self.width()
        total_white_keys = sum(1 for key in self.keys if key["type"] == "white")
        total_width = total_white_keys * 80  # 각 흰 건반의 너비를 80px로 설정
        start_x = ((widget_width - total_width) // 2 )-80 # 중앙 정렬 시작 x 좌표

        x = start_x  # 초기 x 위치 설정

        # 흰 건반 그리기
        for key in self.keys:
            if key["type"] == "white":
                rect = QRect(x+80, 50, 80, 200)  # 흰 건반 높이를 200px로 설정
                color = self.highlighted_keys.get(key["note"], Qt.white)
                painter.setBrush(QColor(color))
                painter.setPen(QPen(Qt.black))
                painter.drawRect(rect)
                self.key_rects.append((rect, key["note"]))
                x += 80  # 흰 건반의 너비만큼 이동

        # 검은 건반 그리기
        x = start_x  # 흰 건반의 시작점 다시 계산
        for key in self.keys:
            if key["type"] == "black":
                # 검은 건반은 흰 건반의 중간에 위치
                rect = QRect(x + 50, 50, 60, 140)  # 검은 건반 크기를 적당히 조정
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
        # 키보드 건반 클릭 시 액션 처리
        print(f"Key pressed: {note}")

    def highlight_key(self, note, color):
        # 건반 하이라이트
        self.highlighted_keys[note] = color
        self.update()

    def reset_highlighted_keys(self):
        # 하이라이트 초기화
        self.highlighted_keys = {}
        self.update()

# PyQt5 앱 실행
def main():
    # QT_QPA_PLATFORM_PLUGIN_PATH 환경 변수 설정
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = "/path/to/your/qt/plugins"
    
    app = QApplication(sys.argv)

    # 통합된 창 실행
    combined_window = CombinedWindow()
    combined_window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()