import os
import cv2
import pickle
import numpy as np
import face_recognition
from PIL import Image, ImageEnhance
import time
from collections import Counter
from fastapi import FastAPI, UploadFile, Form
import shutil

app = FastAPI()

# Configuration
DATASET_DIR = "dataset"
ENCODINGS_FILE = "/app/encodings/encodings.pkl"
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')

def validate_dataset():
    """Valide la structure du dataset"""
    print("🔍 Validation du dataset...")
    
    total_persons = 0
    total_images = 0
    
    for person_name in os.listdir(DATASET_DIR):
        person_dir = os.path.join(DATASET_DIR, person_name)
        
        if not os.path.isdir(person_dir):
            print(f"⚠️ Ignoré (pas un dossier): {person_name}")
            continue
        
        images = [f for f in os.listdir(person_dir) 
                 if f.lower().endswith(SUPPORTED_EXTENSIONS)]
        
        if len(images) == 0:
            print(f"⚠️ Aucune image trouvée dans: {person_name}")
            continue
        
        total_persons += 1
        total_images += len(images)
        print(f"✅ {person_name}: {len(images)} images")
    
    print(f"\n📊 Dataset: {total_persons} personnes, {total_images} images total")
    
    if total_persons == 0:
        print("❌ Aucune personne valide trouvée dans le dataset!")
        return False
    
    return True

def preprocess_image(image_path):
    """Préprocesse une image pour améliorer la détection"""
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Impossible de charger: {image_path}")
            return None
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced = enhancer.enhance(1.2)
        return np.array(enhanced)
    
    except Exception as e:
        print(f"❌ Erreur preprocessing {image_path}: {e}")
        return None

def create_augmented_images(image_array):
    """Crée des variations de l'image pour améliorer la robustesse"""
    augmented = [image_array]
    h, w = image_array.shape[:2]
    center = (w // 2, h // 2)
    
    for angle in [5, -5, 10, -10]:
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_array, matrix, (w, h))
        augmented.append(rotated)
    
    bright = cv2.convertScaleAbs(image_array, alpha=1.1, beta=10)
    dark = cv2.convertScaleAbs(image_array, alpha=0.9, beta=-10)
    augmented.extend([bright, dark])
    
    return augmented

def load_existing_encodings():
    try:
        with open(ENCODINGS_FILE, 'rb') as f:
            data = pickle.load(f)
        return data.get('encodings', []), data.get('names', []), data.get('processed_images', {})
    except:
        return [], [], {}


@app.post("/students/add")
async def add_student(matricule: str = Form(...), photo: UploadFile = None):
    """Add student and encode face"""
    try:
        print(f"🔄 Adding student: {matricule}")
        
        # Create student directory in dataset
        student_dir = os.path.join(DATASET_DIR, matricule)
        os.makedirs(student_dir, exist_ok=True)
        print(f"📁 Created directory: {student_dir}")

        # Save uploaded photo
        if photo:
            # Generate unique filename to avoid conflicts
            timestamp = int(time.time())
            file_extension = os.path.splitext(photo.filename)[1] or '.jpg'
            photo_filename = f"{matricule}_{timestamp}{file_extension}"
            photo_path = os.path.join(student_dir, photo_filename)
            
            with open(photo_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            print(f"💾 Saved photo: {photo_path}")

        # Run encoding after adding
        print("🧠 Starting face encoding...")
        success = encode_faces_from_dataset()
        
        if success:
            print(f"✅ Successfully encoded faces for {matricule}")
            return {"status": "ok", "message": f"Student {matricule} added and encoded successfully"}
        else:
            print(f"❌ Failed to encode faces for {matricule}")
            return {"status": "fail", "message": "Face encoding failed"}
            
    except Exception as e:
        print(f"❌ Error adding student {matricule}: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/students/encodings/status")
async def get_encodings_status():
    """Get status of face encodings"""
    try:
        if not os.path.exists(ENCODINGS_FILE):
            return {
                "status": "no_encodings", 
                "message": "No encodings file found",
                "total_faces": 0,
                "unique_students": 0
            }
        
        known_encodings, known_names, _ = load_existing_encodings()
        
        # Count students in dataset
        dataset_students = 0
        if os.path.exists(DATASET_DIR):
            dataset_students = len([d for d in os.listdir(DATASET_DIR) 
                                 if os.path.isdir(os.path.join(DATASET_DIR, d))])
        
        name_counts = Counter(known_names)
        
        return {
            "status": "ok",
            "total_faces": len(known_encodings),
            "unique_students": len(set(known_names)),
            "dataset_students": dataset_students,
            "student_face_counts": dict(name_counts),
            "encodings_file": ENCODINGS_FILE,
            "dataset_dir": DATASET_DIR
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/students/encodings/rebuild")
async def rebuild_encodings():
    """Force rebuild all encodings from dataset"""
    try:
        print("🔨 Force rebuilding all encodings...")
        
        # Clear existing encodings by starting fresh
        success = encode_faces_from_dataset()
        
        if success:
            return {"status": "ok", "message": "All encodings rebuilt successfully"}
        else:
            return {"status": "fail", "message": "Failed to rebuild encodings"}
            
    except Exception as e:
        print(f"❌ Error rebuilding encodings: {e}")
        return {"status": "error", "message": str(e)}


@app.delete("/students/{matricule}")
async def delete_student(matricule: str):
    """Delete student and re-encode"""
    try:
        print(f"🗑️  Deleting student: {matricule}")
        
        student_dir = os.path.join(DATASET_DIR, matricule)
        if os.path.exists(student_dir):
            shutil.rmtree(student_dir)
            print(f"📁 Removed directory: {student_dir}")
        else:
            print(f"⚠️  Directory not found: {student_dir}")

        # Re-encode after deletion
        print("🧠 Re-encoding remaining faces...")
        success = encode_faces_from_dataset()
        
        if success:
            print(f"✅ Successfully removed {matricule} and re-encoded")
            return {"status": "ok", "message": f"Student {matricule} deleted and faces re-encoded"}
        else:
            print(f"❌ Failed to re-encode after deleting {matricule}")
            return {"status": "fail", "message": "Re-encoding failed after deletion"}
            
    except Exception as e:
        print(f"❌ Error deleting student {matricule}: {e}")
        return {"status": "error", "message": str(e)}


def encode_faces_from_dataset():
    """Encode faces from dataset directory structure"""
    print("🔄 Starting face encoding from dataset...")
    
    # Create dataset directory if it doesn't exist
    os.makedirs(DATASET_DIR, exist_ok=True)
    
    # Check if dataset has any directories
    if not os.path.exists(DATASET_DIR) or not os.listdir(DATASET_DIR):
        print("❌ No students found in dataset directory")
        return False
    
    # Load existing encodings 
    known_encodings, known_names, processed_images = load_existing_encodings()
    total_faces_encoded = 0
    total_students = 0

    for person_name in sorted(os.listdir(DATASET_DIR)):
        person_dir = os.path.join(DATASET_DIR, person_name)
        if not os.path.isdir(person_dir):
            continue
            
        total_students += 1
        student_faces = 0
        
        print(f"📸 Processing student: {person_name}")
        
        for image_name in os.listdir(person_dir):
            if not image_name.lower().endswith(SUPPORTED_EXTENSIONS):
                continue
                
            image_path = os.path.join(person_dir, image_name)
            try:
                # Load and process image
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                
                if not face_locations:
                    print(f"⚠️  No faces found in {image_name}")
                    continue
                
                # Get face encodings
                face_encodings = face_recognition.face_encodings(image, face_locations)
                
                for encoding in face_encodings:
                    known_encodings.append(encoding)
                    known_names.append(person_name)
                    total_faces_encoded += 1
                    student_faces += 1
                    
                print(f"   ✅ {image_name}: {len(face_encodings)} face(s) encoded")
                
            except Exception as e:
                print(f"   ❌ Error processing {image_name}: {e}")
        
        print(f"   📊 {person_name}: {student_faces} total faces encoded")

    print(f"\n📈 Encoding complete:")
    print(f"   - Students processed: {total_students}")
    print(f"   - Total faces encoded: {total_faces_encoded}")
    print(f"   - Unique students: {len(set(known_names))}")

    if known_encodings and total_faces_encoded > 0:
        # Save encodings
        data = {
            'encodings': known_encodings,
            'names': known_names,
            'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'total_faces': total_faces_encoded,
            'unique_students': len(set(known_names))
        }
        
        # Ensure encodings directory exists
        encodings_dir = os.path.dirname(ENCODINGS_FILE)
        os.makedirs(encodings_dir, exist_ok=True)
        
        with open(ENCODINGS_FILE, 'wb') as f:
            pickle.dump(data, f)
            
        print(f"✅ Encodings saved to {ENCODINGS_FILE}")
        return True
    else:
        print("❌ No faces were encoded successfully")
        return False

