// Backend Server Base URL
const SERVER_URL = "http://127.0.0.1:8000";

// DOM Element Selectors
const statusTrained = document.getElementById('statusTrained');
const statusCamera = document.getElementById('statusCamera');

const userNameInput = document.getElementById('userNameInput');
const registerBtn = document.getElementById('registerBtn');
const progressContainer = document.getElementById('progressContainer');
const progressText = document.getElementById('progressText');
const progressPercent = document.getElementById('progressPercent');
const progressBarFill = document.getElementById('progressBarFill');

const trainBtn = document.getElementById('trainBtn');
const consoleLogs = document.getElementById('consoleLogs');

const refreshBtn = document.getElementById('refreshBtn');
const exportBtn = document.getElementById('exportBtn');
const attendanceTableBody = document.getElementById('attendanceTableBody');

// Register polling interval ID
let registerPollInterval = null;

// Write to telemetry console
function addLog(text, type = "sys-log") {
    const line = document.createElement('div');
    line.className = `log-line ${type}`;
    line.innerText = `>> ${text}`;
    consoleLogs.appendChild(line);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

// Fetch general backend status
async function updateStatus() {
    try {
        const res = await fetch(`${SERVER_URL}/status`);
        if (!res.ok) return;
        const data = await res.json();
        
        // Update Trainer Badge
        if (data.trained) {
            statusTrained.classList.add('active');
            statusTrained.querySelector('.status-label').innerText = `TRAINER: ONLINE (${data.registered_count} USERS)`;
        } else {
            statusTrained.classList.remove('active');
            statusTrained.querySelector('.status-label').innerText = `TRAINER: OFFLINE`;
        }
        
        // Update Camera Badge
        if (data.camera_active) {
            statusCamera.classList.add('active');
            statusCamera.querySelector('.status-label').innerText = `CAMERA: ACTIVE`;
        } else {
            statusCamera.classList.remove('active');
            statusCamera.querySelector('.status-label').innerText = `CAMERA: OFFLINE`;
        }
    } catch (err) {
        // Server offline
        statusTrained.classList.remove('active');
        statusCamera.classList.remove('active');
        statusTrained.querySelector('.status-label').innerText = `TRAINER: OFFLINE`;
        statusCamera.querySelector('.status-label').innerText = `CAMERA: DISCONNECTED`;
    }
}

// Load daily attendance logs
async function loadAttendance() {
    try {
        const res = await fetch(`${SERVER_URL}/attendance`);
        if (!res.ok) return;
        const logs = await res.json();
        
        if (logs.length === 0) {
            attendanceTableBody.innerHTML = '<tr><td colspan="5" class="table-empty">No attendance records logged for today.</td></tr>';
            return;
        }
        
        attendanceTableBody.innerHTML = '';
        logs.forEach((log, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td>${log.name}</td>
                <td>${log.date}</td>
                <td>${log.time}</td>
                <td><span class="check-in-tag">CHECKED-IN</span></td>
            `;
            attendanceTableBody.appendChild(tr);
        });
    } catch (err) {
        attendanceTableBody.innerHTML = '<tr><td colspan="5" class="table-empty" style="color: #ff0055;">Failed to load attendance. Check backend.</td></tr>';
    }
}

// Face samples capture progression monitor
function startProgressPolling() {
    progressContainer.style.display = 'block';
    registerBtn.disabled = true;
    
    registerPollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${SERVER_URL}/register_status`);
            if (!res.ok) return;
            const data = await res.json();
            
            if (data.is_registering) {
                const count = data.count;
                const percentage = Math.round((count / 30) * 100);
                
                progressText.innerText = `Scanning: ${count} / 30 Samples`;
                progressPercent.innerText = `${percentage}%`;
                progressBarFill.style.width = `${percentage}%`;
                
                // Add tick sound on progress ticks
                if (count > 0 && count % 5 === 0) {
                    playTone(600, 0.05);
                }
            } else {
                // Completed
                clearInterval(registerPollInterval);
                progressContainer.style.display = 'none';
                progressBarFill.style.width = '0%';
                registerBtn.disabled = false;
                userNameInput.value = '';
                
                addLog("Dataset capture completed successfully.", "success-log");
                addLog("Please click 'TRAIN AI RECOGNIZER' to compile profile.", "prompt-log");
                playTone(800, 0.15);
                updateStatus();
            }
        } catch (err) {
            clearInterval(registerPollInterval);
            progressContainer.style.display = 'none';
            registerBtn.disabled = false;
            addLog("Scanning process aborted due to connection error.", "error-log");
        }
    }, 200);
}

// User Registration Trigger
async function registerUser() {
    const name = userNameInput.value.trim();
    if (!name) {
        alert("Please enter a valid profile name.");
        return;
    }
    
    addLog(`Initializing scan sequence for profile: ${name}...`, "sys-log");
    addLog("Look directly at the viewfinder webcam.", "prompt-log");
    
    try {
        const res = await fetch(`${SERVER_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: name })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            addLog(data.message, "sys-log");
            startProgressPolling();
        } else {
            addLog(`Error: ${data.detail}`, "error-log");
        }
    } catch (err) {
        addLog("Failed to connect to register API endpoint.", "error-log");
    }
}

// Trainer Trigger
async function trainModel() {
    addLog("Compiling facial dataset and training LBPH recognizer...", "sys-log");
    trainBtn.disabled = true;
    const originalLabel = trainBtn.innerHTML;
    trainBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> COMPILING PROFILES...';
    
    try {
        const res = await fetch(`${SERVER_URL}/train`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (res.ok) {
            addLog(data.message, "success-log");
            addLog("Face Recognizer online & listening.", "success-log");
            playTone(900, 0.2);
            updateStatus();
        } else {
            addLog(`Training aborted: ${data.detail}`, "error-log");
            playTone(300, 0.25);
        }
    } catch (err) {
        addLog("Connection failed to train API endpoint.", "error-log");
    } finally {
        trainBtn.disabled = false;
        trainBtn.innerHTML = originalLabel;
    }
}

// Sound feedback helper
function playTone(freq, duration) {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.04, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch(e) {}
}

// Setup Event Listeners
registerBtn.addEventListener('click', registerUser);
userNameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') registerUser();
});

trainBtn.addEventListener('click', trainModel);
refreshBtn.addEventListener('click', loadAttendance);

exportBtn.addEventListener('click', () => {
    addLog("Exporting attendance spreadsheet logs...", "sys-log");
    window.location.href = `${SERVER_URL}/export`;
});

// Initialization
window.addEventListener('DOMContentLoaded', () => {
    updateStatus();
    loadAttendance();
    
    // Status polling intervals
    setInterval(updateStatus, 5000);
    setInterval(loadAttendance, 4000);
});
