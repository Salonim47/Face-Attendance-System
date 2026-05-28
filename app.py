import os
import csv
import time
import sqlite3
from datetime import datetime
import cv2
import numpy as np
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="Face Recognition Attendance Backend")

# CORS middleware for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories setup
DATASET_DIR = "dataset"
TRAINER_DIR = "trainer"
TRAINER_FILE = os.path.join(TRAINER_DIR, "trainer.yml")
ATTENDANCE_CSV = "attendance.csv"
DB_FILE = "attendance.db"

os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(TRAINER_DIR, exist_ok=True)

# Database Setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            name TEXT,
            date TEXT,
            time TEXT,
            UNIQUE(name, date)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Global State Variables
capture_name = ""
capture_id = -1
capture_count = 0
is_registering = False

# Load OpenCV Classifiers & Recognizer
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()

# Load trained model if exists
has_trainer = os.path.exists(TRAINER_FILE)
if has_trainer:
    try:
        recognizer.read(TRAINER_FILE)
    except Exception as e:
        print(f"Error reading trainer file: {e}")
        has_trainer = False

# Mapping of ID to Name loaded from Database
def load_user_mappings():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

user_mappings = load_user_mappings()

# Global Camera Object
camera = None

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
    return camera

# Log Attendance to CSV and Database
def log_attendance(name: str):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    # 1. Log to SQLite (UNIQUE constraint prevents multiple logs per day)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO attendance (name, date, time) VALUES (?, ?, ?)", (name, date_str, time_str))
        conn.commit()
        
        # 2. Write to CSV if successfully logged in DB (avoid duplicates in CSV)
        write_header = not os.path.exists(ATTENDANCE_CSV)
        with open(ATTENDANCE_CSV, mode="a", newline="") as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(["Name", "Date", "Time"])
            writer.writerow([name, date_str, time_str])
            
        print(f"Logged attendance: {name} at {time_str}")
    except sqlite3.IntegrityError:
        # Already logged today
        pass
    finally:
        conn.close()

# MJPEG Stream generator
def generate_frames():
    global capture_name, capture_id, capture_count, is_registering, has_trainer, user_mappings
    cam = get_camera()

    while True:
        success, frame = cam.read()
        if not success:
            # yield dummy blank frame if camera not ready
            blank_frame = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(blank_frame, "Camera Feed Unavailable", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', blank_frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1)
            continue

        # Flip horizontally for mirrored review
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

        for (x, y, w, h) in faces:
            # Draw boundary boxes on faces
            box_color = (255, 243, 0) # default blue-cyan
            label = "Detecting..."

            # 1. If currently capturing dataset for registration
            if is_registering and capture_name:
                box_color = (0, 191, 255) # orange-gold
                label = f"Registering: {capture_count}/30"
                
                # Crop and save grayscale face
                face_crop = gray[y:y+h, x:x+w]
                face_crop = cv2.resize(face_crop, (200, 200))
                
                user_dir = os.path.join(DATASET_DIR, str(capture_id))
                os.makedirs(user_dir, exist_ok=True)
                
                img_path = os.path.join(user_dir, f"face_{capture_count}.jpg")
                cv2.imwrite(img_path, face_crop)
                capture_count += 1
                
                if capture_count >= 30:
                    # Capture completed
                    is_registering = False
                    capture_name = ""
                    print("Face registration samples complete.")
            
            # 2. If trained, run recognition prediction
            elif has_trainer:
                try:
                    face_crop = gray[y:y+h, x:x+w]
                    face_crop = cv2.resize(face_crop, (200, 200))
                    id_pred, confidence = recognizer.predict(face_crop)
                    
                    # For LBPH, confidence represents Euclidean distance. 
                    # Lower value = better match. Confidence < 75 is reliable.
                    if confidence < 75:
                        name = user_mappings.get(id_pred, f"ID: {id_pred}")
                        label = f"{name} ({round(100 - confidence)}%)"
                        box_color = (57, 255, 20) # neon green
                        
                        # Log attendance in background
                        log_attendance(name)
                    else:
                        label = "Unknown"
                        box_color = (0, 0, 255) # red
                except Exception as e:
                    print(f"Prediction error: {e}")
            else:
                label = "AI Trainer Offline"
                box_color = (255, 0, 127) # magenta

            # Draw box & label
            cv2.rectangle(frame, (x, y), (x+w, y+h), box_color, 2)
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, box_color, 2)

        # Encode frame back to JPEG stream
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# Streaming route
@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# Register Endpoint
class RegisterRequest(BaseModel):
    name: str

@app.post("/register")
def register_user(req: RegisterRequest):
    global capture_name, capture_id, capture_count, is_registering, user_mappings
    
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")
        
    # Check if camera is active
    cam = get_camera()
    if not cam.isOpened():
         raise HTTPException(status_code=500, detail="Webcam not active.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Save user to DB to allocate new ID
        cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        # User already exists, retrieve existing ID
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        new_id = cursor.fetchone()[0]
    finally:
        conn.close()

    # Reset globals to trigger image capture loop in generator
    capture_name = name
    capture_id = new_id
    capture_count = 0
    is_registering = True
    
    # Reload user mappings
    user_mappings = load_user_mappings()
    
    return {"message": f"Capture sequence initialized for {name}.", "id": new_id}

@app.get("/register_status")
def register_status():
    global capture_name, capture_count, is_registering
    return {
        "is_registering": is_registering,
        "count": capture_count,
        "name": capture_name
    }

# Trainer Executor
@app.post("/train")
def train_model():
    global has_trainer
    
    dataset_path = DATASET_DIR
    if not os.path.exists(dataset_path) or len(os.listdir(dataset_path)) == 0:
        raise HTTPException(status_code=400, detail="Dataset is empty. Register at least one user first.")

    faces = []
    ids = []

    try:
        for user_dir in os.listdir(dataset_path):
            dir_path = os.path.join(dataset_path, user_dir)
            if not os.path.isdir(dir_path):
                continue
            
            user_id = int(user_dir)
            for filename in os.listdir(dir_path):
                if filename.endswith(".jpg"):
                    img_path = os.path.join(dir_path, filename)
                    gray_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if gray_img is not None:
                        faces.append(gray_img)
                        ids.append(user_id)

        if len(faces) == 0:
            raise HTTPException(status_code=400, detail="No face images found in dataset.")

        # Train LBPH classifier
        recognizer.train(faces, np.array(ids))
        recognizer.write(TRAINER_FILE)
        
        has_trainer = True
        return {"message": "AI face recognition trainer finished successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training error: {str(e)}")

# Log Reader
@app.get("/attendance")
def get_attendance():
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, date, time FROM attendance WHERE date = ? ORDER BY time DESC", (date_str,))
    rows = cursor.fetchall()
    conn.close()
    
    logs = [{"name": r[0], "date": r[1], "time": r[2]} for r in rows]
    return logs

# Export CSV
@app.get("/export")
def export_csv():
    if not os.path.exists(ATTENDANCE_CSV):
        # Create empty CSV with headers if it doesn't exist
        with open(ATTENDANCE_CSV, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Name", "Date", "Time"])
            
    return FileResponse(
        ATTENDANCE_CSV, 
        media_type="text/csv", 
        filename=f"attendance_{datetime.now().strftime('%Y-%m-%d')}.csv"
    )

# Status Endpoint
@app.get("/status")
def get_status():
    global has_trainer
    cam = get_camera()
    return {
        "trained": has_trainer,
        "camera_active": cam.isOpened(),
        "registered_count": len(load_user_mappings())
    }

# Shutdown hook to release resources
@app.on_event("shutdown")
def shutdown_event():
    global camera
    if camera is not None:
        camera.release()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

