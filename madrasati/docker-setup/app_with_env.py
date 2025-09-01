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
import pickle
import websocket
import sys
from collections import Counter


# 📁 Chemins
ENCODINGS_FILE = "/app/encodings/encodings.pkl"
UNKNOWN_DIR = "unknown_faces"
LOG_FILE = "logs/logs.csv"

# Backend configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:3000")
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://backend:3001")

def load_encodings():
    try:
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            return data["encodings"], data["names"]
    except Exception as e:
        print(f"❌ Erreur lors du rechargement des encodages: {e}")
        return [], []

def validate_encodings(verbose=True):
    """Valide le fichier d'encodages et affiche des statistiques"""
    stats = {
        'valid': False,
        'total_encodings': 0,
        'unique_persons': 0,
        'avg_encodings_per_person': 0,
        'persons': {}
    }
    
    try:
        encodings, names = load_encodings()
        
        if not encodings or not names:
            if verbose:
                print("❌ Aucun encodage trouvé.")
            return stats
        
        if len(encodings) != len(names):
            if verbose:
                print("❌ Incohérence: nombre d'encodages ≠ nombre de noms")
            return stats
        
        name_counts = Counter(names)
        stats['valid'] = True
        stats['total_encodings'] = len(encodings)
        stats['unique_persons'] = len(name_counts)
        stats['avg_encodings_per_person'] = len(encodings) / len(name_counts)
        stats['persons'] = dict(name_counts)
        
        if verbose:
            print(f"✅ Fichier d'encodages valide:")
            print(f"   - {stats['total_encodings']} encodages total")
            print(f"   - {stats['unique_persons']} personnes uniques")
            print(f"   - Moyenne: {stats['avg_encodings_per_person']:.1f} encodages par personne")
            
            print("\n📊 Répartition:")
            for name, count in name_counts.most_common():
                print(f"   - {name}: {count} encodages")
        
        return stats
        
    except Exception as e:
        if verbose:
            print(f"❌ Erreur lors de la validation: {e}")
        return stats

def fetch_saved_cameras():
    """Récupère les caméras sauvegardées depuis la base de données"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/cameras", timeout=10)
        if response.status_code == 200:
            cameras = response.json()
            print(f"✅ {len(cameras)} caméra(s) récupérée(s) depuis la base de données")
            return cameras
        else:
            print(f"❌ Erreur API caméras: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des caméras: {e}")
        return []

def build_camera_url(camera):
    """Construit l'URL complète d'une caméra depuis les données de la DB"""
    try:
        ip = camera.get('ip')
        port = camera.get('port', 8080)
        username = camera.get('username', '')
        password = camera.get('password', '')
        
        if not ip:
            return None
            
        # Construire l'URL avec ou sans authentification
        if username and password:
            url = f"http://{username}:{password}@{ip}:{port}/video"
        else:
            url = f"http://{ip}:{port}/video"
            
        return url
    except Exception as e:
        print(f"❌ Erreur construction URL caméra: {e}")
        return None

def validate_encodings_with_database():
    """Validate that encoded students exist in the database"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/students", timeout=10)
        if response.status_code == 200:
            students = response.json()
            active_matricules = set(str(student.get('matricule')) for student in students if student.get('matricule'))
            
            # Check how many encoded students are still active
            encoded_students = set(str(name) for name in known_names)
            active_encoded = encoded_students.intersection(active_matricules)
            inactive_encoded = encoded_students - active_matricules
            
            print(f"📊 Validation des encodages avec la base de données:")
            print(f"   Étudiants encodés: {len(encoded_students)}")
            print(f"   Étudiants actifs en DB: {len(active_matricules)}")
            print(f"   Encodages valides: {len(active_encoded)}")
            
            if inactive_encoded:
                print(f"⚠️  Encodages obsolètes détectés: {len(inactive_encoded)} étudiants")
                print(f"   Étudiants supprimés: {', '.join(sorted(list(inactive_encoded)))}")
                print(f"💡 Recommandation: Exécutez 'python sync_encodings_with_db.py' pour nettoyer")
                return False
            else:
                print(f"✅ Tous les encodages correspondent à des étudiants actifs")
                return True
        else:
            print(f"⚠️  Impossible de valider avec la DB (erreur {response.status_code})")
            return True  # Continue anyway
    except Exception as e:
        print(f"⚠️  Erreur validation DB: {e}")
        return True  # Continue anyway

# 📂 Dossiers requis
os.makedirs(UNKNOWN_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# 🧠 Charger les encodages connus
known_encodings = []
known_names = []

try:
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
        known_encodings = data["encodings"]
        known_names = data["names"]
    validation_stats = validate_encodings(verbose=True)
    if not validation_stats['valid']:
        print("⚠️  Encodages non valides ou vides. Le système démarrera en mode attente.")
        print("💡 Ajoutez des étudiants via l'interface web pour générer les encodages.")
        known_encodings = []
        known_names = []
    else:
        print(f"✅ {len(known_encodings)} encodages chargés pour {validation_stats['unique_persons']} personnes.")

    # Validate encodings against database and auto-sync if needed
    try:
        response = requests.get(f"{BACKEND_URL}/api/students", timeout=10)
        if response.status_code == 200:
            students = response.json()
            active_matricules = set(str(student.get('matricule')) for student in students if student.get('matricule'))
            encoded_students = set(str(name) for name in known_names)
            active_encoded = encoded_students.intersection(active_matricules)
            inactive_encoded = encoded_students - active_matricules
            print(f"📊 Validation des encodages avec la base de données:")
            print(f"   Étudiants encodés: {len(encoded_students)}")
            print(f"   Étudiants actifs en DB: {len(active_matricules)}")
            print(f"   Encodages valides: {len(active_encoded)}")
            if inactive_encoded:
                print(f"⚠️  Encodages obsolètes détectés: {len(inactive_encoded)} étudiants")
                print(f"   Étudiants supprimés: {', '.join(sorted(list(inactive_encoded)))}")
                print(f"💡 Synchronisation automatique des encodages...")
                os.system("python3 /app/sync_encodings_with_db.py")
                # Reload encodings after sync
                with open(ENCODINGS_FILE, "rb") as f:
                    data = pickle.load(f)
                    known_encodings = data["encodings"]
                    known_names = data["names"]
                print(f"✅ Encodages synchronisés et rechargés.")
            else:
                print(f"✅ Tous les encodages correspondent à des étudiants actifs")
        else:
            print(f"⚠️  Impossible de valider avec la DB (erreur {response.status_code})")
    except Exception as e:
        print(f"⚠️  Erreur validation DB: {e}")
except FileNotFoundError:
    print("⚠️  Fichier encodings.pkl non trouvé. Le système démarrera en mode attente.")
    print("💡 Ajoutez des étudiants via l'interface web pour générer les encodages automatiquement.")
    known_encodings = []
    known_names = []
except Exception as e:
    print(f"⚠️  Erreur lors du chargement des encodages: {e}")
    print("💡 Le système démarrera avec des encodages vides.")
    known_encodings = []
    known_names = []

# 📝 Variables de suivi
presence = {}
last_recognition = {}
frame_count = 0


# Configuration WebSocket
ws = None
ws_connected = False

# Shutdown event for clean thread exit
shutdown_event = threading.Event()

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

def verify_student_exists(student_id):
    """Verify if student exists in database before logging attendance"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/students", timeout=5)
        if response.status_code == 200:
            students = response.json()
            student_matricules = [str(student.get('matricule')) for student in students if student.get('matricule')]
            return str(student_id) in student_matricules
        else:
            print(f"⚠️  Impossible de vérifier l'étudiant {student_id} (erreur {response.status_code})")
            return True  # Continue anyway if API is down
    except Exception as e:
        print(f"⚠️  Erreur vérification étudiant {student_id}: {e}")
        return True  # Continue anyway if connection fails

def log_attendance(student_id, camera_type, confidence):
    """Enregistre la présence dans le fichier CSV et envoie au backend"""
    
    # Verify student exists in database first
    if not verify_student_exists(student_id):
        print(f"⚠️  Étudiant {student_id} non trouvé en base de données - présence ignorée")
        return
    
    now = datetime.datetime.now()
    timestamp_csv = now.strftime("%Y-%m-%d %H:%M:%S")
    timestamp_backend = now.strftime("%Y-%m-%d %H:%M")  # Format attendu par le backend
    timestamp_iso = now.isoformat()
    
    # Écrire dans le fichier CSV
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([timestamp_csv, student_id, camera_type, f"{confidence:.2f}"])
    
    # Envoyer via WebSocket pour les mises à jour en temps réel
    websocket_data = {
        "studentId": student_id,
        "timestamp": timestamp_backend,  # Format YYYY-MM-DD HH:MM
        "camera_type": camera_type,  # Changed to camera_type for WebSocket
        "confidence": confidence
    }
    
    if send_websocket_message(websocket_data):
        print(f"✅ Présence envoyée via WebSocket: {student_id}")
    else:
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
    while not shutdown_event.is_set():
        try:
            user_input = input().strip().lower()
            if user_input in ['q', 'quit', 'exit']:
                print("🛑 Arrêt demandé par l'utilisateur")
                shutdown_event.set()
                break
        except:
            pass


# Démarrer le thread d'écoute
listener_thread = threading.Thread(target=listen_for_quit)
listener_thread.start()

def initialize_cameras():
    """Initialise les caméras (DB puis env) et retourne les objets cap pour l'entrée et la sortie"""
    
    # 1. Essayer de récupérer les caméras sauvegardées
    saved_cameras = fetch_saved_cameras()
    
    # 2. Préparer les sources de caméras
    entry_cameras = []
    exit_cameras = []
    
    # 3. Ajouter les caméras sauvegardées (actives seulement) basé sur le type
    active_cameras = [cam for cam in saved_cameras if cam.get('status') == 'active']
    
    for camera in active_cameras:
        camera_url = build_camera_url(camera)
        if camera_url:
            camera_name = camera.get('name', 'Camera')
            camera_type = camera.get('type', 'entry')  # Utiliser le champ type
            
            # Associer les caméras selon le type défini dans la DB
            if camera_type == 'entry':
                entry_cameras.append(camera_url)
                print(f"📹 Caméra d'entrée ajoutée: {camera_name} ({camera_url})")
            elif camera_type == 'exit':
                exit_cameras.append(camera_url)
                print(f"📹 Caméra de sortie ajoutée: {camera_name} ({camera_url})")
            else:
                # Fallback: si le type n'est pas reconnu, ajouter en entrée
                entry_cameras.append(camera_url)
                print(f"📹 Caméra ajoutée (entrée par défaut): {camera_name} ({camera_url})")
    
    # 4. Ajouter les caméras d'environnement comme fallback
    # Entry cameras from environment
    if os.getenv("ENTRY_CAMERA_1"):
        entry_cameras.append(os.getenv("ENTRY_CAMERA_1"))
    if os.getenv("ENTRY_CAMERA_2"):
        try:
            entry_cameras.append(int(os.getenv("ENTRY_CAMERA_2")))
        except ValueError:
            entry_cameras.append(os.getenv("ENTRY_CAMERA_2"))
    
    # Exit cameras from environment
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

# === Encodings reload logic ===



# Shared variables for encodings
encodings_lock = threading.Lock()
known_encodings, known_names = load_encodings()

def encodings_reloader():
    global known_encodings, known_names
    last_mtime = None
    while not shutdown_event.is_set():
        try:
            mtime = os.path.getmtime(ENCODINGS_FILE)
        except Exception:
            mtime = None
        if mtime != last_mtime:
            new_encodings, new_names = load_encodings()
            with encodings_lock:
                known_encodings = new_encodings
                known_names = new_names
            print(f"🔄 Encodings reloaded at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            last_mtime = mtime
        shutdown_event.wait(10)


# Start the background thread
encodings_thread = threading.Thread(target=encodings_reloader)
encodings_thread.start()

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
    
    with encodings_lock:
        current_encodings = known_encodings
        current_names = known_names
    
    # Si aucun encodage n'est disponible, sauvegarder les visages comme inconnus
    if not current_encodings:
        if face_locations and frame_count % 30 == 0:  # Sauvegarder seulement toutes les 30 frames
            for face_location in face_locations:
                # Ajuster les coordonnées pour la frame originale
                top, right, bottom, left = face_location
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                save_unknown_face(frame, (top, right, bottom, left))
        return
    
    for face_encoding, face_location in zip(face_encodings, face_locations):
        # Comparer avec les visages connus
        matches = face_recognition.compare_faces(current_encodings, face_encoding, tolerance=0.6)
        face_distances = face_recognition.face_distance(current_encodings, face_encoding)
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = current_names[best_match_index]
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
    
    # Check if we have encodings
    if not known_encodings:
        print("⚠️  Aucun encodage disponible. Le système fonctionnera en mode détection seulement.")
        print("💡 Les visages détectés seront sauvegardés comme inconnus.")
    
    # Initialiser les caméras
    caps = initialize_cameras()
    
    if not caps:
        print("⚠️  Aucune caméra disponible. Le système continuera en mode API seulement.")
        print("💡 Vous pouvez ajouter des étudiants via l'interface web.")
        
        # Wait indefinitely to keep the container running for API access
        try:
            while not shutdown_event.is_set():
                time.sleep(10)
                # Check for new encodings periodically
                if not known_encodings:
                    new_encodings, new_names = load_encodings()
                    if new_encodings:
                        print("✅ Nouveaux encodages détectés! Tentative de démarrage des caméras...")
                        caps = initialize_cameras()
                        if caps:
                            break
        except KeyboardInterrupt:
            print("\n🛑 Arrêt par Ctrl+C")
            shutdown_event.set()
            return
    
    print("🎥 Démarrage de la reconnaissance faciale...")
    print("💡 Tapez 'q' ou 'quit' pour arrêter le programme")
    
    try:
        while not shutdown_event.is_set():
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
        shutdown_event.set()
    finally:
        # Nettoyer les ressources
        shutdown_event.set()
        for cap in caps.values():
            cap.release()
        cv2.destroyAllWindows()
        if ws:
            ws.close()
        # Join background threads
        listener_thread.join(timeout=2)
        encodings_thread.join(timeout=2)
        print("🧹 Ressources nettoyées")

if __name__ == "__main__":
    main()

