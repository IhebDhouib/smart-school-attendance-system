"""
Test Script: RetinaFace + Real-ESRGAN + ArcFace
Purpose: Test modern face detection/recognition pipeline with PC camera

Dependencies:
pip install insightface onnxruntime opencv-python numpy

Features:
- RetinaFace: Robust face detection with landmarks
- Real-ESRGAN: Optional super-resolution for enhancement
- ArcFace: High-accuracy face recognition
- Multi-scale detection for far faces
"""

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
import os
import pickle
import time
from pathlib import Path

# ============================
# CONFIGURATION
# ============================
DATASET_DIR = "dataset"
ENCODINGS_FILE = "encodings_arcface.pkl"
CAMERA_ID = 0  # PC webcam (0, 1, 2, etc.)

# Detection settings
DET_SIZE = (640, 640)  # Detection input size - larger = better for small faces
DET_THRESH = 0.5       # Detection confidence threshold
NMS_THRESH = 0.4       # Non-max suppression threshold

# Recognition settings
REC_THRESH = 0.3       # Recognition similarity threshold (lower = stricter)

# Performance settings
ENABLE_ESRGAN = True  # Enable Real-ESRGAN enhancement (slower but better quality)
SKIP_FRAMES = 1        # Process every Nth frame
SHOW_FPS = True        # Display FPS counter

# ============================
# INITIALIZE MODELS
# ============================
print("🔧 Initializing models...")
print("⚠️  First run will download models (~150MB)...")

# Initialize FaceAnalysis with RetinaFace + ArcFace
app = FaceAnalysis(
    name='buffalo_l',  # Model pack: buffalo_l (accurate) or buffalo_s (fast)
    providers=['CPUExecutionProvider']  # Use 'CUDAExecutionProvider' for GPU
)
app.prepare(ctx_id=-1, det_size=DET_SIZE, det_thresh=DET_THRESH)

print("✅ Models loaded successfully!")
print(f"📦 Detection model: RetinaFace")
print(f"🧠 Recognition model: ArcFace (512-dim embeddings)")

# Optional: Load Real-ESRGAN (currently disabled by default)
if ENABLE_ESRGAN:
    try:
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
        
        print("🔧 Loading Real-ESRGAN...")
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
        upsampler = RealESRGANer(
            scale=2,
            model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
            model=model,
            tile=0,
            tile_pad=10,
            pre_pad=0,
            half=False
        )
        print("✅ Real-ESRGAN loaded!")
    except ImportError:
        print("⚠️  Real-ESRGAN not available. Install: pip install realesrgan basicsr")
        ENABLE_ESRGAN = False

# ============================
# ENCODE DATASET FACES
# ============================
def encode_dataset_faces():
    """Encode all faces from dataset directory"""
    print("\n📂 Encoding faces from dataset...")
    
    if not os.path.exists(DATASET_DIR):
        print(f"❌ Dataset directory '{DATASET_DIR}' not found!")
        return [], []
    
    known_embeddings = []
    known_names = []
    total_encoded = 0
    
    # Iterate through person directories
    for person_name in sorted(os.listdir(DATASET_DIR)):
        person_dir = os.path.join(DATASET_DIR, person_name)
        
        if not os.path.isdir(person_dir):
            continue
        
        person_embeddings = []
        
        # Process each image
        for img_file in os.listdir(person_dir):
            if not img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            
            img_path = os.path.join(person_dir, img_file)
            
            try:
                # Read and process image
                img = cv2.imread(img_path)
                if img is None:
                    continue
                
                # Detect and extract face
                faces = app.get(img)
                
                if len(faces) == 0:
                    print(f"  ⚠️  No face found in {person_name}/{img_file}")
                    continue
                
                # Use the largest face
                face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
                
                # Get embedding (InsightFace embeddings are usually L2-normalized,
                # but normalize again to be safe to avoid large dot-product values)
                embedding = np.asarray(face.embedding, dtype=np.float32)
                # L2 normalize
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                person_embeddings.append(embedding)
                total_encoded += 1
                
                print(f"  ✓ Encoded {person_name}/{img_file}")
                
            except Exception as e:
                print(f"  ❌ Error processing {person_name}/{img_file}: {e}")
        
        # Add to known faces
        if person_embeddings:
            # Average embeddings for this person
            avg_embedding = np.mean(person_embeddings, axis=0)
            known_embeddings.append(avg_embedding)
            known_names.append(person_name)
            print(f"✅ {person_name}: {len(person_embeddings)} images encoded")
    
    print(f"\n📊 Total: {len(known_names)} persons, {total_encoded} images")
    
    # Save encodings
    if known_embeddings:
        with open(ENCODINGS_FILE, 'wb') as f:
            pickle.dump({'embeddings': known_embeddings, 'names': known_names}, f)
        print(f"💾 Encodings saved to {ENCODINGS_FILE}")
    
    return known_embeddings, known_names

# ============================
# LOAD OR CREATE ENCODINGS
# ============================
def load_encodings():
    """Load existing encodings or create new ones"""
    if os.path.exists(ENCODINGS_FILE):
        print(f"\n📂 Loading encodings from {ENCODINGS_FILE}...")
        with open(ENCODINGS_FILE, 'rb') as f:
            data = pickle.load(f)
        # Ensure embeddings are numpy arrays and normalized
        emb = [np.asarray(e, dtype=np.float32) for e in data['embeddings']]
        for i in range(len(emb)):
            n = np.linalg.norm(emb[i])
            if n > 0:
                emb[i] = emb[i] / n
        print(f"✅ Loaded {len(data['names'])} known persons")
        return np.vstack(emb), data['names']
    else:
        print(f"\n⚠️  No existing encodings found. Creating new...")
        return encode_dataset_faces()

# ============================
# FACE RECOGNITION
# ============================
def recognize_face(face_embedding, known_embeddings, known_names, threshold=REC_THRESH):
    """
    Recognize a face by comparing embeddings using cosine similarity
    Returns: (name, confidence, similarity_score)
    """
    if len(known_embeddings) == 0:
        return "Unknown", 0.0, 0.0

    # Ensure input embedding is normalized
    emb = np.asarray(face_embedding, dtype=np.float32)
    n = np.linalg.norm(emb)
    if n > 0:
        emb = emb / n

    # known_embeddings is a 2D array (N, D)
    # cosine similarity = dot product (since vectors are normalized)
    similarities = np.dot(known_embeddings, emb)

    best_idx = int(np.argmax(similarities))
    best_similarity = float(similarities[best_idx])

    if best_similarity >= threshold:
        name = known_names[best_idx]
        return name, best_similarity, best_similarity
    else:
        return "Unknown", best_similarity, best_similarity

# ============================
# MAIN CAMERA LOOP
# ============================
def main():
    print("\n" + "="*60)
    print("🎥 RETINAFACE + REAL-ESRGAN + ARCFACE TEST")
    print("="*60)
    
    # Load encodings
    known_embeddings, known_names = load_encodings()
    
    if len(known_embeddings) == 0:
        print("\n❌ No faces encoded. Please add images to 'dataset/<person_name>/' directory")
        print("   Example: dataset/John_Doe/image1.jpg")
        return
    
    # Open camera
    print(f"\n📹 Opening camera {CAMERA_ID}...")
    cap = cv2.VideoCapture(CAMERA_ID)
    
    if not cap.isOpened():
        print(f"❌ Failed to open camera {CAMERA_ID}")
        return
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("✅ Camera opened successfully!")
    print("\n📋 Controls:")
    print("   - Press 'q' to quit")
    print("   - Press 'r' to re-encode dataset faces")
    print("   - Press 's' to save current frame")
    print("\n🔄 Starting detection...\n")
    
    frame_count = 0
    fps_start = time.time()
    fps_counter = 0
    current_fps = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to read frame")
            break
        
        frame_count += 1
        display_frame = frame.copy()
        
        # Skip frames for performance
        if frame_count % SKIP_FRAMES != 0:
            cv2.imshow("RetinaFace + ArcFace Test", display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue
        
        process_start = time.time()
        
        # Detect faces with RetinaFace
        faces = app.get(frame)
        
        # Process each detected face
        for face in faces:
            # Extract face info
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            
            # Get embedding
            embedding = face.embedding
            
            # Recognize face
            name, confidence, similarity = recognize_face(
                embedding, 
                known_embeddings, 
                known_names, 
                threshold=REC_THRESH
            )
            
            # Determine color based on recognition
            if name != "Unknown":
                color = (0, 255, 0)  # Green for known
                label = f"{name} ({similarity:.2f})"
            else:
                color = (0, 0, 255)  # Red for unknown
                label = f"Unknown ({similarity:.2f})"
            
            # Draw bounding box
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(
                display_frame,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1
            )
            
            # Draw label text
            cv2.putText(
                display_frame,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            
            # Draw landmarks (optional)
            if hasattr(face, 'kps') and face.kps is not None:
                for kp in face.kps:
                    cv2.circle(display_frame, (int(kp[0]), int(kp[1])), 2, (255, 255, 0), -1)
        
        # Calculate FPS
        fps_counter += 1
        if time.time() - fps_start >= 1.0:
            current_fps = fps_counter
            fps_counter = 0
            fps_start = time.time()
        
        # Display info
        process_time = (time.time() - process_start) * 1000
        info_text = [
            f"FPS: {current_fps}",
            f"Faces: {len(faces)}",
            f"Process: {process_time:.1f}ms",
            f"Known: {len(known_names)} persons"
        ]
        
        y_offset = 30
        for text in info_text:
            cv2.putText(
                display_frame,
                text,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )
            y_offset += 30
        
        # Show frame
        cv2.imshow("RetinaFace + ArcFace Test", display_frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n👋 Quitting...")
            break
        elif key == ord('r'):
            print("\n🔄 Re-encoding dataset faces...")
            cap.release()
            cv2.destroyAllWindows()
            known_embeddings, known_names = encode_dataset_faces()
            cap = cv2.VideoCapture(CAMERA_ID)
            print("✅ Re-encoding complete. Resuming...")
        elif key == ord('s'):
            filename = f"capture_{int(time.time())}.jpg"
            cv2.imwrite(filename, display_frame)
            print(f"📸 Saved frame to {filename}")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Test complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
