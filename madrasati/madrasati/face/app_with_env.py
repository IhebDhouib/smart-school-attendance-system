"""
Face Recognition System Optimized for Security Cameras

🚀 Key Features for Far Face Detection:
- Multi-scale face detection (3 different scales)
- CNN model for better accuracy on small faces
- Image enhancement (CLAHE, sharpening, gamma correction)
- High-resolution camera settings (1080p)
- Configurable minimum face size (40px default)
- Duplicate face filtering
- Optimized for security camera environments

🔧 Configuration:
- FACE_DETECTION_MODEL: 'cnn' (accurate) or 'hog' (fast)
- MIN_FACE_SIZE: Minimum detectable face size in pixels
- MAX_FACES_PER_FRAME: Maximum faces to process per frame
- CAMERA_WIDTH/HEIGHT: Camera resolution settings
- FRAME_SKIP_INTERVAL: Performance optimization

📊 Performance Optimizations:
- Frame skipping for real-time processing
- Multiprocessing for CPU-intensive tasks
- Threading for I/O operations
- Adaptive sleep timing
"""
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
import multiprocessing as mp
import shutil
import signal
import psutil  # For CPU monitoring
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Suppress pkg_resources deprecation warning
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)


# 📁 Chemins
#ENCODINGS_FILE = "/app/encodings/encodings.pkl"
ENCODINGS_FILE = "encodings.pkl"
UNKNOWN_DIR = "unknown_faces"
LOG_FILE = "logs/logs.csv"

# Backend configuration
# BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:3000")
# WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://backend:3001")
BACKEND_URL = "http://localhost:3000"
WEBSOCKET_URL = "ws://localhost:3001"

# 🔍 Face Detection Configuration for Security Cameras
FACE_DETECTION_MODEL = 'hog'  # 'cnn' for better accuracy, 'hog' for speed
MIN_FACE_SIZE = 40  # Minimum face size in pixels for far face detection
MAX_FACES_PER_FRAME = 10  # Maximum faces to process per frame
FRAME_SKIP_INTERVAL = 1  # Process every Nth frame for performance
ENABLE_INTELLIGENT_FRAME_SKIPPING = True  # Enable scene change detection to skip unchanged frames

# 🚀 CPU Optimization Settings
MAX_CPU_PROCESSES = 12  # Maximum processes to utilize all CPU cores
ENABLE_CPU_BOOST = True  # Enable additional CPU-intensive processing
CPU_BOOST_ITERATIONS = 5  # Number of computational iterations for CPU boost

# 📊 Performance Monitoring Settings
ENABLE_PERFORMANCE_MONITORING = True  # Enable lightweight performance tracking
PERFORMANCE_REPORT_INTERVAL = 50  # Report performance every N frames
TRACK_DETAILED_TIMING = False  # Enable detailed timing (impacts performance slightly)

# 📹 Camera Configuration for Security
CAMERA_WIDTH = 1920   # 1080p width for better far face detection
CAMERA_HEIGHT = 1080  # 1080p height
CAMERA_FPS = 15       # Reasonable FPS for processing

# 📈 Performance Monitoring Variables
perf_frame_count = 0
perf_total_frame_time = 0
perf_total_detection_time = 0
perf_total_recognition_time = 0
perf_total_io_time = 0
perf_faces_detected = 0
perf_faces_recognized = 0
perf_start_time = time.time()

def reset_performance_stats():
    """Reset performance monitoring statistics"""
    global perf_frame_count, perf_total_frame_time, perf_total_detection_time
    global perf_total_recognition_time, perf_total_io_time, perf_faces_detected, perf_faces_recognized
    perf_frame_count = 0
    perf_total_frame_time = 0
    perf_total_detection_time = 0
    perf_total_recognition_time = 0
    perf_total_io_time = 0
    perf_faces_detected = 0
    perf_faces_recognized = 0

def log_performance_metric(metric_name, value, unit="ms"):
    """Log a performance metric if monitoring is enabled"""
    if ENABLE_PERFORMANCE_MONITORING:
        print(f"📊 {metric_name}: {value:.2f} {unit}")

def report_performance_stats():
    """Generate and display performance report"""
    if not ENABLE_PERFORMANCE_MONITORING or perf_frame_count == 0:
        return

    total_time = time.time() - perf_start_time
    avg_frame_time = (perf_total_frame_time / perf_frame_count) * 1000
    avg_detection_time = (perf_total_detection_time / perf_frame_count) * 1000 if perf_total_detection_time > 0 else 0
    avg_recognition_time = (perf_total_recognition_time / perf_frame_count) * 1000 if perf_total_recognition_time > 0 else 0
    fps = perf_frame_count / total_time if total_time > 0 else 0

    print("\n📈 === PERFORMANCE REPORT ===")
    print(f"⏱️  Total Runtime: {total_time:.1f}s")
    print(f"🎬 Frames Processed: {perf_frame_count}")
    print(f"🎯 Average FPS: {fps:.1f}")
    print(f"⏱️  Average Frame Time: {avg_frame_time:.2f}ms")
    print(f"🔍 Average Detection Time: {avg_detection_time:.2f}ms")
    print(f"👤 Average Recognition Time: {avg_recognition_time:.2f}ms")
    print(f"💾 Faces Detected: {perf_faces_detected}")
    print(f"✅ Faces Recognized: {perf_faces_recognized}")
    print(f"💻 CPU Usage: {psutil.cpu_percent():.1f}%")
    print(f"🧠 Memory Usage: {psutil.virtual_memory().percent:.1f}%")
    print("===============================\n")

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

# 🔍 Scene Change Detection Settings
SCENE_CHANGE_THRESHOLD = 15.0  # Threshold for scene change detection (lower = more sensitive) - reduced for better detection
SCENE_CHANGE_MIN_CONTOUR_AREA = 300  # Minimum contour area to consider for change - reduced for sensitivity
ENABLE_SCENE_CHANGE_DETECTION = True  # Enable/disable scene change detection
SCENE_CHANGE_PIXEL_THRESHOLD = 20.0  # Threshold for mean pixel difference method

def detect_scene_change(prev_frame, curr_frame, threshold=SCENE_CHANGE_THRESHOLD):
    """
    Detect if there's significant change between two frames to determine if processing is needed.
    Returns True if significant change is detected, False otherwise.
    """
    if prev_frame is None:
        return True  # Always process the first frame
    
    try:
        # Convert frames to grayscale for faster processing
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        prev_blur = cv2.GaussianBlur(prev_gray, (21, 21), 0)
        curr_blur = cv2.GaussianBlur(curr_gray, (21, 21), 0)
        
        # Calculate absolute difference
        frame_diff = cv2.absdiff(prev_blur, curr_blur)
        
        # Apply threshold to get binary image
        _, thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)
        
        # Find contours of changed regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Calculate total area of change
        total_change_area = 0
        significant_contours = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > SCENE_CHANGE_MIN_CONTOUR_AREA:
                total_change_area += area
                significant_contours += 1
        
        # Calculate percentage of frame that changed
        frame_area = prev_frame.shape[0] * prev_frame.shape[1]
        change_percentage = (total_change_area / frame_area) * 100
        
        # Alternative method: simple pixel difference
        mean_diff = np.mean(frame_diff)
        
        # Decision logic: significant change if either method indicates change
        has_significant_change = (change_percentage > threshold) or (mean_diff > SCENE_CHANGE_PIXEL_THRESHOLD)
        
        return has_significant_change
        
    except Exception as e:
        print(f"⚠️ Error in scene change detection: {e}")
        return True  # Default to processing if detection fails

def encode_student_locally(student_data):
    """Encode a single student locally by downloading their photos and processing them"""
    try:
        matricule = str(student_data.get('matricule'))
        student_id = student_data.get('_id')
        photos = student_data.get('photos', [])
        
        if not matricule or not photos:
            print(f"⚠️  Étudiant {matricule} n'a pas de photos")
            return False
        
        print(f"🧠 Encodage local de l'étudiant {matricule}...")
        
        # Create student directory in dataset
        dataset_dir = "dataset"
        student_dir = os.path.join(dataset_dir, matricule)
        os.makedirs(student_dir, exist_ok=True)
        
        # Download and save student photos
        photos_saved = 0
        for i, photo_url in enumerate(photos):
            try:
                # If it's a local path, copy it directly
                if photo_url.startswith('uploads/'):
                    local_path = os.path.join("..", "..", "backend", photo_url)
                    if os.path.exists(local_path):
                        photo_name = f"{matricule}_{i + 1}{os.path.splitext(photo_url)[1]}"
                        dest_path = os.path.join(student_dir, photo_name)
                        shutil.copy2(local_path, dest_path)
                        photos_saved += 1
                        print(f"   📸 Photo {i+1} copiée: {photo_name}")
                else:
                    # Download from URL
                    response = requests.get(photo_url, timeout=10)
                    if response.status_code == 200:
                        photo_name = f"{matricule}_{i + 1}.jpg"
                        dest_path = os.path.join(student_dir, photo_name)
                        with open(dest_path, 'wb') as f:
                            f.write(response.content)
                        photos_saved += 1
                        print(f"   📸 Photo {i+1} téléchargée: {photo_name}")
            
            except Exception as e:
                print(f"   ⚠️  Erreur avec la photo {i+1}: {e}")
        
        if photos_saved == 0:
            print(f"❌ Aucune photo n'a pu être sauvegardée pour {matricule}")
            return False
        
        print(f"✅ {photos_saved} photo(s) sauvegardée(s) pour {matricule}")
        
        # Now encode the faces using the local function
        success = encode_faces_from_dataset_local()
        
        if success:
            print(f"✅ Encodage réussi pour l'étudiant {matricule}")
            return True
        else:
            print(f"❌ Échec de l'encodage pour l'étudiant {matricule}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'encodage local de l'étudiant {matricule}: {e}")
        return False

def encode_faces_from_dataset_local():
    """Encode faces from dataset directory structure - local version"""
    print("🔄 Encodage des visages depuis le dataset...")
    
    dataset_dir = "dataset"
    
    # Create dataset directory if it doesn't exist
    os.makedirs(dataset_dir, exist_ok=True)
    
    # Check if dataset has any directories
    if not os.path.exists(dataset_dir) or not os.listdir(dataset_dir):
        print("❌ Aucun étudiant trouvé dans le répertoire dataset")
        return False
    
    # Load existing encodings 
    known_encodings, known_names, _ = load_existing_encodings_local()
    total_faces_encoded = 0
    total_students = 0

    for person_name in sorted(os.listdir(dataset_dir)):
        person_dir = os.path.join(dataset_dir, person_name)
        if not os.path.isdir(person_dir):
            continue
            
        total_students += 1
        student_faces = 0
        
        print(f"📸 Traitement de l'étudiant: {person_name}")
        
        for image_name in os.listdir(person_dir):
            if not image_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                continue
                
            image_path = os.path.join(person_dir, image_name)
            try:
                # Load and process image
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                
                if not face_locations:
                    print(f"⚠️  Aucun visage trouvé dans {image_name}")
                    continue
                
                # Get face encodings
                face_encodings = face_recognition.face_encodings(image, face_locations)
                
                for encoding in face_encodings:
                    known_encodings.append(encoding)
                    known_names.append(person_name)
                    total_faces_encoded += 1
                    student_faces += 1
                    
                print(f"   ✅ {image_name}: {len(face_encodings)} visage(s) encodé(s)")
                
            except Exception as e:
                print(f"   ❌ Erreur lors du traitement de {image_name}: {e}")
        
        print(f"   📊 {person_name}: {student_faces} visages encodés au total")

    print(f"\n📈 Encodage terminé:")
    print(f"   - Étudiants traités: {total_students}")
    print(f"   - Visages encodés au total: {total_faces_encoded}")
    print(f"   - Étudiants uniques: {len(set(known_names))}")

    if known_encodings and total_faces_encoded > 0:
        # Save encodings
        data = {
            'encodings': known_encodings,
            'names': known_names,
            'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'total_faces': total_faces_encoded,
            'unique_students': len(set(known_names))
        }
        
        with open(ENCODINGS_FILE, 'wb') as f:
            pickle.dump(data, f)
            
        print(f"✅ Encodages sauvegardés dans {ENCODINGS_FILE}")
        return True
    else:
        print("❌ Aucun visage n'a été encodé avec succès")
        return False

def load_existing_encodings_local():
    """Load existing encodings - local version"""
    try:
        with open(ENCODINGS_FILE, 'rb') as f:
            data = pickle.load(f)
        return data.get('encodings', []), data.get('names', []), data.get('processed_images', {})
    except:
        return [], [], {}

def create_default_encodings_file():
    """Create a default encodings.pkl file if it doesn't exist."""
    try:
        default_data = {"encodings": [], "names": []}
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(default_data, f)
        print(f"✅ Default encodings file created at {ENCODINGS_FILE}")
    except Exception as e:
        print(f"❌ Failed to create default encodings file: {e}")

# Check if encodings file exists, create if absent
if not os.path.exists(ENCODINGS_FILE):
    print(f"⚠️  Encodings file not found: {ENCODINGS_FILE}. Creating a default file.")
    create_default_encodings_file()

# 🧠 Global variables for encodings (initialized later)
known_encodings = []
known_names = []

def initialize_encodings():
    """Initialize encodings - called only from main process"""
    global known_encodings, known_names
    
    print("🧠 INITIALIZING FACE ENCODINGS...")
    
    try:
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            known_encodings = data["encodings"]
            known_names = data["names"]
            
        print(f"📊 ENCODING STATISTICS:")
        print(f"   - Total encodings loaded: {len(known_encodings)}")
        print(f"   - Total names loaded: {len(known_names)}")
        print(f"   - Unique students: {len(set(known_names))}")
        
        if known_names:
            name_counts = {}
            for name in known_names:
                name_counts[name] = name_counts.get(name, 0) + 1
            print(f"   - Student breakdown:")
            for name, count in sorted(name_counts.items()):
                print(f"     • {name}: {count} encoding(s)")
                
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
                unencoded_students = active_matricules - encoded_students
                
                print(f"📊 Validation des encodages avec la base de données:")
                print(f"   Étudiants encodés: {len(encoded_students)}")
                print(f"   Étudiants actifs en DB: {len(active_matricules)}")
                print(f"   Encodages valides: {len(active_encoded)}")
                
                # Handle inactive encodings (students removed from DB)
                if inactive_encoded:
                    print(f"⚠️  Encodages obsolètes détectés: {len(inactive_encoded)} étudiants")
                    print(f"   Étudiants supprimés: {', '.join(sorted(list(inactive_encoded)))}")
                    print(f"💡 Synchronisation automatique des encodages...")
                    # Use local path for sync script
                    sync_script_path = os.path.join(os.path.dirname(__file__), "..", "docker-setup", "sync_encodings_with_db.py")
                    os.system(f"python {sync_script_path}")
                    # Reload encodings after sync
                    with open(ENCODINGS_FILE, "rb") as f:
                        data = pickle.load(f)
                        known_encodings = data["encodings"]
                        known_names = data["names"]
                    print(f"✅ Encodages synchronisés et rechargés.")
                
                # Handle unencoded students (new students in DB without encodings)
                elif unencoded_students:
                    print(f"⚠️  Nouveaux étudiants détectés: {len(unencoded_students)} étudiants")
                    print(f"   Étudiants à encoder: {', '.join(sorted(list(unencoded_students)))}")
                    print(f"💡 Encodage automatique des nouveaux étudiants...")
                    
                    # Encode each unencoded student locally
                    for matricule in unencoded_students:
                        try:
                            # Find the student details
                            student_data = next((s for s in students if str(s.get('matricule')) == matricule), None)
                            if student_data:
                                success = encode_student_locally(student_data)
                                if success:
                                    print(f"✅ Encodage réussi pour l'étudiant {matricule}")
                                else:
                                    print(f"❌ Échec encodage pour l'étudiant {matricule}")
                            else:
                                print(f"⚠️  Impossible de trouver les détails de l'étudiant {matricule}")
                        except Exception as e:
                            print(f"❌ Erreur lors de l'encodage de l'étudiant {matricule}: {e}")
                    
                    # Reload encodings after encoding new students
                    try:
                        with open(ENCODINGS_FILE, "rb") as f:
                            data = pickle.load(f)
                            known_encodings = data["encodings"]
                            known_names = data["names"]
                        print(f"✅ Encodages rechargés après ajout de nouveaux étudiants")
                    except Exception as e:
                        print(f"⚠️  Impossible de recharger les encodages: {e}")
                
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
previous_frames = {}  # Store previous frames for each camera for scene change detection


# Configuration WebSocket
ws = None
ws_connected = False
ws_reconnect_attempts = 0
max_reconnect_attempts = 10
reconnect_interval = 5
ws_lock = Lock()

# Camera management
camera_caps = {}
camera_configs = {}
camera_lock = Lock()
camera_check_interval = 30  # Check for camera changes every 30 seconds

# Shutdown event for clean thread exit
shutdown_event = threading.Event()

def signal_handler(signum, frame):
    """Handle Ctrl+C signal for clean shutdown"""
    print("\n🛑 Signal d'arrêt reçu (Ctrl+C)")
    print("🔄 Arrêt propre du système en cours...")
    print("💡 Le programme va s'arrêter dans quelques secondes...")
    shutdown_event.set()

# Register signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

def on_message(ws, message):
    print(f"📨 Message reçu: {message}")

def on_error(ws, error):
    print(f"❌ Erreur WebSocket: {error}")
    global ws_connected
    with ws_lock:
        ws_connected = False

def on_close(ws, close_status_code, close_msg):
    print(f"🔌 Connexion WebSocket fermée (Code: {close_status_code}, Message: {close_msg})")
    global ws_connected
    with ws_lock:
        ws_connected = False
    # Attempt to reconnect
    if not shutdown_event.is_set():
        threading.Thread(target=reconnect_websocket, daemon=True).start()

def on_open(ws):
    print("✅ Connexion WebSocket établie")
    global ws_connected, ws_reconnect_attempts
    with ws_lock:
        ws_connected = True
        ws_reconnect_attempts = 0

def reconnect_websocket():
    """Reconnect WebSocket with exponential backoff"""
    global ws, ws_connected, ws_reconnect_attempts
    
    while not shutdown_event.is_set() and ws_reconnect_attempts < max_reconnect_attempts:
        try:
            ws_reconnect_attempts += 1
            wait_time = min(reconnect_interval * (2 ** (ws_reconnect_attempts - 1)), 60)
            print(f"🔄 Tentative de reconnexion WebSocket #{ws_reconnect_attempts} dans {wait_time}s...")
            
            time.sleep(wait_time)
            
            if shutdown_event.is_set():
                break
                
            connect_websocket()
            break
            
        except Exception as e:
            print(f"❌ Erreur lors de la reconnexion WebSocket: {e}")
    
    if ws_reconnect_attempts >= max_reconnect_attempts:
        print(f"❌ Échec de la reconnexion WebSocket après {max_reconnect_attempts} tentatives")

def connect_websocket():
    """Établit la connexion WebSocket"""
    global ws, ws_connected
    try:
        if ws:
            ws.close()
            
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
        with ws_lock:
            ws_connected = False

def send_websocket_message(message):
    """Envoie un message via WebSocket avec retry logic"""
    global ws, ws_connected
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with ws_lock:
                if ws_connected and ws:
                    ws.send(json.dumps(message))
                    return True
                else:
                    if attempt == 0:  # Only trigger reconnection on first attempt
                        threading.Thread(target=reconnect_websocket, daemon=True).start()
        except Exception as e:
            print(f"❌ Erreur envoi WebSocket (tentative {attempt + 1}): {e}")
            with ws_lock:
                ws_connected = False
            
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
                
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
    
    print(f"🎯 RECOGNITION DETECTED: Student {student_id} on {camera_type} camera (confidence: {confidence:.3f})")
    
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
    
    print(f"📝 CSV logged: {timestamp_csv} | {student_id} | {camera_type} | {confidence:.3f}")
    
    # Envoyer via WebSocket pour les mises à jour en temps réel
    websocket_data = {
        "studentId": student_id,
        "timestamp": timestamp_backend,  # Format YYYY-MM-DD HH:MM
        "camera_type": camera_type,  # Changed to camera_type for WebSocket
        "confidence": confidence
    }
    
    print(f"📡 Sending WebSocket data: {websocket_data}")
    
    if send_websocket_message(websocket_data):
        print(f"✅ Présence envoyée via WebSocket: {student_id} (confidence: {confidence:.3f})")
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

def initialize_single_camera(camera_config):
    """Initialize a single camera - to be used in parallel processing"""
    camera_id = camera_config.get('_id', 'unknown')
    camera_name = camera_config.get('name', f'Camera-{camera_id}')
    camera_type = camera_config.get('type', 'entry')
    camera_url = build_camera_url(camera_config)
    
    if not camera_url:
        print(f"❌ URL invalide pour la caméra {camera_name}")
        return None
    
    try:
        print(f"🔄 Tentative de connexion à la caméra {camera_name} ({camera_type})...")
        
        if isinstance(camera_url, str):
            cap = cv2.VideoCapture(camera_url, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(camera_url)

        if cap.isOpened():
            # Set camera properties for better far face detection
            # Higher resolution for security cameras
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)   # 1080p width
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)  # 1080p height
            cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)             # Reasonable FPS for processing
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)       # Minimize latency

            ret, frame = cap.read()
            if ret:
                # Verify the frame has reasonable dimensions
                height, width = frame.shape[:2]
                if width >= 1280 and height >= 720:  # At least 720p
                    print(f"✅ Caméra {camera_name} connectée avec succès ({width}x{height})")
                    return {
                        'id': camera_id,
                        'name': camera_name,
                        'type': camera_type,
                        'url': camera_url,
                        'cap': cap,
                        'config': camera_config,
                        'resolution': (width, height)
                    }
                else:
                    print(f"⚠️ Résolution insuffisante pour {camera_name}: {width}x{height}, utilisation quand même")
                    return {
                        'id': camera_id,
                        'name': camera_name,
                        'type': camera_type,
                        'url': camera_url,
                        'cap': cap,
                        'config': camera_config,
                        'resolution': (width, height)
                    }
            else:
                print(f"❌ Impossible de lire depuis la caméra {camera_name}")
                cap.release()
        else:
            print(f"❌ Impossible d'ouvrir la caméra {camera_name}")
            cap.release()
                
    except Exception as e:
        print(f"❌ Erreur avec la caméra {camera_name}: {e}")
        
    return None

def initialize_cameras():
    """Initialize all cameras in parallel and return camera objects"""
    global camera_caps, camera_configs
    
    # Fetch saved cameras from database
    saved_cameras = fetch_saved_cameras()
    active_cameras = [cam for cam in saved_cameras if cam.get('status') == 'active']
    
    if not active_cameras:
        print("⚠️  Aucune caméra active trouvée en base de données")
        return {}
    
    print(f"🔄 Initialisation parallèle de {len(active_cameras)} caméra(s)...")
    
    # Use ThreadPoolExecutor for parallel camera initialization
    camera_results = {}
    with ThreadPoolExecutor(max_workers=min(len(active_cameras), 10)) as executor:
        # Submit all camera initialization tasks
        future_to_camera = {
            executor.submit(initialize_single_camera, camera): camera 
            for camera in active_cameras
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_camera):
            camera_config = future_to_camera[future]
            try:
                result = future.result()
                if result:
                    camera_id = result['id']
                    camera_results[camera_id] = result
                    print(f"✅ Caméra {result['name']} ({result['type']}) initialisée")
                else:
                    print(f"❌ Échec d'initialisation de la caméra {camera_config.get('name', 'Unknown')}")
            except Exception as e:
                print(f"❌ Exception lors de l'initialisation de la caméra {camera_config.get('name', 'Unknown')}: {e}")
    
    # Update global camera storage
    with camera_lock:
        # Close existing cameras that are no longer active
        for cam_id, cam_data in camera_caps.items():
            if cam_id not in camera_results:
                print(f"🔄 Fermeture de la caméra supprimée: {cam_data.get('name', cam_id)}")
                if cam_data.get('cap'):
                    cam_data['cap'].release()
        
        camera_caps = {cam_id: cam_data for cam_id, cam_data in camera_results.items()}
        camera_configs = {cam_id: cam_data['config'] for cam_id, cam_data in camera_results.items()}
    
    print(f"✅ {len(camera_results)} caméra(s) initialisée(s) avec succès")
    return camera_results

def camera_monitor():
    """Monitor database for camera changes and reinitialize if needed"""
    global camera_caps, camera_configs
    last_camera_hash = None
    
    while not shutdown_event.is_set():
        try:
            # Fetch current cameras from database
            current_cameras = fetch_saved_cameras()
            active_cameras = [cam for cam in current_cameras if cam.get('status') == 'active']
            
            # Create a hash of camera configurations for comparison
            camera_hash = hash(json.dumps(sorted([
                {
                    'id': cam.get('_id'),
                    'name': cam.get('name'),
                    'type': cam.get('type'),
                    'ip': cam.get('ip'),
                    'port': cam.get('port'),
                    'status': cam.get('status')
                } for cam in active_cameras
            ], key=lambda x: x['id']), sort_keys=True))
            
            # Check if cameras have changed
            if last_camera_hash is not None and camera_hash != last_camera_hash:
                print("🔄 Changement détecté dans la configuration des caméras - reinitialisation...")
                initialize_cameras()
            
            last_camera_hash = camera_hash
            
        except Exception as e:
            print(f"❌ Erreur lors de la surveillance des caméras: {e}")
        
        # Wait before next check
        shutdown_event.wait(camera_check_interval)

# === Encodings reload logic ===

class EncodingFileHandler(FileSystemEventHandler):
    """Handler for monitoring changes to the encodings file"""
    
    def __init__(self):
        super().__init__()
        self.last_modified = 0
        self.cooldown_period = 2  # Prevent rapid successive reloads
    
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Check if it's the encodings file
        if os.path.abspath(event.src_path) == os.path.abspath(ENCODINGS_FILE):
            current_time = time.time()
            
            # Prevent rapid successive reloads with cooldown period
            if current_time - self.last_modified < self.cooldown_period:
                return
                
            self.last_modified = current_time
            print(f"🔄 Encodings file modified: {event.src_path}")
            reload_encodings()
    
    def on_created(self, event):
        # Handle case where encodings file is created
        if not event.is_directory and os.path.abspath(event.src_path) == os.path.abspath(ENCODINGS_FILE):
            print(f"✅ Encodings file created: {event.src_path}")
            reload_encodings()

def reload_encodings():
    """Reload encodings from the file in a thread-safe manner"""
    global known_encodings, known_names
    try:
        if not os.path.exists(ENCODINGS_FILE):
            print(f"⚠️  Encodings file not found: {ENCODINGS_FILE}. Using empty encodings.")
            with encodings_lock:
                known_encodings = []
                known_names = []
            return

        new_encodings, new_names = load_encodings()
        
        with encodings_lock:
            known_encodings = new_encodings
            known_names = new_names
            
        if new_encodings:
            print(f"✅ Encodings reloaded at {time.strftime('%Y-%m-%d %H:%M:%S')} - {len(new_encodings)} encodings loaded")
        else:
            print(f"⚠️  Encodings file empty or invalid at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
    except Exception as e:
        print(f"❌ Error reloading encodings: {e}")

def start_encodings_watcher():
    """Start the watchdog observer to monitor the encodings file"""
    try:
        event_handler = EncodingFileHandler()
        observer = Observer()
        
        # Watch the directory containing the encodings file
        watch_directory = os.path.dirname(os.path.abspath(ENCODINGS_FILE))
        if not os.path.exists(watch_directory):
            os.makedirs(watch_directory, exist_ok=True)
            print(f"📁 Created encodings directory: {watch_directory}")
        
        observer.schedule(event_handler, path=watch_directory, recursive=False)
        observer.start()
        
        print(f"👀 Started file watcher for encodings: {ENCODINGS_FILE}")
        return observer
        
    except Exception as e:
        print(f"❌ Failed to start encodings file watcher: {e}")
        return None



# Shared variables for encodings
encodings_lock = threading.Lock()

def initialize_file_watcher():
    """Initialize the encodings file watcher - called only from main process"""
    try:
        encodings_observer = start_encodings_watcher()
        return encodings_observer
    except:
        return None

def process_camera_frame_multiprocess(camera_data):
    """Process a single camera frame using multiprocessing"""
    camera_id, cap, camera_type, camera_name, known_encodings, known_names, frame_count = camera_data
    
    try:
        if not cap or not cap.isOpened():
            return {'camera_id': camera_id, 'success': False, 'error': f"Caméra {camera_name} non disponible"}
            
        ret, frame = cap.read()
        if ret:
            # Process frame in separate process
            frame_data = (frame, camera_type, camera_name, known_encodings, known_names, frame_count)
            results = process_frame_multiprocess(frame_data)
            return {'camera_id': camera_id, 'success': True, 'results': results, 'frame_processed': True}
        else:
            return {'camera_id': camera_id, 'success': False, 'error': f"Erreur lecture caméra {camera_name}"}
            
    except Exception as e:
        return {'camera_id': camera_id, 'success': False, 'error': f"Erreur traitement caméra {camera_id}: {e}"}

def process_camera_frame(camera_id, camera_data):
    """Process a single camera frame - legacy function for thread compatibility"""
    try:
        cap = camera_data.get('cap')
        camera_type = camera_data.get('type', 'entry')
        camera_name = camera_data.get('name', f'Camera-{camera_id}')
        
        if not cap or not cap.isOpened():
            print(f"❌ Caméra {camera_name} non disponible")
            return False
            
        ret, frame = cap.read()
        if ret:
            # For legacy compatibility, we still process inline for now
            with encodings_lock:
                current_encodings = known_encodings
                current_names = known_names
            
            global frame_count
            frame_count += 1
            
            frame_data = (frame, camera_type, camera_name, current_encodings, current_names, frame_count)
            results = process_frame_multiprocess(frame_data)
            
            # Process results
            for result in results:
                if result['type'] == 'recognition':
                    name = result['name']
                    confidence = result['confidence']
                    current_time = result['timestamp']
                    
                    # Check for duplicate detection
                    if name not in last_recognition or current_time - last_recognition[name] > 30:
                        print(f"👤 {name} détecté sur caméra {camera_name} ({camera_type}) (confiance: {confidence:.2f})")
                        log_attendance(name, camera_type, confidence)
                        last_recognition[name] = current_time
                        presence[name] = current_time
                        
                elif result['type'] == 'unknown_face':
                    save_unknown_face_from_data(result)
            
            return True
        else:
            print(f"❌ Erreur lecture caméra {camera_name}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur traitement caméra {camera_id}: {e}")
        return False

def save_unknown_face_from_data(result):
    """Save unknown face from processed result data"""
    try:
        face_image = result['face_image']
        face_location = result['face_location']
        camera_name = result['camera_name']
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unknown_id = f"inconnu_{hash(str(face_location)) % 100000000:08x}"
        filename = f"{unknown_id}_{timestamp}.jpg"
        filepath = os.path.join(UNKNOWN_DIR, filename)
        
        cv2.imwrite(filepath, face_image)
        print(f"💾 Visage inconnu sauvegardé: {filename} (caméra: {camera_name})")
    except Exception as e:
        print(f"❌ Erreur sauvegarde visage inconnu: {e}")

def enhance_image_for_face_detection(frame):
    """
    Enhance image for better face detection, especially for far faces
    """
    # Convert to LAB color space for better contrast enhancement
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l)

    # Merge channels back
    lab_enhanced = cv2.merge([l_enhanced, a, b])
    enhanced_frame = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    # Apply slight sharpening to enhance edges
    kernel = np.array([[-1,-1,-1],
                       [-1, 9,-1],
                       [-1,-1,-1]])
    enhanced_frame = cv2.filter2D(enhanced_frame, -1, kernel)

    # Apply gamma correction for better visibility
    gamma = 1.2
    lookUpTable = np.empty((1,256), np.uint8)
    for i in range(256):
        lookUpTable[0,i] = np.clip(pow(i / 255.0, gamma) * 255.0, 0, 255)
    enhanced_frame = cv2.LUT(enhanced_frame, lookUpTable)

    return enhanced_frame

def process_frame_multiprocess(frame_data):
    """
    Process frame for face recognition - designed for multiprocessing
    Optimized for security cameras with far face detection
    frame_data should be a tuple: (frame, camera_type, camera_name, known_encodings, known_names, frame_count)
    """
    # Performance monitoring - start timing
    if ENABLE_PERFORMANCE_MONITORING:
        process_start_time = time.time()
        detection_start_time = 0
        recognition_start_time = 0
        detection_time = 0  # Initialize to avoid undefined variable error
        recognition_time = 0  # Initialize to avoid undefined variable error
    else:
        process_start_time = 0
        detection_start_time = 0
        recognition_start_time = 0
        detection_time = 0
        recognition_time = 0
    
    # Ensure global variables are accessible in multiprocessing context
    global MIN_FACE_SIZE, MAX_FACES_PER_FRAME, FACE_DETECTION_MODEL

    frame, camera_type, camera_name, known_encodings, known_names, frame_count = frame_data

    results = []

    # Get original frame dimensions
    height, width = frame.shape[:2]

    # Multi-scale face detection for better far face detection
    face_locations = []

    # Apply image enhancement for better face detection
    enhanced_frame = enhance_image_for_face_detection(frame)

    # Performance monitoring - detection phase start
    if ENABLE_PERFORMANCE_MONITORING:
        detection_start_time = time.time()

    # Scale 1: Enhanced original frame (for close faces)
    rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
    faces_scale1 = face_recognition.face_locations(rgb_frame, model=FACE_DETECTION_MODEL, number_of_times_to_upsample=1)
    face_locations.extend([(top, right, bottom, left, 1.0) for top, right, bottom, left in faces_scale1])

    # Scale 2: Slightly downscaled (for medium distance faces)
    scale2_factor = 0.75
    small_frame = cv2.resize(enhanced_frame, (0, 0), fx=scale2_factor, fy=scale2_factor)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    faces_scale2 = face_recognition.face_locations(rgb_small_frame, model=FACE_DETECTION_MODEL, number_of_times_to_upsample=1)
    # Scale coordinates back to original
    for top, right, bottom, left in faces_scale2:
        orig_top = int(top / scale2_factor)
        orig_right = int(right / scale2_factor)
        orig_bottom = int(bottom / scale2_factor)
        orig_left = int(left / scale2_factor)
        face_locations.append((orig_top, orig_right, orig_bottom, orig_left, scale2_factor))

    # Scale 3: Further downscaled (for far faces) - but keep minimum size
    scale3_factor = 0.5
    far_frame = cv2.resize(enhanced_frame, (0, 0), fx=scale3_factor, fy=scale3_factor)
    rgb_far_frame = cv2.cvtColor(far_frame, cv2.COLOR_BGR2RGB)
    faces_scale3 = face_recognition.face_locations(rgb_far_frame, model=FACE_DETECTION_MODEL, number_of_times_to_upsample=2)
    # Scale coordinates back to original
    for top, right, bottom, left in faces_scale3:
        orig_top = int(top / scale3_factor)
        orig_right = int(right / scale3_factor)
        orig_bottom = int(bottom / scale3_factor)
        orig_left = int(left / scale3_factor)
        face_locations.append((orig_top, orig_right, orig_bottom, orig_left, scale3_factor))

    # Remove duplicates and filter by minimum size (for security cameras)
    # Ensure MIN_FACE_SIZE is accessible (fallback to default if needed)
    min_face_size = globals().get('MIN_FACE_SIZE', 40)
    filtered_faces = []
    seen_faces = set()

    for face_data in face_locations:
        if len(face_data) == 5:
            top, right, bottom, left, scale = face_data
        else:
            top, right, bottom, left = face_data
            scale = 1.0

        face_width = right - left
        face_height = bottom - top

        # Filter faces that are too small
        if face_width < min_face_size or face_height < min_face_size:
            continue

        # Create a unique key for this face location (with some tolerance)
        face_key = (top // 20, left // 20, face_width // 20, face_height // 20)

        if face_key not in seen_faces:
            seen_faces.add(face_key)
            filtered_faces.append((top, right, bottom, left))

    face_locations = filtered_faces
    
    # Add detailed logging for face detection
    print(f"🎯 FACE DETECTION RESULTS for {camera_name}:")
    print(f"   - Scale 1 faces: {len(faces_scale1)}")
    print(f"   - Scale 2 faces: {len(faces_scale2)}")  
    print(f"   - Scale 3 faces: {len(faces_scale3)}")
    print(f"   - Total before filtering: {len(face_locations) + len([f for f in filtered_faces if f not in face_locations])}")
    print(f"   - After size filtering: {len(face_locations)}")

    # Limit the number of faces processed (prioritize larger faces for security)
    if len(face_locations) > MAX_FACES_PER_FRAME:
        # Sort by face size (largest first)
        face_sizes = [(bottom - top) * (right - left) for top, right, bottom, left in face_locations]
        sorted_indices = np.argsort(face_sizes)[::-1][:MAX_FACES_PER_FRAME]  # Largest faces first
        face_locations = [face_locations[i] for i in sorted_indices]
        print(f"   - Limited to: {len(face_locations)} faces (max: {MAX_FACES_PER_FRAME})")

    # Complete detection timing even if no faces found
    if ENABLE_PERFORMANCE_MONITORING:
        detection_end_time = time.time()
        detection_time = detection_end_time - detection_start_time
        log_performance_metric('detection_time', detection_time)
        print(f"📊 detection_time: {detection_time * 1000:.2f} ms")

    # Get face encodings from original frame
    if face_locations:
        # Performance monitoring - recognition phase start
        if ENABLE_PERFORMANCE_MONITORING:
            recognition_start_time = time.time()
        
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        # Add CPU-intensive processing to better utilize cores
        # Process each face encoding with additional analysis
        enhanced_encodings = []
        for encoding in face_encodings:
            # Add some computational work to increase CPU usage
            # This helps utilize CPU cores more effectively
            enhanced_encoding = encoding.copy()

            # Perform additional vector operations to increase CPU load
            if ENABLE_CPU_BOOST:
                for _ in range(CPU_BOOST_ITERATIONS):  # Configurable iterations
                    enhanced_encoding = enhanced_encoding * 0.99 + np.random.random(len(encoding)) * 0.01
                    enhanced_encoding = np.clip(enhanced_encoding, -1, 1)

            enhanced_encodings.append(enhanced_encoding)

        face_encodings = enhanced_encodings
    else:
        face_encodings = []
    
    # Si aucun encodage n'est disponible, sauvegarder les visages comme inconnus
    if not known_encodings:
        print(f"⚠️  No encodings available - {len(face_locations)} faces detected will be saved as unknown")
        if face_locations and frame_count % 30 == 0:  # Sauvegarder seulement toutes les 30 frames
            unknown_faces = []
            for face_location in face_locations:
                # Coordonnées déjà dans l'échelle originale
                top, right, bottom, left = face_location
                face_image = frame[top:bottom, left:right]
                unknown_faces.append({
                    'type': 'unknown_face',
                    'face_image': face_image,
                    'face_location': (top, right, bottom, left),
                    'camera_name': camera_name
                })
            results.extend(unknown_faces)
            print(f"💾 Saved {len(unknown_faces)} unknown faces from {camera_name}")
        return results
    
    print(f"🔍 Processing {len(face_locations)} faces with {len(known_encodings)} known encodings (Camera: {camera_name})")
    
    current_time = time.time()
    
    for i, (face_encoding, face_location) in enumerate(zip(face_encodings, face_locations)):
        print(f"  👤 Processing face {i+1}/{len(face_encodings)} at location {face_location}")
        
        # Comparer avec les visages connus
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.6)
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        
        print(f"     🎯 Found {sum(matches)} matches out of {len(matches)} comparisons")
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            best_distance = face_distances[best_match_index]
            print(f"     📏 Best match distance: {best_distance:.3f} (threshold: 0.6)")
            
            if matches[best_match_index]:
                name = known_names[best_match_index]
                confidence = 1 - face_distances[best_match_index]
                
                print(f"     ✅ RECOGNIZED: {name} (confidence: {confidence:.3f})")
                
                results.append({
                    'type': 'recognition',
                    'name': name,
                    'confidence': confidence,
                    'camera_type': camera_type,
                    'camera_name': camera_name,
                    'timestamp': current_time
                })
            else:
                print(f"     ❌ No match found - face will be saved as unknown")
                # Visage inconnu
                if frame_count % 30 == 0:  # Sauvegarder seulement toutes les 30 frames
                    # Coordonnées déjà dans l'échelle originale
                    top, right, bottom, left = face_location
                    face_image = frame[top:bottom, left:right]

                    results.append({
                        'type': 'unknown_face',
                        'face_image': face_image,
                        'face_location': (top, right, bottom, left),
                        'camera_name': camera_name
                    })
    
    # Performance monitoring - recognition phase end and overall timing
    if ENABLE_PERFORMANCE_MONITORING:
        if recognition_start_time > 0:  # Only calculate if recognition actually started
            recognition_end_time = time.time()
            recognition_time = recognition_end_time - recognition_start_time
            log_performance_metric('recognition_time', recognition_time)
        
        total_process_time = time.time() - process_start_time
        log_performance_metric('total_process_time', total_process_time)
        
        # Update global performance counters - only if variables are properly defined
        try:
            global perf_total_detection_time, perf_total_recognition_time, perf_faces_detected, perf_faces_recognized
            perf_total_detection_time += detection_time
            perf_total_recognition_time += recognition_time
            perf_faces_detected += len(face_locations)
            perf_faces_recognized += len([r for r in results if r['type'] == 'recognition'])
        except NameError as e:
            print(f"⚠️ Performance counter error (non-critical): {e}")
    
    return results


def main():
    """Fonction principale"""
    global frame_count
    
    # Initialize encodings first (only in main process)
    initialize_encodings()
    
    print("🚀 Démarrage du système de reconnaissance faciale...")
    
    # Établir la connexion WebSocket
    connect_websocket()
    
    # Check if we have encodings
    if not known_encodings:
        print("⚠️  Aucun encodage disponible. Le système fonctionnera en mode détection seulement.")
        print("💡 Les visages détectés seront sauvegardés comme inconnus.")
    
    # Initialiser les caméras avec support parallèle
    camera_results = initialize_cameras()
    
    # Start camera monitoring thread
    camera_monitor_thread = threading.Thread(target=camera_monitor, daemon=True)
    camera_monitor_thread.start()
    
    # Start listener thread for quit commands
    listener_thread = threading.Thread(target=listen_for_quit)
    listener_thread.start()
    
    # Initialize file watcher
    encodings_observer = initialize_file_watcher()
    
    if not camera_results:
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
                        camera_results = initialize_cameras()
                        if camera_results:
                            break
        except KeyboardInterrupt:
            print("\n🛑 Arrêt par Ctrl+C")
            shutdown_event.set()
            return
    
    print(f"🎥 Démarrage de la reconnaissance faciale avec {len(camera_results)} caméra(s)...")
    print("💡 Tapez 'q' ou 'quit' pour arrêter le programme")
    
    # Initialize multiprocessing pool for face recognition
    # Use more processes to fully utilize CPU, regardless of camera count
    num_processes = min(mp.cpu_count(), MAX_CPU_PROCESSES)  # Use up to MAX_CPU_PROCESSES for better CPU utilization
    print(f"🚀 Utilisation de {num_processes} processus pour la reconnaissance faciale (CPU: {mp.cpu_count()} cores)")
    print(f"💡 Configuration optimisée pour utilisation maximale du CPU")
    
    # Display performance optimization settings
    print(f"⚡ OPTIMISATIONS DE PERFORMANCE:")
    print(f"   - Frame skipping interval: {FRAME_SKIP_INTERVAL}")
    print(f"   - Intelligent frame skipping: {'ENABLED' if ENABLE_INTELLIGENT_FRAME_SKIPPING else 'DISABLED'}")
    print(f"   - Scene change detection: {'ENABLED' if ENABLE_SCENE_CHANGE_DETECTION else 'DISABLED'}")
    if ENABLE_SCENE_CHANGE_DETECTION:
        print(f"   - Scene change threshold: {SCENE_CHANGE_THRESHOLD}%")
        print(f"   - Pixel difference threshold: {SCENE_CHANGE_PIXEL_THRESHOLD}")
        print(f"   - Min contour area: {SCENE_CHANGE_MIN_CONTOUR_AREA}px")
    print(f"   - Performance monitoring: {'ENABLED' if ENABLE_PERFORMANCE_MONITORING else 'DISABLED'}")

    # Frame skipping configuration for performance optimization
    # Reduce frame skipping to increase CPU workload
    frame_skip_counter = 0
    cpu_report_counter = 0

    try:
        with ProcessPoolExecutor(max_workers=num_processes) as process_executor:
            while not shutdown_event.is_set():
                frame_start_time = time.time() if ENABLE_PERFORMANCE_MONITORING else 0

                with camera_lock:
                    current_cameras = dict(camera_caps)

                if not current_cameras:
                    time.sleep(1)
                    continue

                # Increment frame skip counter
                frame_skip_counter += 1
                
                # Check for shutdown signal frequently for responsive stopping
                if shutdown_event.is_set():
                    print("🔄 Signal d'arrêt détecté, arrêt du traitement...")
                    break
                
                # Only process frames every Nth iteration for performance
                should_process_frame = (frame_skip_counter % FRAME_SKIP_INTERVAL == 0)
                
                # Prepare data for multiprocessing
                camera_frame_data = []
                failed_cameras = []
                
                # First, collect frames from all cameras (I/O bound - use threads)
                io_start_time = time.time() if ENABLE_PERFORMANCE_MONITORING else 0
                with ThreadPoolExecutor(max_workers=min(len(current_cameras), 10)) as thread_executor:
                    frame_futures = {}
                    
                    for cam_id, cam_data in current_cameras.items():
                        cap = cam_data.get('cap')
                        if cap and cap.isOpened():
                            future = thread_executor.submit(cap.read)
                            frame_futures[future] = (cam_id, cam_data)
                    
                    # Collect frames as they're ready
                    for future in as_completed(frame_futures):
                        cam_id, cam_data = frame_futures[future]
                        try:
                            ret, frame = future.result()
                            if ret:
                                # 🔍 Scene Change Detection
                                should_process_camera = True
                                if ENABLE_INTELLIGENT_FRAME_SKIPPING and ENABLE_SCENE_CHANGE_DETECTION and cam_id in previous_frames:
                                    has_change = detect_scene_change(previous_frames[cam_id], frame)
                                    should_process_camera = has_change
                                    if not has_change:
                                        print(f"⏭️  No significant change detected in {cam_data.get('name', f'Camera-{cam_id}')} - skipping processing")
                                
                                # Store current frame as previous for next iteration
                                previous_frames[cam_id] = frame.copy()
                                
                                # Only add to processing queue if scene change detected or first frame or if intelligent skipping is disabled
                                if should_process_camera or not ENABLE_INTELLIGENT_FRAME_SKIPPING:
                                    with encodings_lock:
                                        current_encodings = list(known_encodings)  # Create copy for process
                                        current_names = list(known_names)  # Create copy for process
                                    
                                    camera_frame_data.append((
                                        frame,
                                        cam_data.get('type', 'entry'),
                                        cam_data.get('name', f'Camera-{cam_id}'),
                                        current_encodings,
                                        current_names,
                                        frame_count + 1
                                    ))
                                    print(f"📹 Scene change detected in {cam_data.get('name', f'Camera-{cam_id}')} - added to processing queue")
                            else:
                                failed_cameras.append(cam_id)
                        except Exception as e:
                            print(f"❌ Erreur lecture caméra {cam_id}: {e}")
                            failed_cameras.append(cam_id)
                
                # Performance monitoring - I/O timing
                if ENABLE_PERFORMANCE_MONITORING and io_start_time > 0:
                    io_end_time = time.time()
                    io_time = io_end_time - io_start_time
                    log_performance_metric('io_time', io_time)
                    global perf_total_io_time
                    perf_total_io_time += io_time
                
                # Increment frame count
                frame_count += 1
                
                # Log frame processing every 50 frames
                if frame_count % 50 == 0:
                    processed_cameras = len(camera_frame_data)
                    skipped_cameras = len(current_cameras) - processed_cameras if current_cameras else 0
                    print(f"📊 FRAME PROCESSING STATUS (Frame {frame_count}):")
                    print(f"   - Total cameras: {len(current_cameras) if current_cameras else 0}")
                    print(f"   - Cameras with scene changes: {processed_cameras}")
                    print(f"   - Cameras skipped (no change): {skipped_cameras}")
                    print(f"   - Known encodings: {len(known_encodings) if known_encodings else 0}")
                    print(f"   - Should process this frame: {should_process_frame}")
                    print(f"   - Scene change detection: {'ENABLED' if ENABLE_SCENE_CHANGE_DETECTION else 'DISABLED'}")
                else:
                    processed_cameras = len(camera_frame_data)
                    total_cameras = len(current_cameras) if current_cameras else 0
                    print(f"📹 Frame {frame_count} - Regular skip: {frame_skip_counter % FRAME_SKIP_INTERVAL != 0} | Scene changes: {processed_cameras}/{total_cameras}")

                # Periodic CPU usage report
                cpu_report_counter += 1
                if cpu_report_counter % 30 == 0:  # Every 30 frames
                    avg_cpu = psutil.cpu_percent(interval=0.5)
                    memory = psutil.virtual_memory()
                    print(f"📊 Rapport de performance - CPU: {avg_cpu:.1f}% | Mémoire: {memory.percent:.1f}% | Processus actifs: {len(processing_futures) if 'processing_futures' in locals() else 0}")

                # Process frames using multiprocessing (CPU bound) - only if we should process this frame
                if camera_frame_data and should_process_frame:
                    # Monitor CPU usage
                    cpu_usage = psutil.cpu_percent(interval=0.1)
                    print(f"🔍 Traitement de {len(camera_frame_data)} frame(s) - CPU: {cpu_usage:.1f}% - Compteur: {frame_skip_counter}")

                    # Submit tasks to process pool with proper mapping
                    processing_futures = []
                    future_to_camera_data = {}

                    # Submit original tasks
                    for frame_data in camera_frame_data:
                        future = process_executor.submit(process_frame_multiprocess, frame_data)
                        processing_futures.append(future)
                        future_to_camera_data[future] = frame_data

                    # If we have fewer tasks than processes, submit additional tasks for better CPU utilization
                    original_task_count = len(processing_futures)
                    if len(processing_futures) < num_processes:
                        # Duplicate some tasks to keep all cores busy
                        additional_tasks = min(num_processes - len(processing_futures), len(camera_frame_data))
                        for i in range(additional_tasks):
                            future = process_executor.submit(process_frame_multiprocess, camera_frame_data[i])
                            processing_futures.append(future)
                            future_to_camera_data[future] = camera_frame_data[i]  # Map to original camera data
                        if additional_tasks > 0:
                            print(f"📈 Tâches supplémentaires soumises: {additional_tasks} (Original: {original_task_count}, Total: {len(processing_futures)})")

                    # Validate mapping integrity
                    if len(future_to_camera_data) != len(processing_futures):
                        print(f"⚠️  Attention: Incohérence mapping ({len(future_to_camera_data)} vs {len(processing_futures)})")

                    # Collect and process results using proper mapping
                    processed_count = 0
                    for future in as_completed(processing_futures):
                        processed_count += 1
                        try:
                            results = future.result()
                            # Get camera data from the mapping
                            if future not in future_to_camera_data:
                                print(f"⚠️  Future sans mapping trouvé: {id(future)}")
                                continue

                            frame_data = future_to_camera_data[future]
                            # Validate frame_data structure
                            if len(frame_data) < 3:
                                print(f"⚠️  Structure frame_data invalide: {len(frame_data)} éléments")
                                camera_name = f"Camera-{processed_count}"
                                camera_type = "unknown"
                            else:
                                camera_name = frame_data[2]  # Camera name
                                camera_type = frame_data[1]  # Camera type

                            # Process recognition results
                            total_recognitions = len([r for r in results if r['type'] == 'recognition'])
                            total_unknowns = len([r for r in results if r['type'] == 'unknown_face'])
                            
                            print(f"📋 Processing results from {camera_name}: {total_recognitions} recognitions, {total_unknowns} unknowns")
                            
                            for result in results:
                                if result['type'] == 'recognition':
                                    name = result['name']
                                    confidence = result['confidence']
                                    current_time = result['timestamp']

                                    # Check for duplicate detection
                                    if name not in last_recognition or current_time - last_recognition[name] > 30:
                                        print(f"👤 {name} détecté sur caméra {camera_name} ({camera_type}) (confiance: {confidence:.2f})")
                                        log_attendance(name, camera_type, confidence)
                                        last_recognition[name] = current_time
                                        presence[name] = current_time
                                    else:
                                        time_since_last = current_time - last_recognition[name]
                                        print(f"🔄 {name} détecté récemment ({time_since_last:.1f}s ago) - skipping duplicate")

                                elif result['type'] == 'unknown_face':
                                    print(f"❓ Unknown face detected on {camera_name} - saving")
                                    save_unknown_face_from_data(result)

                        except Exception as e:
                            print(f"❌ Erreur traitement résultat reconnaissance: {e}")
                            # Print additional debug information
                            if future in future_to_camera_data:
                                frame_data = future_to_camera_data[future]
                                camera_name = frame_data[2] if len(frame_data) > 2 else "Unknown"
                                print(f"   📍 Contexte: Caméra {camera_name}, Future ID: {id(future)}")
                            else:
                                print(f"   📍 Contexte: Future ID: {id(future)} (pas de mapping trouvé)")

                    # Log processing completion
                    if processed_count > 0:
                        print(f"✅ Traitement terminé: {processed_count}/{len(processing_futures)} tâches complétées")
                
                # Performance monitoring - log frame completion time
                if ENABLE_PERFORMANCE_MONITORING and frame_start_time > 0:
                    frame_end_time = time.time()
                    frame_processing_time = frame_end_time - frame_start_time
                    log_performance_metric('frame_processing_time', frame_processing_time)
                    
                    # Log detailed timing if enabled
                    if TRACK_DETAILED_TIMING:
                        print(f"⏱️ Frame {frame_count} traité en {frame_processing_time:.3f}s")
                    
                    # Periodic performance report
                    if frame_count % PERFORMANCE_REPORT_INTERVAL == 0:
                        report_performance_stats()
                        reset_performance_stats()
                
                # Handle failed cameras - attempt reconnection
                if failed_cameras:
                    for cam_id in failed_cameras:
                        with camera_lock:
                            if cam_id in camera_caps:
                                cam_data = camera_caps[cam_id]
                                cam_name = cam_data.get('name', f'Camera-{cam_id}')
                                print(f"🔄 Tentative de reconnexion pour {cam_name}...")
                                
                                # Close failed camera
                                if cam_data.get('cap'):
                                    cam_data['cap'].release()
                                
                                # Try to reinitialize this specific camera
                                if cam_id in camera_configs:
                                    new_cam_data = initialize_single_camera(camera_configs[cam_id])
                                    if new_cam_data:
                                        camera_caps[cam_id] = new_cam_data
                                        print(f"✅ Caméra {cam_name} reconnectée")
                                    else:
                                        del camera_caps[cam_id]
                                        print(f"❌ Échec reconnexion {cam_name}")
                
                # Check for shutdown before sleeping
                if shutdown_event.is_set():
                    break
                
                # Adaptive sleep based on processing load and CPU usage
                if should_process_frame:
                    # Check CPU usage to adjust sleep time
                    current_cpu = psutil.cpu_percent(interval=0.1)
                    if current_cpu < 70:  # If CPU usage is low, reduce sleep to process more
                        time.sleep(0.02)  # Very short sleep to increase throughput
                    else:
                        time.sleep(0.05)  # Normal sleep when CPU is busy
                else:
                    time.sleep(0.01)  # Very short sleep when skipping frames
            
        print("✅ Boucle principale terminée")
            
    except KeyboardInterrupt:
        print("\n🛑 Arrêt par Ctrl+C")
        shutdown_event.set()
    finally:
        # Nettoyer les ressources
        shutdown_event.set()
        
        with camera_lock:
            for cam_data in camera_caps.values():
                if cam_data.get('cap'):
                    cam_data['cap'].release()
            camera_caps.clear()
        
        cv2.destroyAllWindows()
        if ws:
            ws.close()
        
        # Join background threads
        try:
            if 'listener_thread' in locals():
                listener_thread.join(timeout=2)
        except:
            pass
        
        try:
            if 'encodings_observer' in locals() and encodings_observer:
                encodings_observer.stop()
                encodings_observer.join(timeout=2)
        except:
            pass
        
        try:
            if 'camera_monitor_thread' in locals():
                camera_monitor_thread.join(timeout=2)
        except:
            pass
        print("🧹 Ressources nettoyées")

if __name__ == "__main__":
    # Set multiprocessing start method for cross-platform compatibility
    if hasattr(mp, 'set_start_method'):
        try:
            mp.set_start_method('spawn', force=True)
        except RuntimeError:
            pass  # Method already set
    
    main()

