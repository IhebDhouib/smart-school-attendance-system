"""
Single Camera Face Recognition System with SCRFD 2.5G Detector

PERFORMANCE OPTIMIZATION:
- Set ENHANCEMENT_LEVEL to control speed vs quality trade-off:
  * "none"     - No enhancement (~0ms)     - Fastest, lowest quality
  * "fast"     - CLAHE only (~10-20ms)     - ⭐ RECOMMENDED for real-time
  * "balanced" - CLAHE + sharpen (~50-100ms) - Good balance
  * "quality"  - Full pipeline (~500-700ms) - Best quality, very slow

USAGE:
  # For real-time (recommended):
  ENHANCEMENT_LEVEL=fast python app_with_env_single_camera_scrfd.py
  
  # For maximum quality (slow):
  ENHANCEMENT_LEVEL=quality python app_with_env_single_camera_scrfd.py
  
  # No enhancement (fastest):
  ENHANCEMENT_LEVEL=none python app_with_env_single_camera_scrfd.py

EXPECTED TIMING (per frame):
  Enhancement: 10-20ms (fast) | 50-100ms (balanced) | 500-700ms (quality)
  Detection:   50-100ms (SCRFD 2.5G is fast and accurate!)
  Total:       ~60-120ms per frame with "fast" level = 8-16 FPS
"""

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
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image

# Suppress pkg_resources deprecation warning
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# Configure logging
LOG_FILE_APP = os.getenv('FACE_RECOGNITION_LOG_FILE', 'face_recognition_app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_APP, encoding='utf-8'),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

# 🎨 Real-ESRGAN imports for image enhancement
try:
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet
    ESRGAN_AVAILABLE = True
    print("✅ Real-ESRGAN libraries loaded successfully")
except ImportError as e:
    ESRGAN_AVAILABLE = False
    print(f"⚠️  Real-ESRGAN not available: {e}")
    print("   Install with: pip install realesrgan basicsr facexlib gfpgan")
    print("   System will use OpenCV enhancement instead")

# ============================================
# SINGLE CAMERA CONFIGURATION
# ============================================
# For local development (your PC):
# SINGLE_CAMERA_URL = "rtsp://admin:admin1234@10.3.8.9:554/cam/realmonitor?channel=7&subtype=0&bitrate=4096&fps=25"

# For server deployment - CHANGE THIS IP TO YOUR SERVER'S CAMERA IP:
SINGLE_CAMERA_URL = os.getenv("CAMERA_URL", "rtsp://admin:admin1234@10.3.8.9:554/cam/realmonitor?channel=7&subtype=0&bitrate=4096&fps=25")
SINGLE_CAMERA_NAME = "RTSP Camera 1"
SINGLE_CAMERA_TYPE = "entry"  # Can be 'entry' or 'exit'
# ============================================

# 📁 Chemins - Use environment variables for Docker compatibility
ENCODINGS_FILE = os.getenv("ENCODINGS_FILE_ARCFACE", "encodings_arcface.pkl")  # Using ArcFace embeddings now
UNKNOWN_DIR = os.getenv("UNKNOWN_FACES_DIR", "unknown_faces")
LOG_FILE = os.path.join(os.getenv("LOG_DIR", "logs"), "logs.csv")

# Backend configuration - Use environment variables for Docker/local compatibility
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:3001")

# 🔍 InsightFace Configuration (SCRFD 2.5G + ArcFace) - Use environment variables
INSIGHTFACE_MODEL = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")  # 'buffalo_l' uses RetinaFace detector (more accurate)
USE_GPU = os.getenv("USE_GPU", "False").lower() == "true"  # Set to True if CUDA is available for GPU acceleration
DET_SIZE_VALUE = int(os.getenv("DET_SIZE", "640"))
DET_SIZE = (DET_SIZE_VALUE, DET_SIZE_VALUE)  # Detection input size - larger = better for small faces
DET_THRESH = float(os.getenv("DET_THRESH", "0.3"))  # Detection confidence threshold (LOWERED to 0.3 for better detection)
REC_THRESH = float(os.getenv("REC_THRESH", "0.3"))  # Recognition similarity threshold (lower = stricter)

# 🎨 Image Enhancement
ENABLE_ESRGAN = os.getenv("ENABLE_ESRGAN", "False").lower() == "true"  # Enable Real-ESRGAN super-resolution (VERY slow ~500ms)
ESRGAN_MODEL_PATH = os.getenv("ESRGAN_MODEL_PATH", "RealESRGAN_x2plus.pth")  # Model file path
ESRGAN_SCALE = int(os.getenv("ESRGAN_SCALE", "2"))  # Upscaling factor (2x or 4x)

# Enhancement level: "none", "fast", "balanced", "quality"
# - none: No enhancement (~0ms) - Use original frame
# - fast: CLAHE only (~10-20ms) - Good for real-time
# - balanced: CLAHE + sharpening (~50-100ms) - Good quality/speed trade-off
# - quality: Full enhancement (~500-700ms) - Maximum quality but slow
ENHANCEMENT_LEVEL = os.getenv("ENHANCEMENT_LEVEL", "fast").lower()

# 📹 Camera Configuration for Security
CAMERA_WIDTH = 1920   # 1080p width for better far face detection
CAMERA_HEIGHT = 1080  # 1080p height
CAMERA_FPS = 15       # Reasonable FPS for processing

# 📊 Performance Settings
MIN_FACE_SIZE = 10  # REDUCED from 20 - Minimum face size in pixels (detect smaller faces)
MAX_FACES_PER_FRAME = 20  # INCREASED from 10 - Maximum faces to process per frame
FRAME_SKIP_INTERVAL = 1  # Process every Nth frame for performance
ENABLE_INTELLIGENT_FRAME_SKIPPING = True  # Enable scene change detection to skip unchanged frames

# 🚀 CPU Optimization Settings
MAX_CPU_PROCESSES = 12  # Maximum processes to utilize all CPU cores
ENABLE_CPU_BOOST = True  # Enable additional CPU-intensive processing
CPU_BOOST_ITERATIONS = 5  # Number of computational iterations for CPU boost

# 📊 Performance Monitoring Settings
ENABLE_PERFORMANCE_MONITORING = False  # Enable lightweight performance tracking
PERFORMANCE_REPORT_INTERVAL = 50  # Report performance every N frames
TRACK_DETAILED_TIMING = False  # Enable detailed timing (impacts performance slightly)

# 📈 Performance Monitoring Variables
perf_frame_count = 0
perf_total_frame_time = 0
perf_total_detection_time = 0
perf_total_recognition_time = 0
perf_total_io_time = 0
perf_faces_detected = 0
perf_faces_recognized = 0
perf_start_time = time.time()

# 🔍 Scene Change Detection Settings
SCENE_CHANGE_THRESHOLD = 2.0  # Threshold for scene change detection (lower = more sensitive) - reduced for better detection
SCENE_CHANGE_MIN_CONTOUR_AREA = 300  # Minimum contour area to consider for change - reduced for sensitivity
ENABLE_SCENE_CHANGE_DETECTION = True  # Enable/disable scene change detection
SCENE_CHANGE_PIXEL_THRESHOLD = 2.0  # Threshold for mean pixel difference method

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
            # ✅ Utiliser 'embeddings' (clé réelle dans le fichier pickle)
            return data.get("embeddings", []), data.get("names", [])
    except Exception as e:
        print(f"❌ Erreur lors du rechargement des encodages: {e}")
        return [], []

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

# 📂 Dossiers requis
os.makedirs(UNKNOWN_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Create detected faces directory
DETECTED_FACES_DIR = os.path.join(os.getenv("UNKNOWN_FACES_DIR", "unknown_faces"), "all_detected")
os.makedirs(DETECTED_FACES_DIR, exist_ok=True)

# 🤖 Initialize InsightFace Model (SCRFD + ArcFace)
print("🔧 Initializing InsightFace models (SCRFD + ArcFace)...")
face_app = None
esrgan_upsampler = None

def initialize_esrgan():
    """Initialize Real-ESRGAN upsampler for image enhancement"""
    global esrgan_upsampler
    
    if not ENABLE_ESRGAN:
        print("ℹ️  ESRGAN disabled - using OpenCV enhancement only")
        return False
    
    if not ESRGAN_AVAILABLE:
        print("⚠️  ESRGAN libraries not installed - falling back to OpenCV enhancement")
        return False
    
    try:
        print("🔧 Initializing Real-ESRGAN...")
        
        # Define model architecture (RealESRGAN_x2plus uses RRDBNet)
        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=ESRGAN_SCALE
        )
        
        # Initialize upsampler
        esrgan_upsampler = RealESRGANer(
            scale=ESRGAN_SCALE,
            model_path=ESRGAN_MODEL_PATH,
            model=model,
            tile=400,  # Process in tiles to save memory
            tile_pad=10,
            pre_pad=0,
            half=False  # Set to True if using GPU with FP16 support
        )
        
        print(f"✅ Real-ESRGAN initialized successfully!")
        print(f"   Model: {ESRGAN_MODEL_PATH}")
        print(f"   Scale: {ESRGAN_SCALE}x upscaling")
        print(f"   Tile size: 400x400 (memory efficient)")
        return True
        
    except FileNotFoundError:
        print(f"❌ ESRGAN model file not found: {ESRGAN_MODEL_PATH}")
        print("   Download from: https://github.com/xinntao/Real-ESRGAN/releases")
        print("   Recommended: RealESRGAN_x2plus.pth (for 2x upscaling)")
        print("   Falling back to OpenCV enhancement")
        return False
    except Exception as e:
        print(f"❌ Failed to initialize Real-ESRGAN: {e}")
        print("   Falling back to OpenCV enhancement")
        return False

def initialize_insightface():
    """Initialize InsightFace FaceAnalysis model with SCRFD 2.5G detector"""
    global face_app
    try:
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if USE_GPU else ['CPUExecutionProvider']
        
        # buffalo_sc uses SCRFD_2.5G detector (faster and balanced)
        face_app = FaceAnalysis(
            name=INSIGHTFACE_MODEL,
            providers=providers
        )
        # Configure for better detection on full frames
        face_app.prepare(
            ctx_id=0 if USE_GPU else -1, 
            det_size=DET_SIZE,  # Detection resolution
            det_thresh=DET_THRESH  # Lower threshold for better detection
        )
        
        print(f"✅ InsightFace initialized successfully!")
        print(f"   Model: {INSIGHTFACE_MODEL} (SCRFD 2.5G detector)")
        print(f"   Providers: {providers}")
        print(f"   Detection size: {DET_SIZE}")
        print(f"   Detection threshold: {DET_THRESH} (lower = more sensitive)")
        print(f"   Recognition threshold: {REC_THRESH}")
        print(f"   Min face size: {MIN_FACE_SIZE}px")
        print(f"   🎯 SCRFD 2.5G provides fast and accurate detection!")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize InsightFace: {e}")
        print("   Please run: pip install insightface onnxruntime")
        return False

# Initialize at startup
if not initialize_insightface():
    print("⚠️  Warning: InsightFace not initialized. Face recognition will not work.")

# Initialize ESRGAN if enabled
esrgan_enabled = initialize_esrgan()

# 🧠 Global variables for encodings (initialized later)
known_encodings = []
known_names = []

def initialize_encodings():
    """Initialize encodings - called only from main process"""
    global known_encodings, known_names
    
    print("🧠 INITIALIZING FACE ENCODINGS...")
    logger.info("Starting face encodings initialization...")
    
    try:
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            # ✅ Utiliser 'embeddings' (clé réelle dans le fichier pickle)
            known_encodings = data.get("embeddings", [])
            known_names = data.get("names", [])
            
            
        print(f"📊 ENCODING STATISTICS:")
        print(f"   - Total encodings loaded: {len(known_encodings)}")
        print(f"   - Total names loaded: {len(known_names)}")
        print(f"   - Unique students: {len(set(known_names))}")
        print(f"   - Embedding dimension: {len(known_encodings[0]) if known_encodings else 'N/A'} (ArcFace: 512-dim)")
        
        if known_names:
            name_counts = {}
            for name in known_names:
                name_counts[name] = name_counts.get(name, 0) + 1
            print(f"   - Student breakdown:")
            for name, count in sorted(name_counts.items()):
                print(f"     • {name}: {count} encoding(s)")
                
        if not known_encodings:
            print("⚠️  Encodages non valides ou vides. Le système démarrera en mode attente.")
            print("💡 Ajoutez des étudiants via l'interface web pour générer les encodages.")
            logger.warning("No valid encodings found - starting in detection-only mode")
            known_encodings = []
            known_names = []
        else:
            print(f"✅ {len(known_encodings)} encodages chargés pour {len(set(known_names))} personnes.")
            logger.info(f"Successfully loaded {len(known_encodings)} encodings for {len(set(known_names))} students")

    except FileNotFoundError:
        print("⚠️  Fichier encodings.pkl non trouvé. Le système démarrera en mode attente.")
        print("💡 Ajoutez des étudiants via l'interface web pour générer les encodages automatiquement.")
        logger.warning("Encodings file not found - starting in detection-only mode")
        known_encodings = []
        known_names = []
    except Exception as e:
        print(f"⚠️  Erreur lors du chargement des encodages: {e}")
        print("💡 Le système démarrera avec des encodages vides.")
        logger.error(f"Error loading encodings: {e}")
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
ws_last_activity = 0  # Track last WebSocket activity
ws_check_interval = 60  # Check connection every 60 seconds

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
    global ws_last_activity
    print(f"📨 WebSocket message received: {message}")
    ws_last_activity = time.time()

def on_error(ws, error):
    print(f"❌ WebSocket error: {error}")
    logger.error(f"WebSocket error: {error}")
    global ws_connected
    with ws_lock:
        ws_connected = False

def on_close(ws, close_status_code, close_msg):
    print(f"🔌 WebSocket closed (Code: {close_status_code}, Message: {close_msg})")
    global ws_connected
    with ws_lock:
        ws_connected = False

def on_open(ws):
    global ws_connected, ws_reconnect_attempts, ws_last_activity
    print("✅ WebSocket connected successfully")
    logger.info("WebSocket connection established")
    with ws_lock:
        ws_connected = True
        ws_reconnect_attempts = 0
        ws_last_activity = time.time()

def on_ping(ws, message):
    global ws_last_activity
    print("🏓 Received ping from server")
    ws_last_activity = time.time()
    # websocket-client automatically responds with pong

def on_pong(ws, message):
    global ws_last_activity
    print("🏓 Pong sent to server")
    ws_last_activity = time.time()

def connect_websocket():
    """Établit la connexion WebSocket avec meilleure gestion des erreurs"""
    global ws, ws_connected
    try:
        if ws:
            try:
                ws.close()
            except:
                pass

        print(f"🔌 Connecting to WebSocket: {WEBSOCKET_URL}")

        ws = websocket.WebSocketApp(WEBSOCKET_URL,
                                  on_open=on_open,
                                  on_message=on_message,
                                  on_error=on_error,
                                  on_close=on_close,
                                  on_ping=on_ping,
                                  on_pong=on_pong)

        # Configuration pour éviter les reconnexions trop fréquentes
        # ping_interval=None, ping_timeout=None : laisser le serveur gérer les ping/pong
        # reconnect=10 : attendre 10 secondes avant de reconnecter
        ws_thread = threading.Thread(
            target=lambda: ws.run_forever(
                ping_interval=None,  # Désactiver les ping du client
                ping_timeout=None,   # Désactiver le timeout ping du client
                reconnect=10         # Attendre 10 secondes avant de reconnecter
            ),
            daemon=True
        )
        ws_thread.start()

        # Attendre un peu pour la connexion
        time.sleep(3)

        # Vérifier si la connexion a réussi
        with ws_lock:
            if ws_connected:
                print("✅ WebSocket connection established and stable")
            else:
                print("⚠️  WebSocket connection attempt completed, but status uncertain")

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        with ws_lock:
            ws_connected = False

def check_websocket_connection():
    """Vérifie périodiquement l'état de la connexion WebSocket"""
    global ws_connected, ws_last_activity

    current_time = time.time()

    with ws_lock:
        # Si pas connecté, essayer de reconnecter
        if not ws_connected:
            print("🔌 WebSocket not connected, attempting to reconnect...")
            connect_websocket()
            return

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
        except Exception as e:
            print(f"❌ Erreur envoi WebSocket (tentative {attempt + 1}): {e}")
            with ws_lock:
                ws_connected = False

            if attempt < max_retries - 1:
                time.sleep(1)

    return False

def check_websocket_connection():
    """Vérifie périodiquement l'état de la connexion WebSocket"""
    global ws_connected, ws_last_activity

    current_time = time.time()

    with ws_lock:
        # Si pas connecté, essayer de reconnecter
        if not ws_connected:
            print("🔌 WebSocket not connected, attempting to reconnect...")
            connect_websocket()
            return

        # Vérifier si on a eu de l'activité récente (ping/pong ou messages)
        time_since_last_activity = current_time - ws_last_activity
        if time_since_last_activity > 120:  # 2 minutes sans activité
            print(f"⚠️  No WebSocket activity for {time_since_last_activity:.0f} seconds, reconnecting...")
            ws_connected = False
            connect_websocket()
        else:
            print(f"✅ WebSocket healthy (last activity: {time_since_last_activity:.0f}s ago)")

# def verify_student_exists(student_id):
#     """Verify if student exists in database before logging attendance"""
#     try:
#         response = requests.get(f"{BACKEND_URL}/api/students", timeout=5)
#         if response.status_code == 200:
#             students = response.json()
#             student_matricules = [str(student.get('matricule')) for student in students if student.get('matricule')]
#             return str(student_id) in student_matricules
#         else:
#             print(f"⚠️  Impossible de vérifier l'étudiant {student_id} (erreur {response.status_code})")
#             return True  # Continue anyway if API is down
#     except Exception as e:
#         print(f"⚠️  Erreur vérification étudiant {student_id}: {e}")
#         return True  # Continue anyway if connection fails

def log_attendance(student_id, camera_type, confidence):
    """Enregistre la présence dans le fichier CSV et envoie au backend"""
    
    print(f"🎯 RECOGNITION DETECTED: Student {student_id} on {camera_type} camera (confidence: {confidence:.3f})")
    logger.info(f"Attendance logged: Student={student_id}, Camera={camera_type}, Confidence={confidence:.3f}")
    
    
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

def draw_arrow_above_face(frame, face_location):
    """
    Draw a small arrow above an unknown face
    """
    top, right, bottom, left = face_location
    face_width = right - left
    
    # Calculate arrow position (centered above the face)
    arrow_tip_x = left + face_width // 2
    arrow_tip_y = top - 10  # 10 pixels above the face
    
    # Arrow dimensions
    arrow_length = 30
    arrow_head_size = 10
    
    # Draw arrow shaft (vertical line)
    cv2.line(frame, 
             (arrow_tip_x, arrow_tip_y), 
             (arrow_tip_x, arrow_tip_y - arrow_length), 
             (0, 0, 255),  # Red color
             2)
    
    # Draw arrow head (two lines forming a V)
    cv2.line(frame,
             (arrow_tip_x, arrow_tip_y),
             (arrow_tip_x - arrow_head_size, arrow_tip_y - arrow_head_size),
             (0, 0, 255),  # Red color
             2)
    cv2.line(frame,
             (arrow_tip_x, arrow_tip_y),
             (arrow_tip_x + arrow_head_size, arrow_tip_y - arrow_head_size),
             (0, 0, 255),  # Red color
             2)
    
    
    return frame


def save_detected_face(frame, face_location, label="detected", confidence=0.0):
    """Save every detected face to the detected_faces directory"""
    try:
        top, right, bottom, left = face_location
        face_image = frame[top:bottom, left:right]
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        face_id = f"{label}_{hash(str(face_location)) % 100000000:08x}"
        filename = f"{face_id}_{timestamp}_conf{confidence:.2f}.jpg"
        filepath = os.path.join(DETECTED_FACES_DIR, filename)
        
        cv2.imwrite(filepath, face_image)
        print(f"💾 Face sauvegardée: {filename}")
        return filepath
    except Exception as e:
        print(f"❌ Erreur sauvegarde face détectée: {e}")
        return None

def listen_for_quit():
    """Écoute les commandes clavier pour quitter"""
    while not shutdown_event.is_set():
        try:
            user_input = input().strip().lower()
            if user_input in ['q', 'quit', 'exit']:
                print("🛑 Commande d'arrêt reçue")
                shutdown_event.set()
                break
        except:
            pass

def reconnect_camera(camera_data, max_retries=5):
    """Reconnect to RTSP camera with retry logic"""
    for attempt in range(1, max_retries + 1):
        print(f"🔄 Tentative de reconnexion {attempt}/{max_retries} pour {camera_data['name']}")
        
        try:
            cap = cv2.VideoCapture(camera_data['url'], cv2.CAP_FFMPEG)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                ret, frame = cap.read()
                if ret:
                    print(f"✅ Caméra reconnectée avec succès (tentative {attempt})")
                    return cap
                else:
                    cap.release()
            else:
                if cap:
                    cap.release()
        except Exception as e:
            print(f"❌ Erreur lors de la tentative {attempt}: {e}")
        
        if attempt < max_retries:
            print(f"⏳ Attente de 2 secondes avant nouvelle tentative...")
            time.sleep(2)
    
    print(f"❌ Échec de reconnexion après {max_retries} tentatives")
    return None

def initialize_single_camera():
    """Initialize the single hardcoded camera"""
    print(f"🔄 Tentative de connexion à la caméra {SINGLE_CAMERA_NAME}...")
    print(f"   URL: {SINGLE_CAMERA_URL}")
    print(f"   Type: {SINGLE_CAMERA_TYPE}")
    
    try:
        cap = cv2.VideoCapture(SINGLE_CAMERA_URL, cv2.CAP_FFMPEG)

        if cap.isOpened():
            # Set camera properties for better far face detection
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            ret, frame = cap.read()
            if ret:
                height, width = frame.shape[:2]
                print(f"✅ Caméra {SINGLE_CAMERA_NAME} initialisée")
                print(f"   Résolution: {width}x{height}")
                
                return {
                    'cap': cap,
                    'name': SINGLE_CAMERA_NAME,
                    'type': SINGLE_CAMERA_TYPE,
                    'url': SINGLE_CAMERA_URL
                }
            else:
                print(f"❌ Impossible de lire une frame de la caméra {SINGLE_CAMERA_NAME}")
                cap.release()
        else:
            print(f"❌ Impossible d'ouvrir la caméra {SINGLE_CAMERA_NAME}")
            cap.release()
                
    except Exception as e:
        print(f"❌ Erreur avec la caméra {SINGLE_CAMERA_NAME}: {e}")
        
    return None

def enhance_image_for_face_detection(frame):
    """
    Configurable image preprocessing for face detection
    Speed: none (0ms) < fast (10-20ms) < balanced (50-100ms) < quality (500-700ms) < ESRGAN (very slow)
    """
    global esrgan_upsampler, esrgan_enabled
    
    # Try ESRGAN enhancement first if enabled (VERY SLOW)
    if esrgan_enabled and esrgan_upsampler is not None:
        try:
            # Apply Real-ESRGAN super-resolution
            enhanced_frame, _ = esrgan_upsampler.enhance(frame, outscale=ESRGAN_SCALE)
            print(f"   🎨 ESRGAN enhancement applied ({ESRGAN_SCALE}x upscaling)")
            return enhanced_frame
        except Exception as e:
            print(f"   ⚠️  ESRGAN failed: {e}, falling back to {ENHANCEMENT_LEVEL}")
            # Continue to configured enhancement below
    
    # No enhancement - use original frame
    if ENHANCEMENT_LEVEL == "none":
        print("   ⚡ No enhancement (original frame)")
        return frame
    
    # Fast enhancement - CLAHE only (~10-20ms)
    elif ENHANCEMENT_LEVEL == "fast":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)
        enhanced_frame = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
        print("   ⚡ Fast enhancement (CLAHE only)")
        return enhanced_frame
    
    # Balanced enhancement - CLAHE + sharpening (~50-100ms)
    elif ENHANCEMENT_LEVEL == "balanced":
        # Convert to LAB for better CLAHE
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        # Merge and convert back
        enhanced_frame = cv2.merge([l_enhanced, a, b])
        enhanced_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_LAB2BGR)
        
        # Light sharpening
        kernel = np.array([[-0.5, -0.5, -0.5],
                           [-0.5,  5.0, -0.5],
                           [-0.5, -0.5, -0.5]])
        enhanced_frame = cv2.filter2D(enhanced_frame, -1, kernel)
        
        print("   ⚖️  Balanced enhancement (CLAHE + sharpen)")
        return enhanced_frame
    
    # Quality enhancement - Full pipeline (~500-700ms)
    elif ENHANCEMENT_LEVEL == "quality":
        # Step 1: White balance correction
        result = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        avg_a = np.average(result[:, :, 1])
        avg_b = np.average(result[:, :, 2])
        result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 0.3)
        result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 0.3)
        balanced_frame = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
        
        # Step 2: Bilateral filter (noise reduction)
        denoised = cv2.bilateralFilter(balanced_frame, 5, 50, 50)
        
        # Step 3: CLAHE
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        # Step 4: Morphological operations
        kernel_morph = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        l_enhanced = cv2.morphologyEx(l_enhanced, cv2.MORPH_CLOSE, kernel_morph)
        
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced_frame = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        # Step 5: Histogram equalization
        yuv = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2YUV)
        yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
        enhanced_frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        
        # Step 6: Sharpening
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]]) / 1.0
        enhanced_frame = cv2.filter2D(enhanced_frame, -1, kernel)
        
        # Step 7: Gamma correction
        gray = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        if mean_brightness > 150:
            gamma = 0.8
        elif mean_brightness < 80:
            gamma = 1.4
        else:
            gamma = 1.1
        
        lookUpTable = np.empty((1, 256), np.uint8)
        for i in range(256):
            lookUpTable[0, i] = np.clip(pow(i / 255.0, gamma) * 255.0, 0, 255)
        enhanced_frame = cv2.LUT(enhanced_frame, lookUpTable)
        
        # Step 8: Detail enhancement
        enhanced_frame = cv2.detailEnhance(enhanced_frame, sigma_s=10, sigma_r=0.15)
        
        print("   💎 Quality enhancement (full pipeline)")
        return enhanced_frame
    
    else:
        # Default to fast if invalid level
        print(f"   ⚠️  Invalid ENHANCEMENT_LEVEL: {ENHANCEMENT_LEVEL}, using 'fast'")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)
        enhanced_frame = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
        return enhanced_frame

def process_frame(frame, camera_type, camera_name):
    """
    Process frame for face recognition using SCRFD detector
    Optimized for security cameras with far face detection
    """
    global known_encodings, known_names, frame_count, previous_frames
    
    frame_start_time = time.time()
    results = []
    frame_count += 1

    # Get original frame dimensions
    height, width = frame.shape[:2]
    
    # ⏱️ Scene change detection (intelligent frame skipping)
    if ENABLE_INTELLIGENT_FRAME_SKIPPING and camera_name in previous_frames:
        scene_change_start = time.time()
        
        # Convert both frames to grayscale for comparison
        gray_current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_previous = cv2.cvtColor(previous_frames[camera_name], cv2.COLOR_BGR2GRAY)
        
        # Calculate absolute difference
        frame_diff = cv2.absdiff(gray_previous, gray_current)
        
        # Apply threshold
        _, thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)
        
        # Calculate percentage of changed pixels
        changed_pixels = np.sum(thresh > 0)
        total_pixels = thresh.size
        change_percentage = (changed_pixels / total_pixels) * 100
        
        scene_change_time = (time.time() - scene_change_start) * 1000
        
        # Skip frame if change is below threshold
        if change_percentage < SCENE_CHANGE_PIXEL_THRESHOLD:
            # 🔇 No logs for skipped frames
            return results
        else:
            # 🔄 Movement detected - processing frame
            # ⏱️ Start timing - Frame enters processing
            
            print(f"\n⏱️  ========== FRAME {frame_count + 1} START ==========")
            print(f"⏱️  Frame capture time: {datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
            print(f"🔄 Movement detected ({change_percentage:.2f}% change) - Processing frame")
            pass
    
    # Store current frame for next comparison
    previous_frames[camera_name] = frame.copy()

    # ⏱️ Enhancement start
    enhancement_start = time.time()
    # Apply image enhancement for better face detection
    enhanced_frame = enhance_image_for_face_detection(frame)
    enhancement_time = (time.time() - enhancement_start) * 1000
    print(f"⏱️  Image enhancement: {enhancement_time:.2f}ms")

    # ⏱️ Detection start
    detection_start = time.time()
    # Use InsightFace SCRFD for detection
    face_locations = []
    face_data_list = []
    face_det_scores = []  # Store detection confidence for each face
    detection_time = 0  # Initialize to avoid UnboundLocalError
    
    # Check if face_app is initialized
    if face_app is None:
        detection_time = (time.time() - detection_start) * 1000
        print(f"❌ Face detection skipped - InsightFace not initialized")
        print(f"⏱️  Face detection (SCRFD 2.5G): {detection_time:.2f}ms")
        
        # Skip to end with empty results
        total_time = (time.time() - frame_start_time) * 1000
        print(f"⏱️  ========== FRAME {frame_count} COMPLETE: {total_time:.2f}ms ==========")
        print(f"⏱️  Breakdown: Enhancement={enhancement_time:.0f}ms | Detection(SCRFD)={detection_time:.0f}ms | Embedding=0ms | Recognition=0ms\n")
        return results
    
    try:
        # Detect faces with SCRFD on BOTH original and enhanced frames
        # Try enhanced frame first (better quality)
        faces = face_app.get(enhanced_frame)
        
        # If no faces found on enhanced, try original frame
        if len(faces) == 0:
            print("   🔄 No faces on enhanced frame, trying original frame...")
            faces = face_app.get(frame)
        
        # Extract bounding boxes and embeddings
        for face in faces:
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            
            # Convert to (top, right, bottom, left) format for consistency
            top, right, bottom, left = y1, x2, y2, x1
            
            face_width = right - left
            face_height = bottom - top
            
            # Get detection confidence score
            det_score = float(face.det_score) if hasattr(face, 'det_score') else 0.0
            
            # Filter faces that are too small (reduced threshold)
            if face_width >= MIN_FACE_SIZE and face_height >= MIN_FACE_SIZE:
                face_locations.append((top, right, bottom, left))
                face_data_list.append(face)
                face_det_scores.append(det_score)
                print(f"   ✅ Face {len(face_locations)}: size={face_width}x{face_height}px, confidence={det_score:.3f}, location=({left},{top})-({right},{bottom})")
        
        detection_time = (time.time() - detection_start) * 1000
        print(f"⏱️  Face detection (SCRFD 2.5G): {detection_time:.2f}ms")
        print(f"🎯 SCRFD 2.5G DETECTION RESULTS for {camera_name}:")
        print(f"   - Total faces detected: {len(faces)}")
        print(f"   - After size filtering (>={MIN_FACE_SIZE}px): {len(face_locations)}")
        logger.info(f"Face detection: {len(faces)} faces found, {len(face_locations)} after filtering (Camera: {camera_name})")
    
    except Exception as e:
        detection_time = (time.time() - detection_start) * 1000
        print(f"❌ Error during face detection: {e}")
        import traceback
        traceback.print_exc()
        faces = []
        face_data_list = []
        face_locations = []  # Ensure it's initialized

    # ⏱️ Embedding extraction start
    embedding_start = time.time()
    # Get face embeddings from detected faces
    face_embeddings = []
    embedding_time = 0  # Initialize to avoid UnboundLocalError
    
    if face_locations:
        # Extract and normalize embeddings from face objects
        for face in face_data_list:
            embedding = np.asarray(face.embedding, dtype=np.float32)
            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            face_embeddings.append(embedding)
    
    embedding_time = (time.time() - embedding_start) * 1000
    if face_locations:
        print(f"⏱️  Embedding extraction: {embedding_time:.2f}ms")
    
    # Si aucun encodage n'est disponible, sauvegarder les visages comme inconnus
    if not known_encodings or len(known_encodings) == 0:
        print(f"⚠️  No encodings available - {len(face_locations)} faces detected will be saved")
        # Save ALL detected faces
        for i, face_location in enumerate(face_locations):
            det_score = face_det_scores[i] if i < len(face_det_scores) else 0.0
            # save_detected_face(frame, face_location, label="unknown", confidence=det_score)
            # save_unknown_face(frame, face_location, confidence=det_score)
        
        total_time = (time.time() - frame_start_time) * 1000
        print(f"⏱️  ========== FRAME {frame_count} COMPLETE: {total_time:.2f}ms ==========\n")
        return results
    
    print(f"🔍 Processing {len(face_locations)} faces with {len(known_encodings)} known encodings (Camera: {camera_name})")
    
    # ⏱️ Recognition start
    recognition_start = time.time()
    recognition_time = 0  # Initialize to avoid UnboundLocalError
    current_time = time.time()
    
    # Convert known_encodings to numpy array for efficient computation
    known_encodings_array = np.array(known_encodings)
    
    # Track unknown faces to draw arrows later
    unknown_face_locations = []
    frame_with_arrows = frame.copy()  # Create a copy to draw on
    
    for i, (face_embedding, face_location) in enumerate(zip(face_embeddings, face_locations)):
        print(f"  👤 Processing face {i+1}/{len(face_embeddings)} at location {face_location}")
        
        # Get detection confidence for this face
        det_score = face_det_scores[i] if i < len(face_det_scores) else 0.0
        
        # Compute cosine similarity with all known faces
        similarities = np.dot(known_encodings_array, face_embedding)
        
        # Find best match
        best_match_index = int(np.argmax(similarities))
        best_similarity = float(similarities[best_match_index])
        
        print(f"     🎯 Best match similarity: {best_similarity:.3f} (threshold: {REC_THRESH})")
        
        if best_similarity >= REC_THRESH:
            name = known_names[best_match_index]
            confidence = best_similarity
            
            print(f"     ✅ RECOGNIZED: {name} (confidence: {confidence:.3f})")
            logger.info(f"Face recognized: Student={name}, Confidence={confidence:.3f}, Location={face_location}")
            
            # 💾 Save the recognized face
            # save_detected_face(frame, face_location, label=name, confidence=confidence)
            
            # ⏱️ Log attendance start
            log_start = time.time()
            # Check if we should log this recognition (avoid duplicates)
            last_time = last_recognition.get(name, 0)
            if current_time - last_time > 30:  # 30 seconds cooldown
                log_attendance(name, camera_type, confidence)
                last_recognition[name] = current_time
                log_time = (time.time() - log_start) * 1000
                print(f"⏱️  Attendance logging: {log_time:.2f}ms")
        else:
            print(f"     ❌ No match found - will draw arrow above face")
            # Add to unknown faces list
            unknown_face_locations.append(face_location)
            # 💾 Save individual detected face for reference
            # save_detected_face(frame, face_location, label="unknown", confidence=best_similarity)
    
    # If there are unknown faces, draw arrows and save the frame
    if unknown_face_locations:
        print(f"🔴 Found {len(unknown_face_locations)} unknown face(s) - drawing arrows and saving frame")
        logger.warning(f"Unknown faces detected: {len(unknown_face_locations)} faces (Camera: {camera_name})")
        
        # Draw arrows above all unknown faces
        for face_location in unknown_face_locations:
            frame_with_arrows = draw_arrow_above_face(frame_with_arrows, face_location)
        
        # Save the frame with arrows
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"unknown_frame_{timestamp}_{len(unknown_face_locations)}faces.jpg"
        filepath = os.path.join(UNKNOWN_DIR, filename)
        cv2.imwrite(filepath, frame_with_arrows)
        print(f"💾 Frame with {len(unknown_face_locations)} unknown face(s) saved: {filename}")
    
    recognition_time = (time.time() - recognition_start) * 1000
    print(f"⏱️  Face recognition: {recognition_time:.2f}ms")
    
    # ⏱️ Total frame processing time
    total_time = (time.time() - frame_start_time) * 1000
    print(f"⏱️  ========== FRAME {frame_count} COMPLETE: {total_time:.2f}ms ==========")
    print(f"⏱️  Breakdown: Enhancement={enhancement_time:.0f}ms | Detection(SCRFD)={detection_time:.0f}ms | Embedding={embedding_time:.0f}ms | Recognition={recognition_time:.0f}ms\n")
    
    return results


def main():
    """Fonction principale"""
    global frame_count
    
    # Initialize encodings first
    initialize_encodings()
    
    print("🚀 Démarrage du système de reconnaissance faciale (Single Camera Mode - SCRFD 2.5G)...")
    print(f"📹 Camera URL: {SINGLE_CAMERA_URL}")
    print(f"📹 Camera Name: {SINGLE_CAMERA_NAME}")
    print(f"📹 Camera Type: {SINGLE_CAMERA_TYPE}")
    print(f"🎯 Using SCRFD 2.5G detector for fast and accurate face detection!")
    logger.info("=" * 50)
    logger.info("Face Recognition System Starting")
    logger.info(f"Camera: {SINGLE_CAMERA_NAME} ({SINGLE_CAMERA_TYPE})")
    logger.info(f"URL: {SINGLE_CAMERA_URL}")
    logger.info(f"Detection Model: SCRFD 2.5G")
    logger.info(f"Enhancement Level: {ENHANCEMENT_LEVEL}")
    logger.info("=" * 50)
    
    # Établir la connexion WebSocket
    connect_websocket()
    
    # Check if we have encodings
    if not known_encodings:
        print("⚠️  Aucun encodage disponible. Le système fonctionnera en mode détection seulement.")
        print("💡 Les visages détectés seront sauvegardés comme inconnus.")
    
    # Initialize the single camera
    camera_data = initialize_single_camera()
    
    if not camera_data:
        print("❌ Impossible d'initialiser la caméra. Le programme va s'arrêter.")
        logger.error("Failed to initialize camera - system shutdown")
        return
    
    logger.info(f"Camera initialized successfully: {camera_data['name']}")
    
    # Start listener thread for quit commands
    listener_thread = threading.Thread(target=listen_for_quit, daemon=True)
    listener_thread.start()
    
    print(f"🎥 Démarrage de la reconnaissance faciale...")
    print("💡 Tapez 'q' ou 'quit' pour arrêter le programme")
    
    cap = camera_data['cap']
    camera_name = camera_data['name']
    camera_type = camera_data['type']
    
    frame_skip_counter = 0
    websocket_check_counter = 0
    camera_failure_count = 0  # Track consecutive failures
    MAX_CAMERA_FAILURES = 10  # Restart container after 10 failures

    try:
        while not shutdown_event.is_set():
            # Check for shutdown signal frequently
            if shutdown_event.is_set():
                print("🔄 Signal d'arrêt détecté, arrêt du traitement...")
                break

            # Periodic WebSocket health check (every 60 seconds)
            # websocket_check_counter += 1
            # if websocket_check_counter >= 600:  # 60 seconds * 10 iterations per second
            #     check_websocket_connection()
            #     websocket_check_counter = 0
            
            # Read frame from camera
            ret, frame = cap.read()
            
            if not ret:
                camera_failure_count += 1
                print(f"❌ Erreur lecture caméra {camera_name} (échec {camera_failure_count}/{MAX_CAMERA_FAILURES})")
                
                # Try to reconnect after 3 consecutive failures
                if camera_failure_count >= 3:
                    print("🔄 Tentative de reconnexion de la caméra...")
                    logger.warning(f"Camera connection lost - attempting reconnection (failures: {camera_failure_count})")
                    cap.release()
                    new_cap = reconnect_camera(camera_data, max_retries=5)
                    
                    if new_cap:
                        cap = new_cap
                        camera_failure_count = 0  # Reset failure counter
                        print("✅ Caméra reconnectée avec succès - reprise du traitement")
                    elif camera_failure_count >= MAX_CAMERA_FAILURES:
                        print("❌ Nombre maximum d'échecs atteint - arrêt pour redémarrage du conteneur")
                        shutdown_event.set()
                        sys.exit(1)  # Exit with error code to trigger container restart
                
                time.sleep(1)
                continue
            
            # Reset failure counter on successful frame read
            camera_failure_count = 0
            
            # Increment frame skip counter
            frame_skip_counter += 1
            
            # Only process frames every Nth iteration
            if frame_skip_counter % FRAME_SKIP_INTERVAL == 0:
                process_frame(frame, camera_type, camera_name)
            
            time.sleep(0.01)  # Small sleep to reduce CPU usage
            
        print("✅ Boucle principale terminée")
            
    except KeyboardInterrupt:
        print("\n🛑 Arrêt par Ctrl+C")
        logger.info("System shutdown requested (Ctrl+C)")
        shutdown_event.set()
    finally:
        # Nettoyer les ressources
        logger.info("Cleaning up resources...")
        shutdown_event.set()
        
        if cap:
            cap.release()
        
        cv2.destroyAllWindows()
        if ws:
            ws.close()
        
        print("🧹 Ressources nettoyées")

if __name__ == "__main__":
    main()
