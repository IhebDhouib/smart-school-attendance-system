"""
Optimized Face Recognition System for Security Cameras
Major improvements:
- Eliminated redundant processing and memory waste
- Added intelligent frame skipping and ROI tracking
- Improved memory management with object pooling
- Better error handling and resource cleanup
- Streamlined multi-processing architecture
- Enhanced configuration management
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
from multiprocessing import shared_memory, Value, Array
import shutil
import signal
import psutil
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock, Event
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('face_recognition.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Suppress warnings
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

@dataclass
class CameraConfig:
    """Camera configuration data class"""
    id: str
    name: str
    type: str
    url: str
    ip: str
    port: int
    username: str = ""
    password: str = ""
    status: str = "active"

@dataclass
class DetectionResult:
    """Face detection result data class"""
    type: str  # 'recognition' or 'unknown_face'
    name: Optional[str] = None
    confidence: Optional[float] = None
    face_location: Optional[Tuple[int, int, int, int]] = None
    camera_name: str = ""
    camera_type: str = ""
    timestamp: float = 0.0

class Config:
    """Centralized configuration management"""
    # File paths
    ENCODINGS_FILE = "encodings/encodings.pkl"
    UNKNOWN_DIR = "unknown_faces"
    LOG_FILE = "logs/logs.csv"
    
    # Backend configuration
    BACKEND_URL = "http://localhost:3000"
    WEBSOCKET_URL = "ws://localhost:3001"
    
    # Face detection settings
    FACE_DETECTION_MODEL = 'hog'  # Use hog for speed, cnn for accuracy
    MIN_FACE_SIZE = 40
    MAX_FACES_PER_FRAME = 5  # Reduced from 10 for better performance
    RECOGNITION_TOLERANCE = 0.6
    
    # Performance settings
    FRAME_SKIP_INTERVAL = 3  # Process every 3rd frame
    MAX_CPU_PROCESSES = min(8, mp.cpu_count())  # More reasonable limit
    DUPLICATE_DETECTION_COOLDOWN = 30  # seconds
    
    # Camera settings
    CAMERA_WIDTH = 1280  # Reduced from 1920 for better performance
    CAMERA_HEIGHT = 720   # Reduced from 1080
    CAMERA_FPS = 10       # Reduced from 15
    
    # Buffer sizes
    CAMERA_BUFFER_SIZE = 2
    ENCODING_CACHE_SIZE = 1000

class ObjectPool:
    """Object pool for memory management"""
    def __init__(self):
        self.frame_buffers = deque(maxlen=20)
        self.result_objects = deque(maxlen=100)
    
    def get_frame_buffer(self, shape):
        if self.frame_buffers:
            buffer = self.frame_buffers.popleft()
            if buffer.shape == shape:
                return buffer
        return np.empty(shape, dtype=np.uint8)
    
    def return_frame_buffer(self, buffer):
        if len(self.frame_buffers) < 20:
            self.frame_buffers.append(buffer)

class EncodingManager:
    """Manages face encodings with thread safety"""
    def __init__(self):
        self.lock = Lock()
        self.encodings = []
        self.names = []
        self.last_modified = 0
        self.encoding_cache = {}
    
    def load_encodings(self) -> bool:
        """Load encodings from file"""
        try:
            if not os.path.exists(Config.ENCODINGS_FILE):
                logger.warning(f"Encodings file not found: {Config.ENCODINGS_FILE}")
                return False
            
            with open(Config.ENCODINGS_FILE, "rb") as f:
                data = pickle.load(f)
            
            with self.lock:
                self.encodings = data.get("encodings", [])
                self.names = data.get("names", [])
                self.last_modified = time.time()
            
            if self.encodings:
                logger.info(f"Loaded {len(self.encodings)} encodings for {len(set(self.names))} people")
                return True
            else:
                logger.warning("No encodings found in file")
                return False
                
        except Exception as e:
            logger.error(f"Error loading encodings: {e}")
            return False
    
    def get_encodings(self) -> Tuple[List, List]:
        """Get thread-safe copy of encodings"""
        with self.lock:
            return self.encodings.copy(), self.names.copy()
    
    def is_empty(self) -> bool:
        """Check if encodings are empty"""
        with self.lock:
            return len(self.encodings) == 0

class CameraManager:
    """Manages camera connections and configurations"""
    def __init__(self):
        self.cameras: Dict[str, Any] = {}
        self.lock = Lock()
        self.failed_cameras = set()
    
    def fetch_camera_configs(self) -> List[CameraConfig]:
        """Fetch camera configurations from backend"""
        try:
            response = requests.get(f"{Config.BACKEND_URL}/api/cameras", timeout=10)
            if response.status_code == 200:
                cameras_data = response.json()
                configs = []
                for cam_data in cameras_data:
                    if cam_data.get('status') == 'active':
                        config = CameraConfig(
                            id=cam_data.get('_id', 'unknown'),
                            name=cam_data.get('name', 'Unknown'),
                            type=cam_data.get('type', 'entry'),
                            ip=cam_data.get('ip', ''),
                            port=cam_data.get('port', 8080),
                            username=cam_data.get('username', ''),
                            password=cam_data.get('password', ''),
                            url=self._build_camera_url(cam_data)
                        )
                        if config.url:
                            configs.append(config)
                return configs
            else:
                logger.error(f"Failed to fetch cameras: HTTP {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching camera configurations: {e}")
            return []
    
    def _build_camera_url(self, camera_data) -> str:
        """Build camera URL from configuration"""
        ip = camera_data.get('ip')
        port = camera_data.get('port', 8080)
        username = camera_data.get('username', '')
        password = camera_data.get('password', '')
        
        if not ip:
            return ""
        
        if username and password:
            return f"http://{username}:{password}@{ip}:{port}/video"
        else:
            return f"http://{ip}:{port}/video"
    
    def initialize_camera(self, config: CameraConfig) -> Optional[cv2.VideoCapture]:
        """Initialize a single camera"""
        try:
            cap = cv2.VideoCapture(config.url, cv2.CAP_FFMPEG)
            if cap.isOpened():
                # Set optimized camera properties
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Test frame capture
                ret, frame = cap.read()
                if ret:
                    logger.info(f"Camera {config.name} initialized successfully")
                    return cap
                else:
                    logger.error(f"Cannot read from camera {config.name}")
                    cap.release()
            else:
                logger.error(f"Cannot open camera {config.name}")
        except Exception as e:
            logger.error(f"Error initializing camera {config.name}: {e}")
        
        return None
    
    def initialize_all_cameras(self) -> Dict[str, Any]:
        """Initialize all cameras in parallel"""
        configs = self.fetch_camera_configs()
        if not configs:
            logger.warning("No camera configurations found")
            return {}
        
        camera_data = {}
        with ThreadPoolExecutor(max_workers=min(len(configs), 5)) as executor:
            future_to_config = {
                executor.submit(self.initialize_camera, config): config 
                for config in configs
            }
            
            for future in as_completed(future_to_config):
                config = future_to_config[future]
                try:
                    cap = future.result()
                    if cap:
                        camera_data[config.id] = {
                            'cap': cap,
                            'config': config,
                            'buffer': deque(maxlen=Config.CAMERA_BUFFER_SIZE),
                            'last_frame_time': 0,
                            'frame_skip_counter': 0
                        }
                except Exception as e:
                    logger.error(f"Exception initializing camera {config.name}: {e}")
        
        with self.lock:
            self.cameras = camera_data
        
        logger.info(f"Initialized {len(camera_data)} cameras")
        return camera_data

class FaceProcessor:
    """Optimized face processing with intelligent detection"""
    def __init__(self, encoding_manager: EncodingManager):
        self.encoding_manager = encoding_manager
        self.object_pool = ObjectPool()
        self.roi_trackers = {}  # Track regions of interest
        self.scene_change_threshold = 30.0  # For intelligent frame skipping
    
    def enhance_image_fast(self, frame: np.ndarray) -> np.ndarray:
        """Fast image enhancement for face detection"""
        # Simplified enhancement - only CLAHE on luminance
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        l_enhanced = clahe.apply(l)
        
        enhanced = cv2.merge([l_enhanced, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    def detect_scene_change(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> bool:
        """Detect if scene has changed significantly"""
        if prev_frame is None:
            return True
        
        # Convert to grayscale for faster comparison
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate difference
        diff = cv2.absdiff(prev_gray, curr_gray)
        mean_diff = np.mean(diff)
        
        return mean_diff > self.scene_change_threshold
    
    def process_frame(self, frame_data: Tuple) -> List[DetectionResult]:
        """Process frame for face recognition - optimized version"""
        frame, camera_name, camera_type, prev_frame = frame_data
        
        # Get current encodings
        known_encodings, known_names = self.encoding_manager.get_encodings()
        if not known_encodings:
            return []
        
        # Intelligent frame skipping based on scene change
        if prev_frame is not None and not self.detect_scene_change(prev_frame, frame):
            return []  # Skip processing if scene hasn't changed much
        
        # Fast enhancement
        enhanced_frame = self.enhance_image_fast(frame)
        rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
        
        # Single-scale detection for performance (can be expanded if needed)
        face_locations = face_recognition.face_locations(
            rgb_frame, 
            model=Config.FACE_DETECTION_MODEL,
            number_of_times_to_upsample=1
        )
        
        if not face_locations:
            return []
        
        # Filter faces by minimum size
        filtered_locations = []
        for top, right, bottom, left in face_locations:
            face_width = right - left
            face_height = bottom - top
            if face_width >= Config.MIN_FACE_SIZE and face_height >= Config.MIN_FACE_SIZE:
                filtered_locations.append((top, right, bottom, left))
        
        if not filtered_locations:
            return []
        
        # Limit number of faces processed
        if len(filtered_locations) > Config.MAX_FACES_PER_FRAME:
            # Sort by face size and keep largest
            face_sizes = [(bottom - top) * (right - left) for top, right, bottom, left in filtered_locations]
            sorted_indices = np.argsort(face_sizes)[::-1][:Config.MAX_FACES_PER_FRAME]
            filtered_locations = [filtered_locations[i] for i in sorted_indices]
        
        # Get face encodings
        try:
            face_encodings = face_recognition.face_encodings(rgb_frame, filtered_locations)
        except Exception as e:
            logger.error(f"Error generating face encodings: {e}")
            return []
        
        # Process recognition
        results = []
        current_time = time.time()
        
        for face_encoding, face_location in zip(face_encodings, filtered_locations):
            try:
                # Compare with known faces
                face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    min_distance = face_distances[best_match_index]
                    
                    if min_distance <= Config.RECOGNITION_TOLERANCE:
                        name = known_names[best_match_index]
                        confidence = 1 - min_distance
                        
                        result = DetectionResult(
                            type='recognition',
                            name=name,
                            confidence=confidence,
                            face_location=face_location,
                            camera_name=camera_name,
                            camera_type=camera_type,
                            timestamp=current_time
                        )
                        results.append(result)
                    else:
                        # Unknown face - reduced frequency saving
                        result = DetectionResult(
                            type='unknown_face',
                            face_location=face_location,
                            camera_name=camera_name,
                            camera_type=camera_type,
                            timestamp=current_time
                        )
                        results.append(result)
                        
            except Exception as e:
                logger.error(f"Error processing face recognition: {e}")
                continue
        
        return results

class AttendanceLogger:
    """Handles attendance logging with batching"""
    def __init__(self):
        self.last_recognition = {}
        self.batch_queue = deque()
        self.batch_lock = Lock()
        self.ws_connection = None
    
    def should_log_attendance(self, student_id: str, current_time: float) -> bool:
        """Check if attendance should be logged (avoid duplicates)"""
        if student_id not in self.last_recognition:
            return True
        
        time_diff = current_time - self.last_recognition[student_id]
        return time_diff > Config.DUPLICATE_DETECTION_COOLDOWN
    
    def log_attendance(self, student_id: str, camera_type: str, confidence: float):
        """Log attendance with improved error handling"""
        current_time = time.time()
        
        if not self.should_log_attendance(student_id, current_time):
            return
        
        self.last_recognition[student_id] = current_time
        
        # First, get student's classId from backend
        class_id = None
        try:
            response = requests.get(
                f"{Config.BACKEND_URL}/api/students/{student_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                student_data = response.json()
                class_id = student_data.get('classId')
                if isinstance(class_id, dict) and '_id' in class_id:
                    class_id = class_id['_id']
                logger.info(f"📋 Retrieved classId for student {student_id}: {class_id}")
            else:
                logger.warning(f"⚠️ Could not retrieve student data for {student_id} (status: {response.status_code})")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch student data: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching student data: {e}")
        
        # Prepare attendance data for backend
        attendance_data = {
            "studentId": student_id,
            "cameraType": camera_type,
            "confidence": float(confidence),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Add classId if available
        if class_id:
            attendance_data["classId"] = class_id
        
        # Send to backend API
        try:
            response = requests.post(
                f"{Config.BACKEND_URL}/api/attendance",
                json=attendance_data,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Attendance sent to backend: {student_id} on {camera_type} (confidence: {confidence:.2f})")
            elif response.status_code == 400 and "already recorded" in response.text.lower():
                logger.info(f"ℹ️ Attendance already recorded today for {student_id}")
            else:
                logger.warning(f"⚠️ Backend returned status {response.status_code} for attendance: {student_id}")
                logger.warning(f"Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to send attendance to backend: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error sending attendance: {e}")
        
        # Log to CSV as backup
        try:
            timestamp_csv = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)
            
            with open(Config.LOG_FILE, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([timestamp_csv, student_id, camera_type, f"{confidence:.2f}"])
            
            logger.info(f"📝 Attendance logged to CSV: {student_id} on {camera_type} (confidence: {confidence:.2f})")
            
        except Exception as e:
            logger.error(f"❌ Error logging to CSV: {e}")
    
    def save_unknown_face(self, frame: np.ndarray, face_location: Tuple[int, int, int, int], camera_name: str):
        """Save unknown face with rate limiting"""
        try:
            top, right, bottom, left = face_location
            face_image = frame[top:bottom, left:right]
            
            if face_image.size == 0:
                return
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unknown_id = f"unknown_{hash(str(face_location)) % 100000000:08x}"
            filename = f"{unknown_id}_{timestamp}.jpg"
            
            os.makedirs(Config.UNKNOWN_DIR, exist_ok=True)
            filepath = os.path.join(Config.UNKNOWN_DIR, filename)
            
            cv2.imwrite(filepath, face_image)
            logger.info(f"Unknown face saved: {filename} from {camera_name}")
            
        except Exception as e:
            logger.error(f"Error saving unknown face: {e}")

class FaceRecognitionSystem:
    """Main system orchestrator"""
    def __init__(self):
        self.shutdown_event = Event()
        self.encoding_manager = EncodingManager()
        self.camera_manager = CameraManager()
        self.face_processor = FaceProcessor(self.encoding_manager)
        self.attendance_logger = AttendanceLogger()
        self.previous_frames = {}  # Store previous frames for scene change detection
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        self.shutdown_event.set()
    
    def initialize(self) -> bool:
        """Initialize the entire system"""
        logger.info("Initializing Face Recognition System...")
        
        # Create required directories
        os.makedirs(Config.UNKNOWN_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)
        
        # Load encodings
        if not self.encoding_manager.load_encodings():
            logger.warning("No encodings loaded - system will run in detection-only mode")
        
        # Initialize cameras
        cameras = self.camera_manager.initialize_all_cameras()
        if not cameras:
            logger.warning("No cameras initialized - API mode only")
            return False
        
        logger.info(f"System initialized with {len(cameras)} cameras")
        return True
    
    def process_camera_frames(self):
        """Main processing loop with optimized architecture"""
        cameras = self.camera_manager.cameras
        frame_count = 0
        
        # Use fewer processes for better resource management
        num_processes = min(Config.MAX_CPU_PROCESSES, len(cameras) * 2)
        logger.info(f"Starting processing with {num_processes} processes")
        
        with ProcessPoolExecutor(max_workers=num_processes) as process_executor:
            while not self.shutdown_event.is_set():
                frame_count += 1
                
                # Skip frames based on interval
                if frame_count % Config.FRAME_SKIP_INTERVAL != 0:
                    time.sleep(0.01)
                    continue
                
                # Collect frames from all cameras (I/O bound - use threads)
                frame_data_list = []
                with ThreadPoolExecutor(max_workers=len(cameras)) as thread_executor:
                    frame_futures = {}
                    
                    for cam_id, cam_data in cameras.items():
                        if cam_data['cap'].isOpened():
                            future = thread_executor.submit(cam_data['cap'].read)
                            frame_futures[future] = (cam_id, cam_data)
                    
                    # Collect frames as they complete
                    for future in as_completed(frame_futures):
                        cam_id, cam_data = frame_futures[future]
                        try:
                            ret, frame = future.result()
                            if ret:
                                config = cam_data['config']
                                prev_frame = self.previous_frames.get(cam_id)
                                
                                frame_data = (
                                    frame,
                                    config.name,
                                    config.type,
                                    prev_frame
                                )
                                frame_data_list.append((cam_id, frame_data, frame))
                            
                        except Exception as e:
                            logger.error(f"Error reading from camera {cam_id}: {e}")
                
                if not frame_data_list:
                    time.sleep(0.1)
                    continue
                
                # Process frames (CPU bound - use processes)
                processing_futures = []
                for cam_id, frame_data, raw_frame in frame_data_list:
                    future = process_executor.submit(self.face_processor.process_frame, frame_data)
                    processing_futures.append((future, cam_id, raw_frame))
                
                # Process results
                for future, cam_id, raw_frame in processing_futures:
                    try:
                        results = future.result(timeout=5.0)  # Add timeout
                        
                        # Update previous frame for scene change detection
                        self.previous_frames[cam_id] = raw_frame
                        
                        # Process recognition results
                        for result in results:
                            if result.type == 'recognition':
                                self.attendance_logger.log_attendance(
                                    result.name, 
                                    result.camera_type, 
                                    result.confidence
                                )
                            elif result.type == 'unknown_face':
                                # Rate-limited unknown face saving
                                if frame_count % 100 == 0:  # Save every 100th frame
                                    self.attendance_logger.save_unknown_face(
                                        raw_frame, 
                                        result.face_location, 
                                        result.camera_name
                                    )
                    
                    except Exception as e:
                        logger.error(f"Error processing recognition results: {e}")
                
                # Adaptive sleep based on system load
                cpu_percent = psutil.cpu_percent(interval=0.1)
                if cpu_percent > 80:
                    time.sleep(0.1)
                else:
                    time.sleep(0.05)
    
    def run(self):
        """Main entry point"""
        try:
            if not self.initialize():
                logger.error("Failed to initialize system")
                return
            
            logger.info("Starting face recognition processing...")
            self.process_camera_frames()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        self.shutdown_event.set()
        
        # Close cameras
        for cam_data in self.camera_manager.cameras.values():
            if cam_data.get('cap'):
                cam_data['cap'].release()
        
        # Only destroy windows if GUI is available
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            # Expected in headless environments
            pass
        
        logger.info("Cleanup completed")

def main():
    """Main function"""
    # Set multiprocessing start method
    if hasattr(mp, 'set_start_method'):
        try:
            mp.set_start_method('spawn', force=True)
        except RuntimeError:
            pass
    
    # Create and run the system
    system = FaceRecognitionSystem()
    system.run()

if __name__ == "__main__":
    main()