import face_recognition
import cv2
import numpy as np
import os
import datetime
import csv
import threading
import time
import requests
import json
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

def send_attendance_data(student_matricule, timestamp, camera_type):
    """Send attendance data to backend via WebSocket"""
    global ws
    try:
        if ws is None:
            if not connect_websocket():
                return False
        
        formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M")
        data = {
            "studentId": student_matricule,
            "timestamp": formatted_timestamp,
            "camera_type":camera_type
        }
        ws.send(json.dumps(data))
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
        ws = None
        return False

def log_event(name, action):
    """Enregistre un événement dans le fichier CSV"""
    now = datetime.datetime.now()
    try:
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
                print(f"🔄 Reconnexion au WebSocket...")
                connect_websocket()
        except (EOFError, KeyboardInterrupt):
            break

listener_thread = threading.Thread(target=listen_for_quit, daemon=True)
listener_thread.start()

def initialize_cameras():
    """Initialise les caméras (IP puis locale) et retourne les objets cap pour l'entrée et la sortie"""
    camera_sources = {
        "entry": ["http://192.168.1.66:8080/video", 1],
        "exit": [0,"http://192.168.1.68:5001/video", 0]
    }
    
    caps = {}
    for cam_type, sources in camera_sources.items():
        print(f"🔄 Tentative de connexion à la caméra {cam_type}...")
        for source in sources:
            print(f"  Tentative avec source: {source}")
            try:
                if isinstance(source, str):
                    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                else:
                    cap = cv2.VideoCapture(source)
                
                ret, frame = cap.read()
                if ret and cap.isOpened():
                    print(f"✅ Caméra {cam_type} connectée: {source}")
                    caps[cam_type] = cap
                    break
                else:
                    cap.release()
            except Exception as e:
                print(f"❌ Erreur caméra {source} ({cam_type}): {e}")
        if cam_type not in caps:
            print(f"❌ Impossible de se connecter à la caméra {cam_type}.")
            return None, None
    
    return caps.get("entry"), caps.get("exit")

cap_entry, cap_exit = initialize_cameras()
if not cap_entry or not cap_exit:
    print("❌ Impossible de se connecter à toutes les caméras requises.")
    exit(1)

connect_websocket()

config = load_config()
recognition_cooldown = config.get("recognition_cooldown", 30)
tolerance = config.get("tolerance", 0.3)
scale_factor = config.get("scale_factor", 0.5)
model = config.get("model", "hog")  # Use "hog" for stability

print("🎬 Démarrage de la reconnaissance faciale...")
print("💡 Commandes:")
print("  - Tapez 'quit' dans le terminal pour quitter")
print("  - Tapez 'stats' pour voir les statistiques")
print("  - Tapez 'reconnect' pour reconnecter au WebSocket")
print("  - Appuyez sur 'q' dans la fenêtre vidéo pour quitter")
print("  - Appuyez sur 's' pour sauvegarder une capture")
print(f"🛠️ Utilisation du modèle: {model} (avec scale_factor: {scale_factor})")

def detect_faces(frame, model, camera_type, scale_factor=0.5):
    try:
        small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced_gray = clahe.apply(gray)
        enhanced_frame = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
        rgb_small_frame = np.ascontiguousarray(cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB))
        locations = face_recognition.face_locations(rgb_small_frame, model=model, number_of_times_to_upsample=1)
        encodings = face_recognition.face_encodings(rgb_small_frame, locations)
        locations = [(int(top / scale_factor), int(right / scale_factor), int(bottom / scale_factor), int(left / scale_factor)) for (top, right, bottom, left) in locations]
        return locations, encodings
    except Exception as e:
        print(f"❌ Erreur dans detect_faces ({camera_type}): {e}")
        if model == "cnn":
            print("⚠️ Échec du modèle 'cnn', tentative avec 'hog'...")
            return detect_faces(frame, "hog", camera_type, scale_factor)
        return [], []

def process_detection(face_locations, face_encodings, camera_type, current_time):
    names = []
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
                print(f"🎯 Reconnu: {name} (confiance: {confidence:.3f}, distance: {best_distance:.3f}) sur caméra {camera_type}")
            else:
                print(f"🔍 Visage détecté mais non reconnu (meilleure distance: {best_distance:.3f}) sur caméra {camera_type}")
        names.append(name)

        if name != "Inconnu":
            if camera_type == "entry":
                if name not in presence or presence[name]["status"] == "out":
                    presence[name] = {"entry_time": current_time, "exit_time": None, "status": "in", "lessons_attended": {}}
                    log_event(name, "entrée")
                    print(f"✅ Entrée enregistrée: {name} via caméra d'entrée")
                    send_attendance_data(name, current_time, "entry")
                last_recognition[name] = current_time
            elif camera_type == "exit":
                if name in presence and presence[name]["status"] == "in":
                    presence[name]["exit_time"] = current_time
                    presence[name]["status"] = "out"
                    log_event(name, "sortie")
                    print(f"📤 Sortie enregistrée: {name} via caméra de sortie")
                    send_attendance_data(name, current_time, "exit")
                last_recognition[name] = current_time

    return names

# Initialize per-camera detection results
entry_locations = []
entry_names = []
exit_locations = []
exit_names = []

# Create windows before loop
cv2.namedWindow("🎥 Caméra d'entrée", cv2.WINDOW_NORMAL)
cv2.namedWindow("🎥 Caméra de sortie", cv2.WINDOW_NORMAL)

try:
    while not stop_flag.is_set():
        current_time = datetime.datetime.now()
        
        ret_entry, frame_entry = cap_entry.read()
        ret_exit, frame_exit = cap_exit.read()

        if not ret_entry:
            print("⚠️ Erreur lecture caméra d'entrée, tentative de reconnexion...")
            cap_entry.release()
            cap_entry, _ = initialize_cameras()
            if not cap_entry:
                print("❌ Échec reconnexion caméra d'entrée.")
                break
            time.sleep(1)
            continue
        if not ret_exit:
            print("⚠️ Erreur lecture caméra de sortie, tentative de reconnexion...")
            cap_exit.release()
            _, cap_exit = initialize_cameras()
            if not cap_exit:
                print("❌ Échec reconnexion caméra de sortie.")
                break
            time.sleep(1)
            continue

        frame_count += 1
        
        if frame_count % 4 == 0:
            if ret_entry:
                entry_locations, entry_encodings = detect_faces(frame_entry, model, "entry", scale_factor)
                entry_names = process_detection(entry_locations, entry_encodings, "entry", current_time)
            if ret_exit:
                exit_locations, exit_encodings = detect_faces(frame_exit, model, "exit", scale_factor)
                exit_names = process_detection(exit_locations, exit_encodings, "exit", current_time)

        ws_status = "🟢 Connected" if ws else "🔴 Disconnected"
        time_text = current_time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            if ret_entry and frame_entry is not None:
                for (top, right, bottom, left), name in zip(entry_locations, entry_names):
                    top = int(top)
                    right = int(right)
                    bottom = int(bottom)
                    left = int(left)
                    color = (0, 255, 0) if name != "Inconnu" else (0, 0, 255)
                    cv2.rectangle(frame_entry, (left, top), (right, bottom), color, 2)
                    cv2.rectangle(frame_entry, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(frame_entry, name, (left + 6, bottom - 6), font, 0.8, (255, 255, 255), 1)
                info_text = f"Frame: {frame_count} | Personnes: {len([n for n in entry_names if n != 'Inconnu'])} | WS: {ws_status}"
                cv2.putText(frame_entry, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame_entry, time_text, (10, frame_entry.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.imshow("🎥 Caméra d'entrée", frame_entry)

            if ret_exit and frame_exit is not None:
                for (top, right, bottom, left), name in zip(exit_locations, exit_names):
                    top = int(top)
                    right = int(right)
                    bottom = int(bottom)
                    left = int(left)
                    color = (0, 255, 0) if name != "Inconnu" else (0, 0, 255)
                    cv2.rectangle(frame_exit, (left, top), (right, bottom), color, 2)
                    cv2.rectangle(frame_exit, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(frame_exit, name, (left + 6, bottom - 6), font, 0.8, (255, 255, 255), 1)
                info_text = f"Frame: {frame_count} | Personnes: {len([n for n in exit_names if n != 'Inconnu'])} | WS: {ws_status}"
                cv2.putText(frame_exit, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame_exit, time_text, (10, frame_exit.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.imshow("🎥 Caméra de sortie", frame_exit)
        except Exception as e:
            print(f"❌ Erreur lors de l'affichage: {e}")

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("⌨️ Touche 'q' pressée.")
            break
        elif key == ord("s"):
            timestamp = current_time.strftime("%Y%m%d_%H%M%S")
            if ret_entry:
                cv2.imwrite(f"capture_entry_{timestamp}.jpg", frame_entry)
                print(f"📸 Capture caméra d'entrée sauvegardée: capture_entry_{timestamp}.jpg")
            if ret_exit:
                cv2.imwrite(f"capture_exit_{timestamp}.jpg", frame_exit)
                print(f"📸 Capture caméra de sortie sauvegardée: capture_exit_{timestamp}.jpg")
        elif key == ord("r"):
            last_recognition.clear()
            absence_start.clear()
            print("🔄 Reset des reconnaissances effectué")

        time.sleep(0.01)  # Small delay to prevent CPU overload

except KeyboardInterrupt:
    print("❌ Interruption clavier (Ctrl+C) détectée.")
except Exception as e:
    print(f"❌ Erreur dans la boucle principale: {e}")
finally:
    print("🛑 Nettoyage des ressources...")
    cap_entry.release()
    cap_exit.release()
    cv2.destroyAllWindows()
    if ws:
        ws.close()
    print("🛑 Programme terminé.")