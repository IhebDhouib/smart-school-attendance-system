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
    student_dir = os.path.join(DATASET_DIR, matricule)
    os.makedirs(student_dir, exist_ok=True)

    # Save uploaded photo
    if photo:
        photo_path = os.path.join(student_dir, photo.filename)
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

    # Run encoding after adding
    success = encode_faces_from_dataset()
    return {"status": "ok" if success else "fail"}


@app.delete("/students/{matricule}")
async def delete_student(matricule: str):
    """Delete student and re-encode"""
    student_dir = os.path.join(DATASET_DIR, matricule)
    if os.path.exists(student_dir):
        shutil.rmtree(student_dir)

    # Re-encode after deletion
    success = encode_faces_from_dataset()
    return {"status": "ok" if success else "fail"}


def encode_faces_from_dataset():
    """Your existing encoding function (simplified)"""
    known_encodings, known_names, processed_images = load_existing_encodings()
    total_faces_encoded = 0

    for person_name in sorted(os.listdir(DATASET_DIR)):
        person_dir = os.path.join(DATASET_DIR, person_name)
        if not os.path.isdir(person_dir):
            continue
        for image_name in os.listdir(person_dir):
            if not image_name.lower().endswith(SUPPORTED_EXTENSIONS):
                continue
            image_path = os.path.join(person_dir, image_name)
            try:
                image = face_recognition.load_image_file(image_path)
                encs = face_recognition.face_encodings(image)
                for enc in encs:
                    known_encodings.append(enc)
                    known_names.append(person_name)
                    total_faces_encoded += 1
            except Exception as e:
                print("Error:", e)

    if known_encodings:
        data = {
            'encodings': known_encodings,
            'names': known_names,
            'created_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(ENCODINGS_FILE, 'wb') as f:
            pickle.dump(data, f)
        return True
    return False

