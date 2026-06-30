import eventlet
eventlet.monkey_patch()

import cv2
import face_recognition
import pyttsx3
import os
import numpy as np
import base64
from datetime import datetime
import threading
import sqlite3
import random
import requests
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart_access_secret'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

DB_PATH = 'logs.db'
TELEGRAM_BOT_TOKEN = ''
TELEGRAM_CHAT_ID = ''

# Глобальный словарь для отслеживания состояния (кто где находится)
# Ключ: name, Значение: 'HOME' или 'INSTITUTE'
user_locations = {}
# Ключ: name, Значение: фото base64 (для карты)
user_avatars = {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Пересоздаем таблицу с новой колонкой action_type
    cursor.execute('DROP TABLE IF EXISTS access_logs')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            name TEXT,
            status TEXT,
            temperature REAL,
            access_granted BOOLEAN,
            action_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_access(name, status, temperature, access_granted, action_type="ENTRY"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO access_logs (name, status, temperature, access_granted, action_type)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, status, temperature, access_granted, action_type))
    conn.commit()
    conn.close()
    
    socketio.emit('new_log', {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'name': name,
        'status': status,
        'temperature': temperature,
        'access_granted': access_granted,
        'action_type': action_type
    })

init_db()

engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak(text):
    print(f"[Voice] {text}")
    engine.say(text)
    engine.runAndWait()

def hardware_open_door():
    print(" [Hardware] Сигнал на GPIO -> Реле щелкает. Турникет ОТКРЫТ.")
    eventlet.sleep(5)
    print(" [Hardware] Сигнал на GPIO -> Реле отключено. Турникет ЗАКРЫТ.")

def hardware_read_temperature():
    print(" [Hardware] Считывание температуры (MLX90614)...")
    if random.random() < 0.1:
        temp = round(random.uniform(37.6, 38.5), 1)
    else:
        temp = round(random.uniform(36.1, 37.1), 1)
    return temp

def send_security_alert(image_b64):
    message = "⚠️ Внимание: Попытка несанкционированного доступа. Неизвестное лицо находилось перед камерой более 3 секунд."
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            image_data = base64.b64decode(image_b64.split(",")[1])
            files = {'photo': ('alert.jpg', image_data, 'image/jpeg')}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': message}
            requests.post(url, files=files, data=data)
        except Exception as e:
            print(f" [Security Webhook] Ошибка: {e}")
    else:
        print(" [Security Webhook] (Симуляция) Сообщение отправлено в чат.")

def load_database(db_path="database"):
    known_face_encodings = []
    known_face_info = []
    
    if not os.path.exists(db_path):
        return known_face_encodings, known_face_info

    print("Загрузка базы данных лиц...")
    for filename in os.listdir(db_path):
        if filename.lower().endswith((".jpg", ".png", ".jpeg")):
            name_parts = os.path.splitext(filename)[0].split('_')
            name = name_parts[0] if len(name_parts) > 0 else "Unknown"
            status = name_parts[1] if len(name_parts) > 1 else "Guest"
            
            image_path = os.path.join(db_path, filename)
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            
            if encodings:
                known_face_encodings.append(encodings[0])
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                image_b64 = f"data:image/jpeg;base64,{encoded_string}"
                
                known_face_info.append({"name": name, "status": status, "image_b64": image_b64})
                
                # Инициализация для Campus Map
                if name not in user_locations:
                    user_locations[name] = 'HOME'
                    user_avatars[name] = image_b64
                    
    return known_face_encodings, known_face_info

def generate_greeting(name, status, temp, action_type):
    now = datetime.now()
    current_time = now.strftime("%I:%M %p")
    
    if action_type == "ENTRY":
        if status.lower() == 'sensei' or status.lower() == 'teacher':
            return f"{name}-sensei, welcome to the Institute. Access granted. Time is {current_time}."
        elif status.lower() == 'student':
            return f"Good morning, {name}. Welcome. Time is {current_time}. Have a productive day!"
        else:
            return f"Welcome, {name}. Time is {current_time}."
    else:
        # EXIT
        if status.lower() == 'sensei' or status.lower() == 'teacher':
            return f"{name}-sensei, leaving so soon? Goodbye. Time is {current_time}."
        elif status.lower() == 'student':
            return f"Goodbye, {name}. Leaving at {current_time}. See you next time!"
        else:
            return f"Goodbye, {name}. Time is {current_time}."

def camera_loop():
    known_face_encodings, known_face_info = load_database()
    video_capture = cv2.VideoCapture(0)
    
    greeted_recently = {}
    timeout_seconds = 15
    unknown_start_time = None
    unknown_alert_sent = False

    while True:
        ret, frame = video_capture.read()
        if not ret:
            eventlet.sleep(0.1)
            continue
            
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        face_names = []
        has_unknown = False
        unknown_face_crop_b64 = None
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            name = "Unknown"
            status = "Unknown"
            
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            top, right, bottom, left = face_location
            top *= 4; right *= 4; bottom *= 4; left *= 4
            
            padding = 60
            crop_top = max(0, top - padding)
            crop_bottom = min(frame.shape[0], bottom + padding)
            crop_left = max(0, left - padding)
            crop_right = min(frame.shape[1], right + padding)
            face_crop = frame[crop_top:crop_bottom, crop_left:crop_right]
            
            if face_crop.size > 0:
                _, buffer = cv2.imencode('.jpg', face_crop)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                camera_image_b64 = f"data:image/jpeg;base64,{frame_b64}"
            else:
                camera_image_b64 = ""
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if face_distances[best_match_index] < 0.5:
                    info = known_face_info[best_match_index]
                    name = info['name']
                    status = info['status']
                    
                    current_time = datetime.now()
                    if name not in greeted_recently or (current_time - greeted_recently[name]).total_seconds() > timeout_seconds:
                        
                        temp = hardware_read_temperature()
                        
                        if temp > 37.5:
                            speak(f"Access denied for {name}. High temperature detected.")
                            log_access(name, status, temp, False, "DENIED")
                        else:
                            # Определение Entry/Exit
                            current_location = user_locations.get(name, 'HOME')
                            if current_location == 'HOME':
                                action_type = 'ENTRY'
                                user_locations[name] = 'INSTITUTE'
                            else:
                                action_type = 'EXIT'
                                user_locations[name] = 'HOME'
                                
                            greeting = generate_greeting(name, status, temp, action_type)
                            
                            socketio.emit('face_recognized', {
                                'name': name,
                                'status': status,
                                'image': camera_image_b64,
                                'action_type': action_type,
                                'location': user_locations[name]
                            })
                            
                            log_access(name, status, temp, True, action_type)
                            eventlet.spawn(hardware_open_door)
                            speak(greeting)
                            
                        greeted_recently[name] = current_time
                else:
                    has_unknown = True
                    unknown_face_crop_b64 = camera_image_b64
            face_names.append((name, status))
            
        if has_unknown:
            if unknown_start_time is None:
                unknown_start_time = datetime.now()
            elif not unknown_alert_sent and (datetime.now() - unknown_start_time).total_seconds() > 3:
                eventlet.spawn(send_security_alert, unknown_face_crop_b64)
                log_access("Unknown", "Intruder", None, False, "INTRUDER")
                speak("Warning. Unknown person detected.")
                unknown_alert_sent = True
        else:
            unknown_start_time = None
            unknown_alert_sent = False

        for (top, right, bottom, left), (name, status) in zip(face_locations, face_names):
            top *= 4; right *= 4; bottom *= 4; left *= 4
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

        cv2.imshow('Smart Reception Server', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        
        eventlet.sleep(0.01)

    video_capture.release()
    cv2.destroyAllWindows()

# --- Socket API для инициализации карты ---
@socketio.on('request_map_state')
def handle_map_state():
    state = []
    for user_name, loc in user_locations.items():
        state.append({
            'name': user_name,
            'location': loc,
            'image': user_avatars.get(user_name, '')
        })
    socketio.emit('map_state', state)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logs')
def get_logs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, name, status, temperature, access_granted, action_type FROM access_logs ORDER BY id DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()
    
    logs = []
    for row in rows:
        logs.append({
            'timestamp': row[0],
            'name': row[1],
            'status': row[2],
            'temperature': row[3],
            'access_granted': bool(row[4]),
            'action_type': row[5]
        })
    return jsonify(logs)

if __name__ == '__main__':
    threading.Thread(target=camera_loop, daemon=True).start()
    try:
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        pass
