import eventlet
eventlet.monkey_patch() # Обязательно в самом начале для WebSockets

import cv2
import face_recognition
import pyttsx3
import os
import numpy as np
import base64
from datetime import datetime
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart_access_secret'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Инициализация движка Text-to-Speech
engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak(text):
    print(f"[Voice] {text}")
    engine.say(text)
    engine.runAndWait()

def load_database(db_path="database"):
    known_face_encodings = []
    known_face_info = []
    
    if not os.path.exists(db_path):
        print(f"Error: Папка '{db_path}' не найдена!")
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
                
                # Конвертируем исходное фото в base64 для отправки на фронтенд
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                image_b64 = f"data:image/jpeg;base64,{encoded_string}"
                
                known_face_info.append({"name": name, "status": status, "image_b64": image_b64})
                print(f" [+] Успешно загружен: {name} (Статус: {status})")
            else:
                print(f" [-] Внимание: Лицо не найдено на фото {filename}")
                
    return known_face_encodings, known_face_info

def generate_greeting(info):
    name = info['name']
    status = info['status']
    
    now = datetime.now()
    day_of_week = now.strftime("%A")
    current_time = now.strftime("%I:%M %p")
    time_str = f"Today is {day_of_week}, the time is {current_time}."
    
    if status.lower() == 'sensei' or status.lower() == 'teacher':
        return f"{name}-sensei, o-tsukaresama desu! Access granted. {time_str}"
    elif status.lower() == 'student':
        return f"Good morning, {name}. Access granted. {time_str} Have a productive day!"
    else:
        return f"Welcome, {name}. Access granted. {time_str}"

def camera_loop():
    """Фоновый поток для работы с камерой и распознавания лиц"""
    known_face_encodings, known_face_info = load_database()
    
    if not known_face_encodings:
        print("В базе данных нет лиц. Запуск остановлен.")
        return
        
    print("\nЗапуск камеры... (Фоновый поток)")
    video_capture = cv2.VideoCapture(0)
    
    greeted_recently = {}
    timeout_seconds = 15

    while True:
        ret, frame = video_capture.read()
        if not ret:
            # Пауза, если кадр не получен
            eventlet.sleep(0.1)
            continue
            
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        face_names = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            name = "Unknown"
            status = "Unknown"
            
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if face_distances[best_match_index] < 0.5:
                    info = known_face_info[best_match_index]
                    name = info['name']
                    status = info['status']
                    
                    current_time = datetime.now()
                    if name not in greeted_recently or (current_time - greeted_recently[name]).total_seconds() > timeout_seconds:
                        greeting = generate_greeting(info)
                        
                        # Вырезаем лицо из текущего кадра камеры
                        top, right, bottom, left = face_location
                        top *= 4; right *= 4; bottom *= 4; left *= 4
                        
                        # Добавляем отступы (padding) вокруг лица
                        padding = 60
                        crop_top = max(0, top - padding)
                        crop_bottom = min(frame.shape[0], bottom + padding)
                        crop_left = max(0, left - padding)
                        crop_right = min(frame.shape[1], right + padding)
                        
                        face_crop = frame[crop_top:crop_bottom, crop_left:crop_right]
                        
                        # Конвертируем снимок с камеры в Base64
                        _, buffer = cv2.imencode('.jpg', face_crop)
                        frame_b64 = base64.b64encode(buffer).decode('utf-8')
                        camera_image_b64 = f"data:image/jpeg;base64,{frame_b64}"
                        
                        # Отправляем событие на фронтенд (снимок с камеры)
                        print(f"Отправка сокета для {name} (с камеры)")
                        socketio.emit('face_recognized', {
                            'name': name,
                            'status': status,
                            'image': camera_image_b64
                        })
                        
                        # Блокирующий вызов голоса
                        speak(greeting)
                        greeted_recently[name] = current_time

            face_names.append((name, status))
            
        # Отрисовка видео-окна (опционально для сервера)
        for (top, right, bottom, left), (name, status) in zip(face_locations, face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            display_text = f"{name} ({status})" if name != "Unknown" else "Access Denied"
            cv2.putText(frame, display_text, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)

        cv2.imshow('Smart Reception Server View', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('й') or key == 27:
            break
        
        # Обязательно отдаем контроль eventlet, иначе вебсокеты повиснут
        eventlet.sleep(0.01)

    video_capture.release()
    cv2.destroyAllWindows()
    print("Камера остановлена. Нажмите Ctrl+C для выхода из сервера.")

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Запускаем поток с камерой
    threading.Thread(target=camera_loop, daemon=True).start()
    
    print("Запуск Flask-SocketIO сервера на http://localhost:5000 ...")
    try:
        # Отключаем встроенные логи Flask для чистоты вывода
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
