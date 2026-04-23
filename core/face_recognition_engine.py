import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from utils.config import CAMERA_INDEX, SIMILARITY_THRESHOLD, ENCODINGS_PATH, STUDENT_IMAGES
import pandas as pd

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
PROFILE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_profileface.xml"
profile_face_cascade = cv2.CascadeClassifier(PROFILE_CASCADE_PATH)

def generate_python_encodings():
    """Reads all images and generates encodings using OpenCV LBPH Native."""
    print("[INFO] Generating LBPH encodings natively...")
    import json

    if not hasattr(cv2, "face"):
        print("[ERROR] OpenCV contrib modules are unavailable. Install opencv-contrib-python.")
        return False
    
    if not os.path.exists(STUDENT_IMAGES): return False
        
    faces = []
    labels = []
    student_map = {}
    current_label = 0
    
    for student_id in os.listdir(STUDENT_IMAGES):
        folder = os.path.join(STUDENT_IMAGES, student_id)
        if not os.path.isdir(folder): continue
        
        student_map[str(current_label)] = student_id
        has_face = False
        
        for img_name in os.listdir(folder):
            if not img_name.endswith(".jpg"): continue
            img_path = os.path.join(folder, img_name)
            
            img = cv2.imread(img_path)
            if img is None: continue
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces.append(gray)
            labels.append(current_label)
            has_face = True
            
        if has_face:
            current_label += 1
            
    if faces:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(labels))
        
        os.makedirs(os.path.dirname(ENCODINGS_PATH), exist_ok=True)
        yml_path = ENCODINGS_PATH.replace('face_encodings.csv', 'face_encodings.yml')
        map_path = ENCODINGS_PATH.replace('face_encodings.csv', 'student_map.json')
        
        recognizer.write(yml_path)
        with open(map_path, 'w') as f:
            json.dump(student_map, f)
            
        print(f"[INFO] Successfully saved LBPH encodings.")
        return True
    return False

def identify_face_dlib(face_img_rgb, student_map, recognizer):
    if not student_map or recognizer is None:
        return "Unknown", 0.0

    gray = _prepare_face_for_lbph(face_img_rgb)
    
    try:
        label, distance = recognizer.predict(gray)
    except Exception:
        return "Unknown", 0.0
        
    # Standard LBPH thresholds (lower distance is better, usually ~40-60 is a solid match)
    if distance < 75:
        name = student_map.get(str(label), "Unknown")
        # Pseudo confidence mapping
        confidence = max(0.0, min(1.0, 1.0 - (distance / 100.0)))
        return name, confidence
    
    return "Unknown", 0.0

def predict_lbph_match(face_img_rgb, student_map, recognizer, distance_threshold=75):
    if not student_map or recognizer is None:
        return "Unknown", 0.0, None

    gray = _prepare_face_for_lbph(face_img_rgb)

    try:
        label, distance = recognizer.predict(gray)
    except Exception:
        return "Unknown", 0.0, None

    if distance < distance_threshold:
        student_id = student_map.get(str(label), "Unknown")
        confidence = max(0.0, min(1.0, 1.0 - (distance / 100.0)))
        return student_id, confidence, float(distance)

    return "Unknown", 0.0, float(distance)

def _prepare_face_for_lbph(face_img_rgb):
    gray = cv2.cvtColor(face_img_rgb, cv2.COLOR_RGB2GRAY)
    if gray.size == 0:
        return gray

    shortest_side = min(gray.shape[:2])
    if shortest_side < 140:
        scale = 140 / max(shortest_side, 1)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    return cv2.equalizeHist(gray)

def detect_faces(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = []

    def add_faces(cascade, image, scale=1.0, min_size=(34, 34), min_neighbors=4):
        if cascade.empty():
            return
        detected = cascade.detectMultiScale(
            image,
            scaleFactor=1.06,
            minNeighbors=min_neighbors,
            minSize=min_size,
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        for (x, y, w, h) in detected:
            if scale != 1.0:
                x = int(x / scale)
                y = int(y / scale)
                w = int(w / scale)
                h = int(h / scale)
            faces.append((x, y, w, h))

    add_faces(face_cascade, gray, min_size=(34, 34), min_neighbors=4)

    # Upscaling makes tiny, far-away faces large enough for Haar detection.
    upscaled = cv2.resize(gray, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_LINEAR)
    add_faces(face_cascade, upscaled, scale=1.6, min_size=(36, 36), min_neighbors=3)
    add_faces(profile_face_cascade, upscaled, scale=1.6, min_size=(36, 36), min_neighbors=3)
    if not profile_face_cascade.empty():
        flipped = cv2.flip(upscaled, 1)
        detected = profile_face_cascade.detectMultiScale(
            flipped,
            scaleFactor=1.06,
            minNeighbors=3,
            minSize=(36, 36),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        full_width = frame.shape[1]
        for (x, y, w, h) in detected:
            x = full_width - int((x + w) / 1.6)
            y = int(y / 1.6)
            w = int(w / 1.6)
            h = int(h / 1.6)
            faces.append((x, y, w, h))

    if len(faces) == 0:
        return []

    return _merge_face_boxes(faces, frame.shape[1], frame.shape[0])

def _merge_face_boxes(faces, frame_width, frame_height):
    cleaned = []
    for (x, y, w, h) in faces:
        aspect_ratio = w / max(h, 1)
        if aspect_ratio < 0.58 or aspect_ratio > 1.62:
            continue
        x = max(0, min(frame_width - 1, int(x)))
        y = max(0, min(frame_height - 1, int(y)))
        w = max(1, min(frame_width - x, int(w)))
        h = max(1, min(frame_height - y, int(h)))
        cleaned.append((x, y, w, h))

    cleaned.sort(key=lambda box: box[2] * box[3], reverse=True)
    merged = []
    for face in cleaned:
        if all(_face_iou(face, existing) < 0.35 for existing in merged):
            merged.append(face)
    return merged

def _face_iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = aw * ah
    area_b = bw * bh
    union = area_a + area_b - inter
    return inter / union if union else 0.0

def draw_results(frame, bbox, name, confidence):
    x, y, w, h = bbox
    # #98C379 green, #E06C75 red
    color = (121, 195, 152) if name != "Unknown" else (117, 108, 224) 
    
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

    label    = f"{name} ({confidence:.0%})" if name != "Unknown" else "Unknown"
    label_y  = y - 28 if y > 28 else y + h + 4

    cv2.rectangle(frame, (x, label_y), (x + w, label_y + 24), color, -1)
    cv2.putText(frame, label, (x + 4, label_y + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    return frame

def run_recognition_session(student_ids, encodings, on_identify, duration_seconds=300):
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera.")
        return

    import time
    start_time = time.time()
    identified = set()

    print(f"[INFO] Session started ({duration_seconds}s). Press Q to quit.")

    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration_seconds:
            print("[INFO] Session time reached. Stopping.")
            break

        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame.")
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces quickly via cascade
        faces = detect_faces(frame)

        for (x, y, w, h) in faces:
            # Provide padding around the detected face for the CNN to get better context
            y1, y2 = max(0, y-30), min(frame.shape[0], y+h+30)
            x1, x2 = max(0, x-30), min(frame.shape[1], x+w+30)
            
            face_crop_rgb = rgb_frame[y1:y2, x1:x2]
            
            # Identify
            name, conf = identify_face_dlib(face_crop_rgb, student_ids, encodings)
            
            frame = draw_results(frame, (x, y, w, h), name, conf)

            if name != "Unknown" and name not in identified:
                identified.add(name)
                on_identify(name)
                print(f"[MATCH] {name} — confidence {conf:.0%}")

        remaining = int(duration_seconds - elapsed)
        
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (28, 30, 34), -1)
        cv2.putText(frame, f"Session Active: {remaining}s left",
                    (10, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (224, 230, 237), 2)
        cv2.putText(frame, f"Marked: {len(identified)}",
                    (frame.shape[1] - 150, 26), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (152, 195, 121), 2)

        cv2.imshow("CogniAttend Live Capture - Press Q to stop", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("[INFO] Session stopped by user.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"[INFO] Session complete. Total identified: {len(identified)}")
    return list(identified)
