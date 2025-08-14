import os
import cv2
import pickle
import numpy as np
import face_recognition
from PIL import Image, ImageEnhance
import time
from collections import Counter
from utils_copy import load_config, validate_encodings

# Configuration
DATASET_DIR = "dataset"
ENCODINGS_FILE = "encodings.pkl"
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
    """Charge les encodages existants et les métadonnées"""
    try:
        with open(ENCODINGS_FILE, 'rb') as f:
            data = pickle.load(f)
        print(f"✅ Encodages existants trouvés: {len(data['encodings'])} encodages pour {len(set(data['names']))} personnes")
        return data.get('encodings', []), data.get('names', []), data.get('processed_images', {})
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return [], [], {}

def encode_faces_from_dataset():
    """Encode les visages du dataset, en évitant les images déjà traitées"""
    print("🚀 Démarrage de l'encodage des visages...\n")
    
    if not validate_dataset():
        return False
    
    config = load_config()
    model = config.get("model", "hog")
    
    known_encodings, known_names, processed_images = load_existing_encodings()
    
    if known_encodings:
        print("\n⚠️ Fichier d'encodages existant détecté.")
        choice = input("Voulez-vous [o] écraser, [u] mettre à jour, ou [s] sauter l'encodage ? (o/u/s) : ").strip().lower()
        if choice == 's':
            print("⏭️ Encodage sauté, utilisation des encodages existants.")
            return True
        elif choice == 'o':
            known_encodings, known_names, processed_images = [], [], {}
            print("🔄 Écrasement des encodages existants.")
        else:
            print("🔄 Mise à jour des encodages existants.")
    
    total_images_processed = 0
    total_faces_encoded = len(known_encodings)
    failed_images = []
    
    start_time = time.time()
    
    for person_name in sorted(os.listdir(DATASET_DIR)):
        person_dir = os.path.join(DATASET_DIR, person_name)
        
        if not os.path.isdir(person_dir):
            continue
        
        print(f"🔄 Traitement de: {person_name}")
        person_encodings = 0
        
        images = [f for f in os.listdir(person_dir) 
                 if f.lower().endswith(SUPPORTED_EXTENSIONS)]
        
        for image_name in images:
            image_path = os.path.join(person_dir, image_name)
            image_mtime = os.path.getmtime(image_path)
            
            if choice == 'u' and image_path in processed_images and processed_images[image_path] == image_mtime:
                print(f"  ⏭️ {image_name} déjà encodée et non modifiée, passage...")
                continue
            
            total_images_processed += 1
            print(f"  📸 {image_name}...", end=" ")
            
            try:
                image_array = preprocess_image(image_path)
                if image_array is None:
                    print("❌ Échec du preprocessing")
                    failed_images.append(image_path)
                    continue
                
                augmented_images = create_augmented_images(image_array)
                image_encodings = 0
                
                for i, aug_image in enumerate(augmented_images):
                    face_locations = face_recognition.face_locations(aug_image, model=model)
                    
                    if not face_locations:
                        if i == 0:
                            print("⚠️ Aucun visage détecté")
                        continue
                    
                    face_encodings = face_recognition.face_encodings(aug_image, [face_locations[0]])
                    
                    if face_encodings:
                        known_encodings.append(face_encodings[0])
                        known_names.append(person_name)
                        image_encodings += 1
                        total_faces_encoded += 1
                
                if image_encodings > 0:
                    print(f"✅ {image_encodings} encodages")
                    person_encodings += image_encodings
                    processed_images[image_path] = image_mtime
                else:
                    print("❌ Aucun encodage créé")
                    failed_images.append(image_path)
                
            except Exception as e:
                print(f"❌ Erreur: {e}")
                failed_images.append(image_path)
        
        print(f"  ✅ Total pour {person_name}: {person_encodings} encodages\n")
    
    # Sauvegarder les encodages
    if known_encodings:
        print("💾 Sauvegarde des encodages...")
        
        data = {
            'encodings': known_encodings,
            'names': known_names,
            'processed_images': processed_images,
            'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'total_images': total_images_processed,
            'total_encodings': total_faces_encoded
        }
        
        with open(ENCODINGS_FILE, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"✅ Encodages sauvegardés dans: {ENCODINGS_FILE}")
        
        elapsed_time = time.time() - start_time
        name_counts = Counter(known_names)
        
        print(f"\n📊 Statistiques finales:")
        print(f"  ⏱️ Temps d'exécution: {elapsed_time:.2f} secondes")
        print(f"  📸 Images traitées: {total_images_processed}")
        print(f"  🎯 Encodages créés: {total_faces_encoded}")
        print(f"  👥 Personnes: {len(name_counts)}")
        print(f"  📈 Moyenne: {total_faces_encoded/len(name_counts):.1f} encodages par personne")
        
        print(f"\n📋 Répartition par personne:")
        for name, count in name_counts.most_common():
            print(f"  - {name}: {count} encodages")
        
        if failed_images:
            print(f"\n⚠️ Images échouées ({len(failed_images)}):")
            for img in failed_images:
                print(f"  - {img}")
        
        return True
    
    else:
        print("❌ Aucun encodage créé! Vérifiez vos images.")
        return False

def test_encodings():
    """Test les encodages créés"""
    print("\n🧪 Test des encodages...")
    stats = validate_encodings(verbose=True)
    return stats['valid']

def main():
    """Fonction principale"""
    print("🎭 ENCODAGE DES VISAGES")
    print("=" * 50)
    
    if not os.path.exists(DATASET_DIR):
        os.makedirs(DATASET_DIR)
        print(f"📁 Dossier '{DATASET_DIR}' créé")
    
    success = encode_faces_from_dataset()
    
    if success:
        test_encodings()
        print("\n🎉 Encodage terminé avec succès!")
        print("💡 Vous pouvez maintenant exécuter app.py pour la reconnaissance")
    else:
        print("\n❌ Échec de l'encodage")
        
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
# import os
# import cv2
# import pickle
# import numpy as np
# import face_recognition
# from PIL import Image, ImageEnhance
# import time
# from collections import Counter

# # Configuration
# DATASET_DIR = "dataset"
# ENCODINGS_FILE = "encodings.pkl"
# SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')


# def validate_dataset():
#     """Valide la structure du dataset"""
#     print("🔍 Validation du dataset...")
    
#     total_persons = 0
#     total_images = 0
    
#     for person_name in os.listdir(DATASET_DIR):
#         person_dir = os.path.join(DATASET_DIR, person_name)
        
#         if not os.path.isdir(person_dir):
#             print(f"⚠️ Ignoré (pas un dossier): {person_name}")
#             continue
        
#         images = [f for f in os.listdir(person_dir) 
#                  if f.lower().endswith(SUPPORTED_EXTENSIONS)]
        
#         if len(images) == 0:
#             print(f"⚠️ Aucune image trouvée dans: {person_name}")
#             continue
        
#         total_persons += 1
#         total_images += len(images)
#         print(f"✅ {person_name}: {len(images)} images")
    
#     print(f"\n📊 Dataset: {total_persons} personnes, {total_images} images total")
    
#     if total_persons == 0:
#         print("❌ Aucune personne valide trouvée dans le dataset!")
#         return False
    
#     return True

# def preprocess_image(image_path):
#     """Préprocesse une image pour améliorer la détection"""
#     try:
#         # Charger l'image
#         image = cv2.imread(image_path)
#         if image is None:
#             print(f"❌ Impossible de charger: {image_path}")
#             return None
        
#         # Convertir en RGB
#         image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
#         # Améliorer le contraste si nécessaire
#         pil_image = Image.fromarray(image_rgb)
#         enhancer = ImageEnhance.Contrast(pil_image)
#         enhanced = enhancer.enhance(1.2)  # Augmenter légèrement le contraste
        
#         return np.array(enhanced)
    
#     except Exception as e:
#         print(f"❌ Erreur preprocessing {image_path}: {e}")
#         return None

# def create_augmented_images(image_array):
#     """Crée des variations de l'image pour améliorer la robustesse"""
#     augmented = [image_array]  # Image originale
    
#     # Rotation légère
#     h, w = image_array.shape[:2]
#     center = (w // 2, h // 2)
    
#     for angle in [5, -5, 10, -10]:
#         matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
#         rotated = cv2.warpAffine(image_array, matrix, (w, h))
#         augmented.append(rotated)
    
#     # Ajustement de luminosité
#     bright = cv2.convertScaleAbs(image_array, alpha=1.1, beta=10)
#     dark = cv2.convertScaleAbs(image_array, alpha=0.9, beta=-10)
#     augmented.extend([bright, dark])
    
#     return augmented

# def encode_faces_from_dataset():
#     """Encode tous les visages du dataset"""
#     print("🚀 Démarrage de l'encodage des visages...\n")
    
#     if not validate_dataset():
#         return False
    
#     known_encodings = []
#     known_names = []
    
#     total_images_processed = 0
#     total_faces_encoded = 0
#     failed_images = []
    
#     start_time = time.time()
    
#     # Parcourir chaque personne
#     for person_name in sorted(os.listdir(DATASET_DIR)):
#         person_dir = os.path.join(DATASET_DIR, person_name)
        
#         if not os.path.isdir(person_dir):
#             continue
        
#         print(f"🔄 Traitement de: {person_name}")
#         person_encodings = 0
        
#         # Parcourir chaque image de la personne
#         images = [f for f in os.listdir(person_dir) 
#                  if f.lower().endswith(SUPPORTED_EXTENSIONS)]
        
#         for image_name in images:
#             image_path = os.path.join(person_dir, image_name)
#             total_images_processed += 1
            
#             print(f"  📸 {image_name}...", end=" ")
            
#             try:
#                 # Préprocesser l'image
#                 image_array = preprocess_image(image_path)
#                 if image_array is None:
#                     print("❌ Échec du preprocessing")
#                     failed_images.append(image_path)
#                     continue
                
#                 # Créer des variations de l'image
#                 augmented_images = create_augmented_images(image_array)
                
#                 image_encodings = 0
                
#                 for i, aug_image in enumerate(augmented_images):
#                     # Détecter les visages
#                     face_locations = face_recognition.face_locations(aug_image, model="hog")
                    
#                     if not face_locations:
#                         if i == 0:  # Seulement pour l'image originale
#                             print("⚠️ Aucun visage détecté", end=" ")
#                         continue
                    
#                     # Encoder le premier visage détecté
#                     face_encodings = face_recognition.face_encodings(aug_image, [face_locations[0]])
                    
#                     if face_encodings:
#                         known_encodings.append(face_encodings[0])
#                         known_names.append(person_name)
#                         image_encodings += 1
#                         total_faces_encoded += 1
                
#                 if image_encodings > 0:
#                     print(f"✅ {image_encodings} encodages")
#                     person_encodings += image_encodings
#                 else:
#                     print("❌ Aucun encodage créé")
#                     failed_images.append(image_path)
                
#             except Exception as e:
#                 print(f"❌ Erreur: {e}")
#                 failed_images.append(image_path)
        
#         print(f"  ✅ Total pour {person_name}: {person_encodings} encodages\n")
    
#     # Sauvegarder les encodages
#     if known_encodings:
#         print("💾 Sauvegarde des encodages...")
        
#         data = {
#             'encodings': known_encodings,
#             'names': known_names,
#             'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
#             'total_images': total_images_processed,
#             'total_encodings': total_faces_encoded
#         }
        
#         with open(ENCODINGS_FILE, 'wb') as f:
#             pickle.dump(data, f)
        
#         print(f"✅ Encodages sauvegardés dans: {ENCODINGS_FILE}")
        
#         # Statistiques finales
#         elapsed_time = time.time() - start_time
#         name_counts = Counter(known_names)
        
#         print(f"\n📊 Statistiques finales:")
#         print(f"  ⏱️ Temps d'exécution: {elapsed_time:.2f} secondes")
#         print(f"  📸 Images traitées: {total_images_processed}")
#         print(f"  🎯 Encodages créés: {total_faces_encoded}")
#         print(f"  👥 Personnes: {len(name_counts)}")
#         print(f"  📈 Moyenne: {total_faces_encoded/len(name_counts):.1f} encodages par personne")
        
#         print(f"\n📋 Répartition par personne:")
#         for name, count in name_counts.most_common():
#             print(f"  - {name}: {count} encodages")
        
#         if failed_images:
#             print(f"\n⚠️ Images échouées ({len(failed_images)}):")
#             for img in failed_images:
#                 print(f"  - {img}")
        
#         return True
    
#     else:
#         print("❌ Aucun encodage créé! Vérifiez vos images.")
#         return False

# def test_encodings():
#     """Test les encodages créés"""
#     print("\n🧪 Test des encodages...")
    
#     try:
#         with open(ENCODINGS_FILE, 'rb') as f:
#             data = pickle.load(f)
        
#         encodings = data['encodings']
#         names = data['names']
        
#         print(f"✅ Fichier chargé avec succès")
#         print(f"  - {len(encodings)} encodages")
#         print(f"  - {len(set(names))} personnes uniques")
        
#         # Vérifier la cohérence
#         if len(encodings) != len(names):
#             print("❌ Incohérence: nombre d'encodages ≠ nombre de noms")
#             return False
        
#         # Vérifier la forme des encodages
#         if encodings:
#             encoding_shape = encodings[0].shape
#             print(f"  - Forme des encodages: {encoding_shape}")
            
#             if encoding_shape != (128,):
#                 print("⚠️ Forme d'encodage inhabituelle (attendu: (128,))")
        
#         return True
        
#     except FileNotFoundError:
#         print("❌ Fichier d'encodages non trouvé")
#         return False
#     except Exception as e:
#         print(f"❌ Erreur lors du test: {e}")
#         return False

# def main():
#     """Fonction principale"""
#     print("🎭 ENCODAGE DES VISAGES")
#     print("=" * 50)
    
#     # Créer le dataset s'il n'existe pas
#     if not os.path.exists(DATASET_DIR):
#         os.makedirs(DATASET_DIR)
#         print(f"📁 Dossier '{DATASET_DIR}' créé")
    
#     # Encoder les visages
#     success = encode_faces_from_dataset()
    
#     if success:
#         # Tester les encodages
#         test_encodings()
        
#         print("\n🎉 Encodage terminé avec succès!")
#         print("💡 Vous pouvez maintenant exécuter app.py pour la reconnaissance")
#     else:
#         print("\n❌ Échec de l'encodage")
        
#     print("\n" + "=" * 50)

# if __name__ == "__main__":
#     main()