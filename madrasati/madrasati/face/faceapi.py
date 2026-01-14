import os
import cv2
import pickle
import numpy as np
from PIL import Image, ImageEnhance
import time
import logging
from collections import Counter
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
import shutil
import base64
import io
from insightface.app import FaceAnalysis

# Configure logging
LOG_FILE = os.getenv('FACE_API_LOG_FILE', 'faceapilogs.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware for communication with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DATASET_DIR = os.getenv('DATASET_DIR', 'dataset')
# Updated to use ArcFace encodings
ENCODINGS_FILE_ARCFACE = os.getenv('ENCODINGS_FILE_ARCFACE', 'encodings_arcface.pkl')
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')

# InsightFace Configuration (RetinaFace + ArcFace)
INSIGHTFACE_MODEL = os.getenv('INSIGHTFACE_MODEL', 'buffalo_l')  # 'buffalo_l' (accurate) or 'buffalo_s' (fast)
USE_GPU = os.getenv('USE_GPU', 'False').lower() == 'true'  # Set to True if CUDA is available
DET_SIZE = (int(os.getenv('DET_SIZE', '640')), int(os.getenv('DET_SIZE', '640')))  # Detection input size
DET_THRESH = float(os.getenv('DET_THRESH', '0.5'))  # Detection confidence threshold

# Face detection models - now using InsightFace
FACE_MODELS = {
    'arcface': {'name': 'ArcFace (512-dim)', 'file': ENCODINGS_FILE_ARCFACE, 'fast': False, 'accurate': True}
}

# Initialize InsightFace
print("🔧 Initializing InsightFace (RetinaFace + ArcFace)...")
print("🚀 Live Editing Enabled - Changes will auto-reload!")
face_app = None

def initialize_insightface():
    """Initialize InsightFace FaceAnalysis model"""
    global face_app
    logger.info("🔧 Initializing InsightFace model...")
    try:
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if USE_GPU else ['CPUExecutionProvider']
        
        face_app = FaceAnalysis(
            name=INSIGHTFACE_MODEL,
            providers=providers
        )
        face_app.prepare(ctx_id=0 if USE_GPU else -1, det_size=DET_SIZE, det_thresh=DET_THRESH)
        
        print(f"✅ InsightFace initialized successfully!")
        print(f"   Model: {INSIGHTFACE_MODEL}")
        print(f"   Providers: {providers}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize InsightFace: {e}")
        return False

# Initialize at startup
if not initialize_insightface():
    print("⚠️  Warning: InsightFace not initialized. Face recognition will not work.")

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
    """Crée des variations de l'image pour améliorer la robustesse
    
    ✅ CAMERA QUALITY MATCHING:
    This function now includes low-quality augmentations to match security camera conditions:
    - JPEG compression (simulates camera compression)
    - Motion blur (simulates camera movement)
    - Downscaling (simulates distant faces)
    - Gaussian noise (simulates sensor noise)
    
    This ensures that high-quality dataset encodings can better match low-quality camera frames.
    """
    augmented = [image_array]
    h, w = image_array.shape[:2]
    center = (w // 2, h // 2)
    
    logger.info(f"   📸 Creating augmented images for camera quality matching...")
    
    # Existing rotations
    for angle in [5, -5, 10, -10]:
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image_array, matrix, (w, h))
        augmented.append(rotated)
    
    # Existing brightness variations
    bright = cv2.convertScaleAbs(image_array, alpha=1.1, beta=10)
    dark = cv2.convertScaleAbs(image_array, alpha=0.9, beta=-10)
    augmented.extend([bright, dark])
    
    # ✅ CAMERA QUALITY SIMULATION: Low-quality versions to match camera conditions
    logger.info(f"   📉 Adding low-quality augmentations (compression, blur, noise, distance)...")
    
    # Simulate camera compression
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]  # Low JPEG quality
    _, compressed = cv2.imencode('.jpg', image_array, encode_param)
    compressed_img = cv2.imdecode(compressed, cv2.IMREAD_COLOR)
    augmented.append(compressed_img)
    
    # Simulate motion blur
    kernel_size = 5
    kernel_motion_blur = np.zeros((kernel_size, kernel_size))
    kernel_motion_blur[int((kernel_size-1)/2), :] = np.ones(kernel_size)
    kernel_motion_blur = kernel_motion_blur / kernel_size
    blurred = cv2.filter2D(image_array, -1, kernel_motion_blur)
    augmented.append(blurred)
    
    # Simulate distance (downscale then upscale)
    small = cv2.resize(image_array, (w//2, h//2))
    distant = cv2.resize(small, (w, h))
    augmented.append(distant)
    
    # Add Gaussian noise
    noise = np.random.normal(0, 10, image_array.shape).astype(np.uint8)
    noisy = cv2.add(image_array, noise)
    augmented.append(noisy)
    
    logger.info(f"   ✅ Created {len(augmented)} augmented images (including {len(augmented)-7} low-quality variants)")
    
    return augmented
    
    return augmented

def load_existing_encodings(model='arcface'):
    """Load existing encodings for ArcFace model with normalization"""
    encodings_file = FACE_MODELS[model]['file']
    try:
        with open(encodings_file, 'rb') as f:
            data = pickle.load(f)
        
        # Ensure embeddings are normalized
        # ✅ Utiliser 'embeddings' (clé réelle dans le fichier pickle)
        encodings = data.get('embeddings', [])
        normalized_encodings = []
        for enc in encodings:
            emb = np.asarray(enc, dtype=np.float32)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            normalized_encodings.append(emb)
        
        return normalized_encodings, data.get('names', []), data.get('processed_images', {})
    except:
        return [], [], {}


@app.post("/students/add")
async def add_student(request: Request):
    logger.info("📥 API Call: POST /students/add")
    """Add student and encode face using ArcFace.

    This endpoint accepts multipart/form-data with fields:
      - matricule: str
      - photo: file (common), or 'image'/'file' etc.
      - or photoBase64: base64 string

    We read the raw form to be robust to different frontend field names and log received keys for debugging.
    """
    try:
        form = await request.form()
        # Log form keys for debugging
        keys = list(form.keys())
        print(f"🔄 /students/add called. Form keys: {keys}")

        # Try to extract matricule from form
        matricule = None
        if 'matricule' in form:
            matricule = str(form.get('matricule'))
        else:
            # try other casing
            for k in keys:
                if k.lower() == 'matricule' or k.lower() == 'id':
                    matricule = str(form.get(k))
                    break

        if not matricule:
            return {"status": "error", "message": "Missing 'matricule' field"}

        print(f"🔄 Adding student: {matricule} with ArcFace (512-dim embeddings)")

        # Create student directory in dataset
        student_dir = os.path.join(DATASET_DIR, matricule)
        os.makedirs(student_dir, exist_ok=True)
        print(f"📁 Created directory: {student_dir}")

        # Determine photo field: accept several common names
        photo_file = None
        for fname in ('photo', 'file', 'image', 'photoFile', 'photo[]'):
            if fname in form:
                photo_file = form.get(fname)
                break

        # If form contains files under a different key, pick the first UploadFile
        if photo_file is None:
            for k in keys:
                v = form.get(k)
                # UploadFile has filename attribute
                if hasattr(v, 'filename'):
                    photo_file = v
                    print(f"📁 Using uploaded file from form key: {k}")
                    break

        # If still None, check for base64 field
        base64_data = None
        for bkey in ('photoBase64', 'imageBase64', 'base64'):
            if bkey in form:
                base64_data = str(form.get(bkey))
                break

        saved_path = None
        if photo_file is not None:
            # Save UploadFile to disk
            timestamp = int(time.time())
            file_extension = os.path.splitext(photo_file.filename)[1] or '.jpg'
            photo_filename = f"{matricule}_{timestamp}{file_extension}"
            photo_path = os.path.join(student_dir, photo_filename)
            with open(photo_path, 'wb') as out_f:
                # form file-like object may be SpooledTemporaryFile or UploadFile
                try:
                    shutil.copyfileobj(photo_file.file, out_f)
                except Exception:
                    # fallback: read bytes
                    content = await photo_file.read()
                    out_f.write(content)
            saved_path = photo_path
            print(f"💾 Saved photo from upload: {photo_path}")

        elif base64_data:
            # Strip data URI prefix if present
            if base64_data.startswith('data:'):
                base64_data = base64_data.split(',')[1]
            try:
                img_bytes = base64.b64decode(base64_data)
                timestamp = int(time.time())
                photo_filename = f"{matricule}_{timestamp}.jpg"
                photo_path = os.path.join(student_dir, photo_filename)
                with open(photo_path, 'wb') as f:
                    f.write(img_bytes)
                saved_path = photo_path
                print(f"💾 Saved photo from base64 field: {photo_path}")
            except Exception as e:
                print(f"❌ Failed to decode base64 image: {e}")
                return {"status": "error", "message": "Invalid base64 image"}

        else:
            print("⚠️ No photo received in request form")
            return {"status": "error", "message": "No photo uploaded. Ensure form field name is 'photo' or 'file' or provide base64 in 'photoBase64'"}

        # Encode only this specific student (not entire dataset)
        print(f"🧠 Starting face encoding for {matricule} with ArcFace...")
        success = encode_single_student(matricule, model='arcface')

        if success:
            print(f"✅ Successfully encoded {matricule} with ArcFace")
            return {
                "status": "ok",
                "message": f"Student {matricule} added and encoded successfully with ArcFace (512-dim)",
                "model": "arcface",
                "saved_photo": saved_path
            }
        else:
            print(f"❌ Failed to encode {matricule}")
            return {
                "status": "fail",
                "message": "Face encoding failed",
                "model": "arcface"
            }

    except Exception as e:
        print(f"❌ Error adding student {locals().get('matricule', 'unknown')}: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/students/encodings/status")
async def get_encodings_status(model: str = 'arcface'):
    """Get status of ArcFace encodings"""
    logger.info(f"📊 API Call: GET /students/encodings/status?model={model}")
    try:
        if model not in FACE_MODELS:
            return {"status": "error", "message": f"Invalid model. Use: {list(FACE_MODELS.keys())}"}
        
        encodings_file = FACE_MODELS[model]['file']
        
        if not os.path.exists(encodings_file):
            return {
                "status": "no_encodings", 
                "message": f"No {FACE_MODELS[model]['name']} encodings file found",
                "total_faces": 0,
                "unique_students": 0,
                "model": model
            }
        
        known_encodings, known_names, _ = load_existing_encodings(model)
        
        # Count students in dataset
        dataset_students = 0
        if os.path.exists(DATASET_DIR):
            dataset_students = len([d for d in os.listdir(DATASET_DIR) 
                                 if os.path.isdir(os.path.join(DATASET_DIR, d))])
        
        name_counts = Counter(known_names)
        
        # Get embedding dimension
        embedding_dim = len(known_encodings[0]) if known_encodings else 0
        
        return {
            "status": "ok",
            "model": model,
            "model_name": FACE_MODELS[model]['name'],
            "embedding_dimension": embedding_dim,
            "total_faces": len(known_encodings),
            "unique_students": len(set(known_names)),
            "dataset_students": dataset_students,
            "student_face_counts": dict(name_counts),
            "encodings_file": encodings_file,
            "dataset_dir": DATASET_DIR,
            "is_accurate": FACE_MODELS[model]['accurate']
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/students/encodings/status/both")
async def get_both_encodings_status():
    """Get status of ArcFace encodings (legacy endpoint for compatibility)"""
    return await get_encodings_status(model='arcface')


@app.post("/students/encodings/rebuild")
async def rebuild_encodings():
    """Force rebuild all encodings from dataset using ArcFace"""
    logger.info("🔨 API Call: POST /students/encodings/rebuild")
    try:
        print("🔨 Force rebuilding all encodings using ArcFace (512-dim)...")
        logger.info("Starting full encodings rebuild...")
        
        success = encode_faces_from_dataset(model='arcface')
        
        if success:
            return {
                "status": "ok", 
                "message": "ArcFace encodings rebuilt successfully",
                "model": "arcface"
            }
        else:
            return {
                "status": "fail", 
                "message": "Failed to rebuild ArcFace encodings",
                "model": "arcface"
            }
            
    except Exception as e:
        print(f"❌ Error rebuilding encodings: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/students/encodings/rebuild/{model}")
async def rebuild_single_model_encodings(model: str):
    """Force rebuild encodings for ArcFace model"""
    try:
        if model not in FACE_MODELS:
            return {"status": "error", "message": f"Invalid model. Use: {list(FACE_MODELS.keys())}"}
        
        print(f"🔨 Force rebuilding encodings using {FACE_MODELS[model]['name']} model...")
        
        success = encode_faces_from_dataset(model=model)
        
        if success:
            return {
                "status": "ok", 
                "message": f"{FACE_MODELS[model]['name']} encodings rebuilt successfully",
                "model": model
            }
        else:
            return {
                "status": "fail", 
                "message": f"Failed to rebuild {FACE_MODELS[model]['name']} encodings",
                "model": model
            }
            
    except Exception as e:
        print(f"❌ Error rebuilding {model} encodings: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/students/encodings")
async def encode_student_by_id(request: Request):
    """Encode faces for a specific student by student_id"""
    try:
        body = await request.json()
        student_id = body.get('student_id')
        logger.info(f"🔄 API Call: POST /students/encodings - student_id={student_id}")
        
        if not student_id:
            return {"status": "error", "message": "Missing 'student_id' field"}
        
        print(f"🔄 Encoding student: {student_id} with ArcFace")
        
        # Check if student directory exists
        student_dir = os.path.join(DATASET_DIR, student_id)
        if not os.path.exists(student_dir):
            return {
                "status": "error", 
                "message": f"Student directory not found: {student_id}"
            }
        
        # Count images
        images = [f for f in os.listdir(student_dir) 
                 if f.lower().endswith(SUPPORTED_EXTENSIONS)]
        
        if not images:
            return {
                "status": "error",
                "message": f"No images found for student: {student_id}"
            }
        
        # Encode this specific student
        success = encode_single_student(student_id, model='arcface')
        
        if success:
            return {
                "status": "ok",
                "message": f"Successfully encoded {student_id}",
                "images_processed": len(images),
                "student_id": student_id,
                "model": "arcface"
            }
        else:
            return {
                "status": "fail",
                "message": f"Failed to encode {student_id}",
                "student_id": student_id
            }
            
    except Exception as e:
        print(f"❌ Error encoding student: {e}")
        return {"status": "error", "message": str(e)}


@app.delete("/students/{matricule}")
async def delete_student(matricule: str):
    logger.info(f"🗑️ API Call: DELETE /students/{matricule}")
    
    """Delete student WITHOUT re-encoding entire database"""
    try:
        print(f"🗑️  Deleting student: {matricule}")
        
        # Delete photos
        student_dir = os.path.join(DATASET_DIR, matricule)
        if os.path.exists(student_dir):
            shutil.rmtree(student_dir)
            print(f"📁 Removed directory: {student_dir}")
        
        # ✅ OPTIMIZED: Remove only this student's encodings
        known_encodings, known_names, _ = load_existing_encodings(model='arcface')
        
        if matricule in known_names:
            count = known_names.count(matricule)
            print(f"🔄 Removing {count} encoding(s) for {matricule}")
            
            indices_to_keep = [i for i, name in enumerate(known_names) if name != matricule]
            known_encodings = [known_encodings[i] for i in indices_to_keep]
            known_names = [known_names[i] for i in indices_to_keep]
            
            # Save updated encodings WITHOUT re-encoding
            encodings_file = FACE_MODELS['arcface']['file']
            data = {
                'embeddings': known_encodings,
                'names': known_names,
                'model': 'arcface',
                'model_name': FACE_MODELS['arcface']['name'],
                'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_faces': len(known_encodings),
                'unique_students': len(set(known_names)),
                'embedding_dimension': len(known_encodings[0]) if known_encodings else 0
            }
            
            with open(encodings_file, 'wb') as f:
                pickle.dump(data, f)
            
            print(f"✅ Student {matricule} deleted ({count} encodings removed)")
            return {
                "status": "ok",
                "message": f"Student {matricule} deleted successfully",
                "encodings_removed": count,
                "remaining_faces": len(known_encodings)
            }
        else:
            print(f"⚠️  No encodings found for {matricule}")
            return {"status": "ok", "message": f"Student {matricule} deleted (no encodings found)"}
            
    except Exception as e:
        print(f"❌ Error deleting student {matricule}: {e}")
        return {"status": "error", "message": str(e)}

@app.delete("/students/{matricule}/encodings")
async def delete_student_encodings(matricule: str):
    logger.info(f"🗑️ API Call: DELETE /students/{matricule}/encodings")
    """Delete only the encodings for a student (not the photos) - used when deleting individual photos"""
    try:
        print(f"🗑️  Deleting encodings for student: {matricule}")
        
        # Load existing encodings
        known_encodings, known_names, _ = load_existing_encodings(model='arcface')
        
        # Remove encodings for this student
        if matricule in known_names:
            count = known_names.count(matricule)
            print(f"🔄 Removing {count} encoding(s) for {matricule}")
            indices_to_keep = [i for i, name in enumerate(known_names) if name != matricule]
            known_encodings = [known_encodings[i] for i in indices_to_keep]
            known_names = [known_names[i] for i in indices_to_keep]
            
            # Save updated encodings
            encodings_file = FACE_MODELS['arcface']['file']
            data = {
                'embeddings': known_encodings,
                'names': known_names,
                'model': 'arcface',
                'model_name': FACE_MODELS['arcface']['name'],
                'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_faces': len(known_encodings),
                'unique_students': len(set(known_names)),
                'embedding_dimension': len(known_encodings[0]) if known_encodings else 0
            }
            
            with open(encodings_file, 'wb') as f:
                pickle.dump(data, f)
                
            print(f"✅ Encodings for {matricule} deleted. Remaining: {len(known_encodings)} faces")
            return {
                "status": "ok",
                "message": f"Deleted {count} encoding(s) for {matricule}",
                "remaining_faces": len(known_encodings),
                "remaining_students": len(set(known_names))
            }
        else:
            print(f"⚠️  No encodings found for {matricule}")
            return {
                "status": "ok",
                "message": f"No encodings found for {matricule}"
            }
            
    except Exception as e:
        print(f"❌ Error deleting encodings for {matricule}: {e}")
        return {"status": "error", "message": str(e)}


@app.delete("/students/{matricule}/{model}")
async def delete_student_single_model(matricule: str, model: str):
    """Delete student and re-encode with ArcFace"""
    return await delete_student(matricule)


def encode_single_student(matricule, model='arcface'):
    """Encode faces for a single student (not entire dataset) to avoid duplicates"""
    if model not in FACE_MODELS:
        print(f"❌ Invalid model: {model}. Use: {list(FACE_MODELS.keys())}")
        logger.error(f"Invalid model specified: {model}")
        return False
    
    print(f"🔄 Encoding single student: {matricule} with {FACE_MODELS[model]['name']}...")
    logger.info(f"Starting encoding for student: {matricule} using {model}")
    
    # Load existing encodings
    known_encodings, known_names, _ = load_existing_encodings(model)
    
    # Remove existing encodings for this student (avoid duplicates)
    if matricule in known_names:
        print(f"🔄 Removing {known_names.count(matricule)} existing encoding(s) for {matricule}")
        indices_to_keep = [i for i, name in enumerate(known_names) if name != matricule]
        known_encodings = [known_encodings[i] for i in indices_to_keep]
        known_names = [known_names[i] for i in indices_to_keep]
    
    # Encode new photos for this student
    person_dir = os.path.join(DATASET_DIR, matricule)
    if not os.path.isdir(person_dir):
        print(f"❌ Student directory not found: {person_dir}")
        return False
    
    student_faces = 0
    for image_name in os.listdir(person_dir):
        if not image_name.lower().endswith(SUPPORTED_EXTENSIONS):
            continue
            
        image_path = os.path.join(person_dir, image_name)
        try:
            # 🎨 Step 1: Preprocess image for better detection
            preprocessed_image = preprocess_image(image_path)
            if preprocessed_image is None:
                print(f"⚠️  Failed to preprocess {image_name}")
                continue
            
            # 🔄 Step 2: Create augmented versions for robustness
            augmented_images = create_augmented_images(preprocessed_image)
            print(f"   🎨 Created {len(augmented_images)} augmented versions of {image_name}")
            
            # 🔍 Step 3: Detect and encode faces from all augmented versions
            for aug_idx, aug_image in enumerate(augmented_images):
                # Detect faces with RetinaFace and get ArcFace embeddings
                faces = face_app.get(aug_image)
                
                # Check if faces is None or empty
                if faces is None or len(faces) == 0:
                    continue
                
                # Process each detected face
                for face in faces:
                    # Get embedding and normalize it
                    embedding = np.asarray(face.embedding, dtype=np.float32)
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = embedding / norm
                    
                    known_encodings.append(embedding)
                    known_names.append(matricule)
                    student_faces += 1
                
            print(f"   ✅ {image_name}: {student_faces} total face(s) encoded (with augmentation)")
            
        except Exception as e:
            print(f"   ❌ Error processing {image_name}: {e}")
    
    if student_faces == 0:
        print(f"❌ No faces encoded for {matricule}")
        logger.warning(f"No faces encoded for student: {matricule}")
        return False
    
    print(f"   📊 {matricule}: {student_faces} total faces encoded")
    logger.info(f"Successfully encoded {student_faces} faces for student: {matricule}")
    
    # Save updated encodings
    encodings_file = FACE_MODELS[model]['file']
    data = {
        'embeddings': known_encodings,
        'names': known_names,
        'model': model,
        'model_name': FACE_MODELS[model]['name'],
        'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
        'total_faces': len(known_encodings),
        'unique_students': len(set(known_names)),
        'embedding_dimension': len(known_encodings[0]) if known_encodings else 0
    }
    
    encodings_dir = os.path.dirname(encodings_file)
    if encodings_dir:
        os.makedirs(encodings_dir, exist_ok=True)
    
    with open(encodings_file, 'wb') as f:
        pickle.dump(data, f)
    
    logger.info(f"Encodings file saved: {encodings_file} - {len(known_encodings)} faces, {len(set(known_names))} students")
    print(f"✅ Encodings updated with {matricule} (Total: {len(known_encodings)} faces, {len(set(known_names))} students)")
    return True


def encode_faces_from_dataset(model='arcface'):
    """Encode faces from dataset directory structure using ArcFace (InsightFace)"""
    if model not in FACE_MODELS:
        print(f"❌ Invalid model: {model}. Use: {list(FACE_MODELS.keys())}")
        logger.error(f"Invalid model specified: {model}")
        return False
    
    print(f"🔄 Starting face encoding from dataset using {FACE_MODELS[model]['name']}...")
    logger.info(f"Starting full dataset encoding using {model}")
    
    # Create dataset directory if it doesn't exist
    os.makedirs(DATASET_DIR, exist_ok=True)
    
    # Check if dataset has any directories
    if not os.path.exists(DATASET_DIR) or not os.listdir(DATASET_DIR):
        print("❌ No students found in dataset directory")
        return False
    
    # Load existing encodings for this model
    known_encodings, known_names, processed_images = load_existing_encodings(model)
    total_faces_encoded = 0
    total_students = 0

    for person_name in sorted(os.listdir(DATASET_DIR)):
        person_dir = os.path.join(DATASET_DIR, person_name)
        if not os.path.isdir(person_dir):
            continue
            
        total_students += 1
        student_faces = 0
        
        print(f"📸 Processing student: {person_name} with {FACE_MODELS[model]['name']}")
        
        for image_name in os.listdir(person_dir):
            if not image_name.lower().endswith(SUPPORTED_EXTENSIONS):
                continue
                
            image_path = os.path.join(person_dir, image_name)
            try:
                # 🎨 Step 1: Preprocess image for better detection
                preprocessed_image = preprocess_image(image_path)
                if preprocessed_image is None:
                    print(f"⚠️  Failed to preprocess {image_name}")
                    continue
                
                # 🔄 Step 2: Create augmented versions for robustness (camera quality matching)
                augmented_images = create_augmented_images(preprocessed_image)
                print(f"   🎨 Created {len(augmented_images)} augmented versions of {image_name}")
                
                # 🔍 Step 3: Detect and encode faces from all augmented versions
                for aug_idx, aug_image in enumerate(augmented_images):
                    # Detect faces with RetinaFace and get ArcFace embeddings
                    faces = face_app.get(aug_image)
                    
                    # Check if faces is None or empty
                    if faces is None or len(faces) == 0:
                        continue
                    
                    # Process each detected face
                    for face in faces:
                        # Get embedding and normalize it (L2 normalization)
                        embedding = np.asarray(face.embedding, dtype=np.float32)
                        norm = np.linalg.norm(embedding)
                        if norm > 0:
                            embedding = embedding / norm
                        
                        known_encodings.append(embedding)
                        known_names.append(person_name)
                        total_faces_encoded += 1
                        student_faces += 1
                    
                print(f"   ✅ {image_name}: {student_faces} face(s) encoded with augmentation")
                
            except Exception as e:
                print(f"   ❌ Error processing {image_name} with {FACE_MODELS[model]['name']}: {e}")
        
        print(f"   📊 {person_name}: {student_faces} total faces encoded with {FACE_MODELS[model]['name']}")

    print(f"\n📈 {FACE_MODELS[model]['name']} encoding complete:")
    print(f"   - Students processed: {total_students}")
    print(f"   - Total faces encoded: {total_faces_encoded}")
    print(f"   - Unique students: {len(set(known_names))}")
    print(f"   - Model used: {FACE_MODELS[model]['name']}")
    print(f"   - Embedding dimension: {len(known_encodings[0]) if known_encodings else 'N/A'}")

    if known_encodings and total_faces_encoded > 0:
        # Save encodings for this model
        encodings_file = FACE_MODELS[model]['file']
        # ✅ Utiliser 'embeddings' pour cohérence avec le fichier existant
        data = {
            'embeddings': known_encodings,
            'names': known_names,
            'model': model,
            'model_name': FACE_MODELS[model]['name'],
            'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'total_faces': total_faces_encoded,
            'unique_students': len(set(known_names)),
            'embedding_dimension': len(known_encodings[0])
        }
        
        # Ensure encodings directory exists
        encodings_dir = os.path.dirname(encodings_file)
        if encodings_dir:
            os.makedirs(encodings_dir, exist_ok=True)
        
        with open(encodings_file, 'wb') as f:
            pickle.dump(data, f)
            
        print(f"✅ {FACE_MODELS[model]['name']} encodings saved to {encodings_file}")
        return True
    else:
        print(f"❌ No faces were encoded successfully with {FACE_MODELS[model]['name']}")
        return False

