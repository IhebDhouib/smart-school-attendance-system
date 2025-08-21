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
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:3001")

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

# Configuration WebSocket
ws = None
ws_connected = False

def on_message(ws, message):
    print(f"📨 Message reçu: {message}")

def on_error(ws, error):
    print(f"❌ Erreur WebSocket: {error}")
    global ws_connected
    ws_connected = False

def on_close(ws, close_status_code, close_msg):
    print("🔌 Connexion WebSocket fermée")
    global ws_connected
    ws_connected = False

def on_open(ws):
    print("✅ Connexion WebSocket établie")
    global ws_connected
    ws_connected = True

def connect_websocket():
    """Établit la connexion WebSocket"""
    global ws, ws_connected
    try:
        ws = websocket.WebSocketApp(WEBSOCKET_URL,
                                  on_open=on_open,
                                  on_message=on_message,
                                  on_error=on_error,
                                  on_close=on_close)
        
        # Démarrer la connexion WebSocket dans un thread séparé
        ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
        ws_thread.start()
        
        # Attendre un peu pour la connexion
        time.sleep(2)
        
    except Exception as e:
        print(f"❌ Erreur lors de la connexion WebSocket: {e}")
        ws_connected = False

def send_websocket_message(message):
    """Envoie un message via WebSocket"""
    global ws, ws_connected
    try:
        if ws_connected and ws:
            ws.send(json.dumps(message))
            return True
    except Exception as e:
        print(f"❌ Erreur envoi WebSocket: {e}")
        ws_connected = False
    return False

def log_attendance(student_id, camera_type, confidence):
    """Enregistre la présence dans le fichier CSV et envoie au backend"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Écrire dans le fichier CSV
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([timestamp, student_id, camera_type, f"{confidence:.2f}"])
    
    # Préparer les données pour le backend
    attendance_data = {
        "studentId": student_id,
        "timestamp": timestamp,
        "cameraType": camera_type,
        "confidence": confidence
    }
    
    # Envoyer au backend via HTTP
    try:
        response = requests.post(f"{BACKEND_URL}/api/attendance", 
                               json=attendance_data, 
                               timeout=5)
        if response.status_code == 200:
            print(f"✅ Présence envoyée au backend: {student_id}")
        else:
            print(f"❌ Erreur backend: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur connexion backend: {e}")
    
    # Envoyer via WebSocket pour les mises à jour en temps réel
    websocket_data = {
        "type": "attendance",
        "data": attendance_data
    }
    
    if not send_websocket_message(websocket_data):
        print("❌ Échec envoi WebSocket")

def save_unknown_face(frame, face_location):
    """Sauvegarde un visage inconnu"""
    top, right, bottom, left = face_location
    face_image = frame[top:bottom, left:right]
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unknown_id = f"inconnu_{hash(str(face_location)) % 100000000:08x}"
    filename = f"{unknown_id}_{timestamp}.jpg"
    filepath = os.path.join(UNKNOWN_DIR, filename)
    
    cv2.imwrite(filepath, face_image)
    print(f"💾 Visage inconnu sauvegardé: {filename}")

def listen_for_quit():
    """Écoute les commandes clavier pour quitter"""
    while True:
        try:
            user_input = input().strip().lower()
            if user_input in ['q', 'quit', 'exit']:
                print("🛑 Arrêt demandé par l'utilisateur")
                os._exit(0)
        except:
            pass

# Démarrer le thread d'écoute
listener_thread = threading.Thread(target=listen_for_quit, daemon=True)
listener_thread.start()

def initialize_cameras():
    """Initialise les caméras (IP puis locale) et retourne les objets cap pour l'entrée et la sortie"""
    # Read camera sources from environment variables
    entry_cameras = []
    exit_cameras = []
    
    # Entry cameras
    if os.getenv("ENTRY_CAMERA_1"):
        entry_cameras.append(os.getenv("ENTRY_CAMERA_1"))
    if os.getenv("ENTRY_CAMERA_2"):
        try:
            entry_cameras.append(int(os.getenv("ENTRY_CAMERA_2")))
        except ValueError:
            entry_cameras.append(os.getenv("ENTRY_CAMERA_2"))
    
    # Exit cameras
    if os.getenv("EXIT_CAMERA_1"):
        try:
            exit_cameras.append(int(os.getenv("EXIT_CAMERA_1")))
        except ValueError:
            exit_cameras.append(os.getenv("EXIT_CAMERA_1"))
    if os.getenv("EXIT_CAMERA_2"):
        exit_cameras.append(os.getenv("EXIT_CAMERA_2"))
    if os.getenv("EXIT_CAMERA_3"):
        try:
            exit_cameras.append(int(os.getenv("EXIT_CAMERA_3")))
        except ValueError:
            exit_cameras.append(os.getenv("EXIT_CAMERA_3"))
    
    camera_sources = {
        "entry": entry_cameras,
        "exit": exit_cameras
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
                    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        print(f"✅ Caméra {cam_type} connectée avec succès: {source}")
                        caps[cam_type] = cap
                        break
                    else:
                        print(f"❌ Impossible de lire depuis: {source}")
                        cap.release()
                else:
                    print(f"❌ Impossible d'ouvrir: {source}")
                    cap.release()
                    
            except Exception as e:
                print(f"❌ Erreur avec {source}: {e}")
        
        if cam_type not in caps:
            print(f"❌ Aucune caméra fonctionnelle trouvée pour {cam_type}")
    
    return caps

def process_frame(frame, camera_type):
    """Traite une frame pour la reconnaissance faciale"""
    global frame_count
    frame_count += 1
    
    # Redimensionner pour améliorer les performances
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    # Détecter les visages
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
    
    for face_encoding, face_location in zip(face_encodings, face_locations):
        # Comparer avec les visages connus
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.6)
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            
            if matches[best_match_index]:
                name = known_names[best_match_index]
                confidence = 1 - face_distances[best_match_index]
                
                # Vérifier si c'est une nouvelle détection (éviter les doublons)
                current_time = time.time()
                if name not in last_recognition or current_time - last_recognition[name] > 30:
                    print(f"👤 {name} détecté sur caméra {camera_type} (confiance: {confidence:.2f})")
                    log_attendance(name, camera_type, confidence)
                    last_recognition[name] = current_time
                    presence[name] = current_time
            else:
                # Visage inconnu
                if frame_count % 30 == 0:  # Sauvegarder seulement toutes les 30 frames
                    # Ajuster les coordonnées pour la frame originale
                    top, right, bottom, left = face_location
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    save_unknown_face(frame, (top, right, bottom, left))

def main():
    """Fonction principale"""
    print("🚀 Démarrage du système de reconnaissance faciale...")
    
    # Établir la connexion WebSocket
    connect_websocket()
    
    # Initialiser les caméras
    caps = initialize_cameras()
    
    if not caps:
        print("❌ Aucune caméra disponible. Arrêt du programme.")
        return
    
    print("🎥 Démarrage de la reconnaissance faciale...")
    print("💡 Tapez 'q' ou 'quit' pour arrêter le programme")
    
    try:
        while True:
            for camera_type, cap in caps.items():
                ret, frame = cap.read()
                if ret:
                    process_frame(frame, camera_type)
                else:
                    print(f"❌ Erreur lecture caméra {camera_type}")
                    # Tentative de reconnexion
                    cap.release()
                    time.sleep(1)
                    new_caps = initialize_cameras()
                    if camera_type in new_caps:
                        caps[camera_type] = new_caps[camera_type]
                        print(f"✅ Caméra {camera_type} reconnectée")
            
            time.sleep(0.1)  # Petite pause pour éviter la surcharge CPU
            
    except KeyboardInterrupt:
        print("\n🛑 Arrêt par Ctrl+C")
    finally:
        # Nettoyer les ressources
        for cap in caps.values():
            cap.release()
        cv2.destroyAllWindows()
        if ws:
            ws.close()
        print("🧹 Ressources nettoyées")

if __name__ == "__main__":
    main()

