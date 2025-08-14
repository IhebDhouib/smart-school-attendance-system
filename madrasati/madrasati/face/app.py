import face_recognition
import cv2
import numpy as np
import os
import datetime
import uuid
import csv
import threading
import time
import requests
import json
from collections import Counter
from utils_copy import load_config, validate_encodings
import pickle
import websocket

# 📁 Chemins
ENCODINGS_FILE = "encodings.pkl"
UNKNOWN_DIR = "unknown_faces"
LOG_FILE = "logs/logs.csv"

# Backend configuration
BACKEND_URL = "http://localhost:3000"
WEBSOCKET_URL = "ws://localhost:3001"

# 📂 Dossiers requis
os.makedirs(UNKNOWN_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# 🧠 Charger les encodages connus
try:
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
        known_encodings = data["encodings"]
        known_names = data["names"]
    validation_stats = validate_encodings(verbose=True)
    if not validation_stats['valid']:
        print("❌ Encodages non valides. Exécutez encode_faces_copy.py.")
        exit(1)
    print(f"✅ {len(known_encodings)} encodages chargés pour {validation_stats['unique_persons']} personnes.")
except FileNotFoundError:
    print("❌ Fichier encodings.pkl non trouvé. Exécutez d'abord encode_faces_copy.py.")
    exit(1)
except Exception as e:
    print(f"❌ Erreur lors du chargement des encodages: {e}")
    exit(1)

# 📝 Variables de suivi
presence = {}
last_recognition = {}
frame_count = 0
absence_start = {}

# WebSocket connection
ws = None

def connect_websocket():
    """Connect to WebSocket server"""
    global ws
    try:
        ws = websocket.WebSocket()
        ws.connect(WEBSOCKET_URL)
        print(f"✅ Connected to WebSocket server at {WEBSOCKET_URL}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to WebSocket: {e}")
        ws = None
        return False

def send_attendance_data(student_matricule, timestamp):
    """Send attendance data to backend via WebSocket"""
    global ws
    try:
        if ws is None:
            if not connect_websocket():
                return False
        
        # Format timestamp as required by backend (YYYY-MM-DD HH:MM)
        formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M")
        
        data = {
            "studentId": student_matricule,
            "timestamp": formatted_timestamp
        }
        
        ws.send(json.dumps(data))
        
        # Wait for response
        response = ws.recv()
        response_data = json.loads(response)
        
        if "error" in response_data:
            print(f"❌ Backend error: {response_data['error']}")
            return False
        else:
            print(f"✅ Attendance sent to backend: {response_data.get('message', 'Success')}")
            return True
            
    except Exception as e:
        print(f"❌ Error sending attendance data: {e}")
        # Try to reconnect
        ws = None
        return False

# 📄 Fonction pour journaliser une action
def log_event(name, action):
    """Enregistre un événement dans le fichier CSV"""
    now = datetime.datetime.now()
    try:
        # Vérifier la structure du fichier CSV
        file_exists = os.path.exists(LOG_FILE)
        expected_headers = ["Nom", "Action", "DateTime"]
        if file_exists:
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers and headers != expected_headers:
                    print("⚠️ Structure CSV incohérente. Réinitialisation du fichier.")
                    file_exists = False

        with open(LOG_FILE, mode="a" if file_exists else "w", newline="", encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(expected_headers)
            writer.writerow([name, action, now.strftime("%Y-%m-%d %H:%M:%S")])
        print(f"📝 Log: {name} - {action}")
    except Exception as e:
        print(f"❌ Erreur log: {e}")

# 🔁 Thread pour quitter via terminal
stop_flag = threading.Event()

def listen_for_quit():
    """Thread pour écouter la commande 'quit' dans le terminal"""
    while not stop_flag.is_set():
        try:
            cmd = input().strip().lower()
            if cmd == "quit":
                print("⛔ Commande 'quit' reçue. Arrêt du programme...")
                stop_flag.set()
                break
            elif cmd == "stats":
                print(f"📊 Statistiques: {frame_count} frames traitées")
                print(f"👥 Personnes présentes: {list(presence.keys())}")
            elif cmd == "reconnect":
                print("🔄 Reconnexion au WebSocket...")
                connect_websocket()
        except (EOFError, KeyboardInterrupt):
            break

listener_thread = threading.Thread(target=listen_for_quit, daemon=True)
listener_thread.start()

# 📷 Configuration caméra
def initialize_camera():
    """Initialise la caméra (IP puis locale)"""
    camera_sources = [
        "http://192.168.1.67:5001/video",  # Caméra IP
        0  # Caméra locale
    ]
    
    for source in camera_sources:
        print(f"🔄 Tentative de connexion à la caméra: {source}")
        try:
            if isinstance(source, str):
                cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            else:
                cap = cv2.VideoCapture(source)
            
            ret, frame = cap.read()
            if ret and cap.isOpened():
                print(f"✅ Caméra connectée: {source}")
                return cap
            else:
                cap.release()
        except Exception as e:
            print(f"❌ Erreur caméra {source}: {e}")
    
    return None

cap = initialize_camera()
if not cap:
    print("❌ Impossible de se connecter à une caméra.")
    exit(1)

# Connect to WebSocket
connect_websocket()

# Charger la configuration
config = load_config()
recognition_cooldown = config.get("recognition_cooldown", 30)
tolerance = config.get("tolerance", 0.3)
scale_factor = config.get("scale_factor", 0.5)
model = config.get("model", "cnn")

print("🎬 Démarrage de la reconnaissance faciale...")
print("💡 Commandes:")
print("  - Tapez 'quit' dans le terminal pour quitter")
print("  - Tapez 'stats' pour voir les statistiques")
print("  - Tapez 'reconnect' pour reconnecter au WebSocket")
print("  - Appuyez sur 'q' dans la fenêtre vidéo pour quitter")
print("  - Appuyez sur 's' pour sauvegarder une capture")

import threading
import queue

# Initialize a queue to store detection results
detection_queue = queue.Queue()

def detect_faces(frame, model, queue):
    # Avant la détection (dans if frame_count % 4 == 0 :)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced_gray = clahe.apply(gray)
    enhanced_frame = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
    rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)  # Utilisez enhanced_frame au lieu de frame
    locations = face_recognition.face_locations(rgb_frame, model=model, number_of_times_to_upsample=1)
    encodings = face_recognition.face_encodings(rgb_frame, locations)
    queue.put((locations, encodings))
    
try:
    while cap.isOpened() and not stop_flag.is_set():
        ret, frame = cap.read()
        # Ajoutez après la lecture du frame (ret, frame = cap.read())
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])  # Filtre de netteté simple
        frame = cv2.filter2D(frame, -1, kernel)
        if not ret:
            print("⚠️ Erreur lecture caméra")
            time.sleep(1)
            continue

        frame_count += 1
        names = []
        face_locations = []

        # Process every 4th frame in a separate thread
        if frame_count % 4 == 0:
            # Clear queue to avoid backlog
            while not detection_queue.empty():
                detection_queue.get()
            # Start detection in a thread
            threading.Thread(target=detect_faces, args=(frame.copy(), model, detection_queue), daemon=True).start()

        # Check if detection results are available
        try:
            face_locations, face_encodings = detection_queue.get_nowait()
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
                name = "Inconnu"
                confidence = 0.0
                face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    best_distance = face_distances[best_match_index]
                    if matches[best_match_index] and best_distance < tolerance:
                        name = known_names[best_match_index]
                        confidence = 1 - best_distance
                        print(f"🎯 Reconnu: {name} (confiance: {confidence:.3f}, distance: {best_distance:.3f})")
                    else:
                        print(f"🔍 Visage détecté mais non reconnu (meilleure distance: {best_distance:.3f})")
                names.append(name)
        except queue.Empty:
            pass  # Use previous frame's results if no new detection
        current_time = datetime.datetime.now()
        
        for (top, right, bottom, left), name in zip(face_locations, names):
            top = int(top)  # No division by scale_factor
            right = int(right)
            bottom = int(bottom)
            left = int(left)

            color = (0, 255, 0) if name != "Inconnu" else (0, 0, 255)
            text_color = (255, 255, 255)

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.8, text_color, 1)

            if name != "Inconnu":
                should_log = False
                
                if name not in last_recognition:
                    should_log = True
                elif (current_time - last_recognition[name]).total_seconds() > recognition_cooldown:
                    should_log = True
                
                if should_log:
                    if name not in presence:
                        presence[name] = {"entrée": current_time, "sortie": None}
                        log_event(name, "entrée")
                        print(f"✅ Entrée enregistrée: {name}")
                        
                        # Send attendance data to backend
                        send_attendance_data(name, current_time)
                        
                    else:
                        presence[name]["sortie"] = current_time
                    
                    last_recognition[name] = current_time
                    absence_start.pop(name, None)
            
            else:
                if config.get("save_unknown_faces", True) and frame_count % 30 == 0:
                    unknown_id = str(uuid.uuid4())[:8]
                    timestamp = current_time.strftime('%Y%m%d_%H%M%S')
                    unknown_name = f"inconnu_{unknown_id}_{timestamp}"
                    
                    face_image = frame[max(0, top-20):min(frame.shape[0], bottom+20), 
                                     max(0, left-20):min(frame.shape[1], right+20)]
                    
                    if face_image.size > 0:
                        filename = os.path.join(UNKNOWN_DIR, f"{unknown_name}.jpg")
                        cv2.imwrite(filename, face_image)
                        log_event(unknown_name, "visage_inconnu_détecté")
                        print(f"📷 Visage inconnu sauvegardé: {filename}")

        for name in list(presence.keys()):
            if name == "Inconnu" or name in names:
                continue

            if name not in absence_start:
                absence_start[name] = current_time
            else:
                absence_duration = (current_time - absence_start[name]).total_seconds()
                if absence_duration >= recognition_cooldown:
                    if presence[name]["sortie"]:
                        duration = presence[name]["sortie"] - presence[name]["entrée"]
                        log_event(name, f"sortie (durée: {duration})")
                        print(f"📤 Sortie enregistrée: {name} (durée: {duration})")
                    else:
                        log_event(name, "sortie_automatique")
                        print(f"📤 Sortie automatique: {name}")
                    presence.pop(name)
                    last_recognition.pop(name, None)
                    absence_start.pop(name, None)

        # Display connection status
        ws_status = "🟢 Connected" if ws else "🔴 Disconnected"
        info_text = f"Frame: {frame_count} | Personnes: {len([n for n in names if n != 'Inconnu'])} | WS: {ws_status}"
        cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        time_text = current_time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, time_text, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("🎥 Reconnaissance faciale - Appuyez sur 'q' pour quitter", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("⌨️ Touche 'q' pressée.")
            break
        elif key == ord("s"):
            timestamp = current_time.strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"📸 Capture sauvegardée: {filename}")
        elif key == ord("r"):
            last_recognition.clear()
            absence_start.clear()
            print("🔄 Reset des reconnaissances effectué")


except KeyboardInterrupt:
    print("⌨️ Ctrl+C détecté. Arrêt immédiat...")

finally:
    print("\n📝 Finalisation des logs de présence...")
    final_time = datetime.datetime.now()
    
    for name, times in presence.items():
        if name.startswith("inconnu_"):
            continue
            
        if times["sortie"]:
            duration = times["sortie"] - times["entrée"]
            log_event(name, f"sortie (durée: {duration})")
            print(f"📤 Sortie enregistrée: {name} (durée: {duration})")
        else:
            log_event(name, "sortie_automatique")
            print(f"📤 Sortie automatique: {name}")

    # Close WebSocket connection
    if ws:
        ws.close()
        print("🔌 WebSocket connection closed")

    cap.release()
    cv2.destroyAllWindows()
    stop_flag.set()
    
    print("✅ Programme terminé proprement.")
    print(f"📊 Statistiques finales:")
    print(f"  - {frame_count} frames traitées")
    print(f"  - {len(presence)} personnes détectées")
    print(f"  - Logs sauvegardés dans {LOG_FILE}")