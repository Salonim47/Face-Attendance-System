# Biometric Face Recognition & Attendance System

An advanced, client-server Biometric Face Recognition and Attendance logging portal. The system uses a local Python backend (FastAPI, SQLite, and OpenCV) and a glassmorphic HTML/CSS frontend dashboard to map, recognize, and log users in real-time.

![Biometric Portal Mockup](https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&q=80&w=800) *(Visual representation of digital biometric interfaces)*

## ✨ Key Features
- **OpenCV LBPH Face Recognizer**: Uses the Local Binary Patterns Histograms (LBPH) classifier for lightweight, local face matching. Avoids heavy dlib/CMake compiler issues, guaranteeing a seamless install.
- **Haar-Cascade Face Detector**: Employs real-time cascade classification to bound, track, and capture gray face crops at 30 FPS.
- **Interactive Dataset Capture**: Enter a name on the dashboard to trigger a 30-frame capture loop. Displays a glowing progress bar indicating scanning milestones.
- **Instant Training Core**: Compiles registered directories and trains the LBPH model locally in under 2 seconds, saving state to `trainer.yml`.
- **Database & Spreadsheet Logs**: Logs check-ins to a local SQLite database (`attendance.db`) and prints daily matches directly to the dashboard log sheet. Automatically aggregates a downloadable `attendance.csv` sheet.
- **One-Click Startup (`run.bat`)**: Automatically uninstalls conflicting standard packages, installs `opencv-contrib-python`, `fastapi`, and `uvicorn`, and boots the server.

## 🛠️ Biometric Mappings & DB Models
1. **Face Sample Processing**:
   - Bounding boxes cropped from camera stream are resized to a uniform `200x200` pixels and converted to grayscale for texture-based LBPH signature extraction.
2. **SQLite Database Structure**:
   - `users`: ID (Autoincrement primary key), Name (Unique). Maps integer labels to profile name strings.
   - `attendance`: Name, Date, Time (Composite Unique Key: `name` + `date` prevents double check-ins on the same day).

## 🚀 Easy Setup & Launch
1. Open the [Face-Attendance-System](file:///c:/Users/mail2/OneDrive/Documents/Face-Attendance-System/) folder.
2. Double-click the **`run.bat`** file. It will uninstall conflictive packages, verify dependencies, and start the FastAPI service on `http://127.0.0.1:8000`.
3. Open **`index.html`** in your browser.
4. Type your name in the input box and click **CAPTURE FACE SAMPLES**. Follow the progress scan.
5. Once completed, click **TRAIN AI RECOGNIZER** to compile the neural mapping.
6. Stand back; the camera view will frame you in green, overlay your name, and append a check-in row to the attendance logs!
