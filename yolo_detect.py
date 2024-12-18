from ultralytics import YOLO
import cv2
import numpy as np

# YOLO 모델 로드
model = YOLO("/home/intel/git-training/jojo_test/best_1_1680.pt")

# 웹캠 설정
cap = cv2.VideoCapture(0)  # 0은 기본 웹캠

while cap.isOpened():
    # 프레임 읽기
    success, frame = cap.read()

    if success:
        # YOLO로 객체 감지 수행
        results = model(frame)
        
        # 결과를 화면에 표시하기 위해 첫 번째 결과 선택
        annotated_frame = results[0].plot()
        
        # 결과 화면 표시
        cv2.imshow("YOLOv8 Detection", annotated_frame)

        # 'q' 키를 누르면 종료
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    else:
        break

# 정리
cap.release()
cv2.destroyAllWindows()