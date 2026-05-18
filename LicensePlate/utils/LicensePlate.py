import cv2
import os
import re
from ultralytics import YOLO
import easyocr
from .super_resolution import upscale_plate_opencv

MODEL_PATH = "license_plate_detector.pt"
model = YOLO(MODEL_PATH)

ocr_reader = easyocr.Reader(['en'], gpu=False)


def clean_plate_text(text):
    text = text.upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text


def detect_license_plates(image_path, save_dir="media/plates/"):
    os.makedirs(save_dir, exist_ok=True)

    image = cv2.imread(image_path)
    results = model.predict(source=image, conf=0.25, verbose=False)

    plates_data = []

    for result in results:
        if result.boxes is None:
            continue

        for i, box in enumerate(result.boxes.xyxy):
            x1, y1, x2, y2 = map(int, box)

            cropped_plate = image[y1:y2, x1:x2]

            # 🔥 SUPER RESOLUTION
            upscaled_plate = upscale_plate_opencv(cropped_plate)

            crop_path = os.path.join(save_dir, f"plate_{i}.jpg")
            cv2.imwrite(crop_path, upscaled_plate)

            # OCR on UPSCALED image
            ocr_result = ocr_reader.readtext(upscaled_plate, detail=0)
            plate_text = clean_plate_text(" ".join(ocr_result))

            plates_data.append({
                "image": crop_path,
                "text": plate_text
            })

    return plates_data
