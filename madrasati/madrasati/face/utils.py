import face_recognition
import numpy as np
import pickle
import os
import pandas as pd
from datetime import datetime, timedelta
import cv2
import json
from collections import Counter

# Configuration
ENCODINGS_PATH = "encodings.pkl"
LOG_FILE = "logs/logs.csv"
CONFIG_FILE = "config.json"

# Configuration par défaut
DEFAULT_CONFIG = {
    "tolerance": 0.6,
    "model": "hog",
    "scale_factor": 0.25,
    "recognition_cooldown": 30,
    "save_unknown_faces": True,
    "log_level": "INFO"
}

def load_config():
    """Charge la configuration depuis le fichier JSON"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            # Fusionner avec la config par défaut
            return {**DEFAULT_CONFIG, **config}
        else:
            # Créer le fichier de config par défaut
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"❌ Erreur chargement config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    """Sauvegarde la configuration dans le fichier JSON"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde config: {e}")
        return False

def load_encodings():
    """Charge les encodages depuis le fichier pickle"""
    try:
        with open(ENCODINGS_PATH, "rb") as f:
            data = pickle.load(f)
        
        encodings = data.get("encodings", [])
        names = data.get("names", [])
        
        if len(encodings) != len(names):
            print("⚠️ Incohérence détectée dans les encodages")
            return [], []
        
        return encodings, names
        
    except FileNotFoundError:
        print(f"❌ Fichier {ENCODINGS_PATH} non trouvé.")
        print("💡 Exécutez encode_faces.py pour créer les encodages")
        return [], []
    except Exception as e:
        print(f"❌ Erreur lors du chargement des encodages: {e}")
        return [], []

def recognize_faces_in_frame(frame, known_encodings, known_names, config=None):
    """
    Reconnaît tous les visages dans une frame
    
    Args:
        frame: Image OpenCV (BGR)
        known_encodings: Liste des encodages connus
        known_names: Liste des noms correspondants
        config: Configuration (optionnel)
    
    Returns:
        Liste de dictionnaires avec les informations des visages reconnus
    """
    if config is None:
        config = load_config()
    
    # Réduire la taille pour améliorer les performances
    scale_factor = config.get("scale_factor", 0.25)
    small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    # Détecter les visages
    model = config.get("model", "hog")
    face_locations = face_recognition.face_locations(rgb_frame, model=model)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    recognized_faces = []
    tolerance = config.get("tolerance", 0.6)
    
    for (face_encoding, face_location) in zip(face_encodings, face_locations):
        name = "Inconnu"
        confidence = 0.0
        distance = 1.0
        
        if known_encodings:
            # Comparer avec les visages connus
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                distance = face_distances[best_match_index]
                
                # Vérifier la correspondance et la distance
                if matches[best_match_index] and distance < tolerance:
                    name = known_names[best_match_index]
                    confidence = 1 - distance
        
        # Redimensionner les coordonnées à la taille originale
        top, right, bottom, left = [int(v / scale_factor) for v in face_location]
        
        recognized_faces.append({
            'name': name,
            'location': (top, right, bottom, left),
            'confidence': confidence,
            'distance': distance,
            'is_known': name != "Inconnu"
        })
    
    return recognized_faces

def recognize_single_face(frame, known_encodings, known_names, config=None):
    """
    Version simplifiée pour reconnaître un seul visage
    Retourne le nom du visage avec la meilleure confiance ou "Inconnu"
    """
    faces = recognize_faces_in_frame(frame, known_encodings, known_names, config)
    
    if faces:
        # Retourner le visage connu avec la meilleure confiance
        known_faces = [f for f in faces if f['is_known']]
        if known_faces:
            best_face = max(known_faces, key=lambda x: x['confidence'])
            return best_face['name']
    
    return "Inconnu"

def log_attendance(name, action="présence", additional_info=None):
    """
    Enregistre la présence dans le fichier CSV
    
    Args:
        name: Nom de la personne
        action: Type d'action (entrée, sortie, présence, etc.)
        additional_info: Informations supplémentaires (optionnel)
    """
    # Créer le dossier logs s'il n'existe pas
    log_dir = os.path.dirname(LOG_FILE) if os.path.dirname(LOG_FILE) else "."
    if log_dir != "." and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d %H:%M:%S")
    date_only = now.strftime("%Y-%m-%d")
    time_only = now.strftime("%H:%M:%S")
    
    # Préparer les données
    log_data = {
        "Nom": name,
        "Action": action,
        "DateTime": date_time,
        "Date": date_only,
        "Heure": time_only,
        "Info": additional_info or ""
    }
    
    try:
        # Vérifier si le fichier existe et a des en-têtes
        file_exists = os.path.exists(LOG_FILE)
        
        if file_exists:
            # Lire le fichier existant pour vérifier la structure
            try:
                existing_df = pd.read_csv(LOG_FILE)
                if existing_df.empty or list(existing_df.columns) != list(log_data.keys()):
                    # Restructurer si nécessaire
                    file_exists = False
            except:
                file_exists = False
        
        log_df = pd.DataFrame([log_data])
        
        if file_exists:
            log_df.to_csv(LOG_FILE, mode='a', header=False, index=False)
        else:
            log_df.to_csv(LOG_FILE, index=False)
        
        print(f"📝 Log: {name} - {action} à {time_only}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'enregistrement du log: {e}")
        return False

def get_attendance_summary(date=None, person_name=None):
    """
    Obtient un résumé de la présence
    
    Args:
        date: Date au format YYYY-MM-DD (par défaut: aujourd'hui)
        person_name: Nom spécifique d'une personne (optionnel)
    
    Returns:
        DataFrame avec le résumé de présence
    """
    if not os.path.exists(LOG_FILE):
        print("❌ Aucun fichier de logs trouvé.")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(LOG_FILE)
        
        if df.empty:
            print("❌ Fichier de logs vide.")
            return pd.DataFrame()
        
        # Nettoyer les données
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df = df.dropna(subset=['DateTime'])
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Filtrer par date
        if 'Date' in df.columns:
            day_logs = df[df['Date'] == date].copy()
        else:
            day_logs = df[df['DateTime'].dt.strftime('%Y-%m-%d') == date].copy()
        
        # Filtrer par personne si spécifié
        if person_name:
            day_logs = day_logs[day_logs['Nom'] == person_name]
        
        if day_logs.empty:
            print(f"❌ Aucun log trouvé pour {person_name or 'toutes les personnes'} le {date}")
            return pd.DataFrame()
        
        # Grouper par personne et calculer les statistiques
        summary = day_logs.groupby('Nom').agg({
            'Action': 'count',
            'Heure': ['first', 'last'],
            'DateTime': ['min', 'max']
        }).round(2)
        
        # Aplatir les colonnes multi-niveaux
        summary.columns = ['Nombre_détections', 'Première_heure', 'Dernière_heure', 'Premier_datetime', 'Dernier_datetime']
        
        # Calculer la durée de présence
        summary['Durée_présence'] = summary.apply(
            lambda row: str(row['Dernier_datetime'] - row['Premier_datetime']).split('.')[0], 
            axis=1
        )
        
        # Supprimer les colonnes datetime intermédiaires
        summary = summary.drop(['Premier_datetime', 'Dernier_datetime'], axis=1)
        
        return summary
        
    except Exception as e:
        print(f"❌ Erreur lors de la lecture des logs: {e}")
        return pd.DataFrame()

def get_weekly_stats():
    """Obtient les statistiques de la semaine"""
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(LOG_FILE)
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df = df.dropna(subset=['DateTime'])
        
        # Dernière semaine
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        week_logs = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
        
        if week_logs.empty:
            return pd.DataFrame()
        
        # Grouper par date et personne
        week_logs['Date'] = week_logs['DateTime'].dt.strftime('%Y-%m-%d')
        daily_stats = week_logs.groupby(['Date', 'Nom']).size().unstack(fill_value=0)
        
        return daily_stats
        
    except Exception as e:
        print(f"❌ Erreur calcul stats hebdomadaires: {e}")
        return pd.DataFrame()

def clean_old_logs(days_to_keep=30):
    """
    Nettoie les anciens logs
    
    Args:
        days_to_keep: Nombre de jours à conserver
    """
    if not os.path.exists(LOG_FILE):
        print("📁 Aucun fichier de logs à nettoyer.")
        return
    
    try:
        df = pd.read_csv(LOG_FILE)
        
        if df.empty:
            print("📁 Fichier de logs vide.")
            return
        
        # Convertir les dates
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df = df.dropna(subset=['DateTime'])
        
        # Date limite
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Filtrer les logs récents
        recent_logs = df[df['DateTime'] >= cutoff_date]
        
        # Compter les logs supprimés
        removed_count = len(df) - len(recent_logs)
        
        if removed_count > 0:
            # Sauvegarder les logs récents
            recent_logs.to_csv(LOG_FILE, index=False)
            print(f"🧹 {removed_count} anciens logs supprimés (plus de {days_to_keep} jours)")
        else:
            print(f"✅ Aucun log ancien à supprimer (seuil: {days_to_keep} jours)")
            
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage des logs: {e}")

def validate_encodings(verbose=True):
    """
    Valide le fichier d'encodages et affiche des statistiques
    
    Args:
        verbose: Afficher les détails
    
    Returns:
        dict: Statistiques de validation
    """
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
        
        # Calculer les statistiques
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

def export_attendance_report(start_date=None, end_date=None, format='csv'):
    """
    Exporte un rapport de présence
    
    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        format: Format d'export ('csv', 'json', 'excel')
    
    Returns:
        str: Chemin du fichier exporté
    """
    if not os.path.exists(LOG_FILE):
        print("❌ Aucun fichier de logs trouvé.")
        return None
    
    try:
        df = pd.read_csv(LOG_FILE)
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df = df.dropna(subset=['DateTime'])
        
        # Filtrer par période
        if start_date:
            start_dt = pd.to_datetime(start_date)
            df = df[df['DateTime'] >= start_dt]
        
        if end_date:
            end_dt = pd.to_datetime(end_date) + timedelta(days=1)  # Inclure la journée complète
            df = df[df['DateTime'] < end_dt]
        
        if df.empty:
            print("❌ Aucune donnée dans la période spécifiée.")
            return None
        
        # Générer le nom de fichier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        period_str = ""
        if start_date or end_date:
            period_str = f"_{start_date or 'debut'}_to_{end_date or 'fin'}"
        
        filename = f"rapport_presence{period_str}_{timestamp}"
        
        # Exporter selon le format
        if format.lower() == 'csv':
            filepath = f"{filename}.csv"
            df.to_csv(filepath, index=False)
        elif format.lower() == 'json':
            filepath = f"{filename}.json"
            df.to_json(filepath, orient='records', date_format='iso', indent=2)
        elif format.lower() == 'excel':
            filepath = f"{filename}.xlsx"
            df.to_excel(filepath, index=False)
        else:
            print("❌ Format non supporté. Utilisez 'csv', 'json' ou 'excel'.")
            return None
        
        print(f"📊 Rapport exporté: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Erreur lors de l'export: {e}")
        return None

def draw_face_box(frame, face_info, draw_confidence=True):
    """
    Dessine un rectangle autour d'un visage avec le nom
    
    Args:
        frame: Image OpenCV
        face_info: Dictionnaire avec les infos du visage
        draw_confidence: Afficher le score de confiance
    
    Returns:
        Image modifiée
    """
    top, right, bottom, left = face_info['location']
    name = face_info['name']
    confidence = face_info.get('confidence', 0)
    
    # Couleur selon la reconnaissance
    if face_info.get('is_known', False):
        color = (0, 255, 0)  # Vert pour reconnu
        text_color = (255, 255, 255)
    else:
        color = (0, 0, 255)  # Rouge pour inconnu
        text_color = (255, 255, 255)
    
    # Dessiner le rectangle
    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
    
    # Préparer le texte
    if draw_confidence and face_info.get('is_known', False):
        text = f"{name} ({confidence:.2f})"
    else:
        text = name
    
    # Calculer la taille du texte
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.6
    thickness = 1
    
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Dessiner le fond du texte
    cv2.rectangle(frame, 
                  (left, bottom - text_height - 10), 
                  (left + text_width, bottom), 
                  color, cv2.FILLED)
    
    # Dessiner le texte
    cv2.putText(frame, text, (left, bottom - 5), font, font_scale, text_color, thickness)
    
    return frame

# Test des fonctions si le script est exécuté directement
if __name__ == "__main__":
    print("🔍 Test des fonctions utilitaires...")
    print("=" * 50)
    
    # Tester la configuration
    config = load_config()
    print(f"⚙️ Configuration chargée: {config}")
    
    # Valider les encodages
    print("\n📊 Validation des encodages:")
    stats = validate_encodings(verbose=True)
    
    if stats['valid']:
        print(f"\n✅ Validation réussie!")
        
        # Afficher le résumé d'aujourd'hui
        print(f"\n📈 Résumé de présence d'aujourd'hui:")
        summary = get_attendance_summary()
        if not summary.empty:
            print(summary)
        else:
            print("Aucune donnée de présence aujourd'hui.")
        
        # Statistiques hebdomadaires
        print(f"\n📅 Statistiques de la semaine:")
        weekly = get_weekly_stats()
        if not weekly.empty:
            print(weekly)
        else:
            print("Aucune donnée cette semaine.")
            
    else:
        print(f"\n❌ Validation échouée!")
        print("💡 Exécutez encode_faces.py pour créer les encodages")
    
    print("\n" + "=" * 50)  