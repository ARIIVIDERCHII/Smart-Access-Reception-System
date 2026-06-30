import cv2
import face_recognition
import pyttsx3
import os
import numpy as np
from datetime import datetime

# Инициализация движка Text-to-Speech (генерация голоса)
engine = pyttsx3.init()
engine.setProperty('rate', 150) # Скорость речи

def speak(text):
    print(f"[Voice] {text}")
    engine.say(text)
    engine.runAndWait()

def load_database(db_path="database"):
    """Загружает фотографии из папки database и извлекает имена и статусы"""
    known_face_encodings = []
    known_face_info = []
    
    if not os.path.exists(db_path):
        print(f"Error: Папка '{db_path}' не найдена!")
        return known_face_encodings, known_face_info

    print("Загрузка базы данных лиц...")
    for filename in os.listdir(db_path):
        if filename.lower().endswith((".jpg", ".png", ".jpeg")):
            # Разбиваем имя файла: EBATA_Sensei.jpg -> ['EBATA', 'Sensei']
            name_parts = os.path.splitext(filename)[0].split('_')
            
            name = name_parts[0] if len(name_parts) > 0 else "Unknown"
            status = name_parts[1] if len(name_parts) > 1 else "Guest"
            
            # Загружаем изображение
            image_path = os.path.join(db_path, filename)
            image = face_recognition.load_image_file(image_path)
            
            # Получаем кодировку лица (encoding)
            encodings = face_recognition.face_encodings(image)
            
            if encodings:
                known_face_encodings.append(encodings[0])
                known_face_info.append({"name": name, "status": status})
                print(f" [+] Успешно загружен: {name} (Статус: {status})")
            else:
                print(f" [-] Внимание: Лицо не найдено на фото {filename}")
                
    return known_face_encodings, known_face_info

def generate_greeting(info):
    """Генерирует приветствие на основе имени и статуса"""
    name = info['name']
    status = info['status']
    
    # Получаем текущий день недели и время
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

def main():
    # 1. Загрузка лиц из базы данных
    known_face_encodings, known_face_info = load_database()
    
    if not known_face_encodings:
        print("В базе данных нет лиц. Пожалуйста, добавьте фото в папку database.")
        return
        
    # 2. Запуск веб-камеры
    print("\nЗапуск камеры... Нажмите 'q' для выхода.")
    video_capture = cv2.VideoCapture(0)
    
    greeted_recently = {}
    timeout_seconds = 10 # Не повторять приветствие одному и тому же человеку 10 секунд

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Не удалось получить изображение с камеры.")
            break
            
        # Уменьшаем кадр для более быстрого распознавания
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        # Конвертируем BGR (OpenCV) в RGB (face_recognition)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Находим все лица в текущем кадре
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        face_names = []
        
        for face_encoding in face_encodings:
            name = "Unknown"
            status = "Unknown"
            
            # Считаем "расстояние" до всех известных лиц
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                # Если сходство высокое (distance < 0.6 обычно считается совпадением)
                if face_distances[best_match_index] < 0.5:
                    info = known_face_info[best_match_index]
                    name = info['name']
                    status = info['status']
                    
                    # Проверяем, здоровались ли мы с этим человеком недавно
                    current_time = datetime.now()
                    if name not in greeted_recently or (current_time - greeted_recently[name]).total_seconds() > timeout_seconds:
                        greeting = generate_greeting(info)
                        speak(greeting)
                        greeted_recently[name] = current_time

            face_names.append((name, status))
            
        # 3. Отрисовка результатов на экране
        for (top, right, bottom, left), (name, status) in zip(face_locations, face_names):
            # Возвращаем координаты обратно к оригинальному размеру (т.к. мы уменьшали в 4 раза)
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Зеленый цвет для известных, красный для неизвестных
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            
            # Рамка вокруг лица
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Плашка с текстом
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            display_text = f"{name} ({status})" if name != "Unknown" else "Access Denied"
            cv2.putText(frame, display_text, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)

        cv2.imshow('Smart Reception System - AI Edge Prototype', frame)

        # Выход по нажатию 'q' (англ), 'й' (рус) или ESC (27)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('й') or key == 27:
            break

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрограмма остановлена пользователем (Ctrl+C).")
        cv2.destroyAllWindows()
