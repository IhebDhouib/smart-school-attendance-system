import face_recognition
import numpy as np
import pickle
import os
import pandas as pd
from datetime import datetime, timedelta
import cv2
import json
from collections import Counter
import csv
# Configuration
ENCODINGS_PATH = "encodings.pkl"
LOG_FILE = "logs/logs.csv"
CONFIG_FILE = "config.json"

# Configuration par défaut
DEFAULT_CONFIG = {
    "tolerance": 0.5,  # Aligné avec app.py
    "model": "hog",
    "scale_factor": 0.5,  # Aligné avec app.py
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
            return {**DEFAULT_CONFIG, **config}
        else:
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
        print("💡 Exécutez encode_faces_copy.py pour créer les encodages")
        return [], []
    except Exception as e:
        print(f"❌ Erreur lors du chargement des encodages: {e}")
        return [], []

def recognize_faces_in_frame(frame, known_encodings, known_names, config=None):
    """Reconnaît tous les visages dans une frame"""
    if config is None:
        config = load_config()
    
    scale_factor = config.get("scale_factor", 0.5)
    small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    model = config.get("model", "hog")
    face_locations = face_recognition.face_locations(rgb_frame, model=model)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    recognized_faces = []
    tolerance = config.get("tolerance", 0.5)
    
    for (face_encoding, face_location) in zip(face_encodings, face_locations):
        name = "Inconnu"
        confidence = 0.0
        distance = 1.0
        
        if known_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                distance = face_distances[best_match_index]
                
                if matches[best_match_index] and distance < tolerance:
                    name = known_names[best_match_index]
                    confidence = 1 - distance
        
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
    """Reconnaît un seul visage et retourne le nom avec la meilleure confiance"""
    faces = recognize_faces_in_frame(frame, known_encodings, known_names, config)
    
    if faces:
        known_faces = [f for f in faces if f['is_known']]
        if known_faces:
            best_face = max(known_faces, key=lambda x: x['confidence'])
            return best_face['name']
    
    return "Inconnu"

def log_event(name, action):
    """Enregistre un événement dans le fichier CSV avec le format [Nom, Action, DateTime]"""
    now = datetime.now()
    try:
        file_exists = os.path.exists(LOG_FILE)
        expected_headers = ["Nom", "Action", "DateTime"]
        if file_exists:
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers and headers != expected_headers:
                    print("⚠️ Structure CSV incohérente. Réinitialisation du fichier.")
                    file_exists = False

        with open(LOG_FILE, mode="a" if file_exists else "w", newline="", encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(expected_headers)
            writer.writerow([name, action, now.strftime("%Y-%m-%d %H:%M:%S")])
        print(f"📝 Log: {name} - {action}")
        return True
    except Exception as e:
        print(f"❌ Erreur log: {e}")
        return False

def get_attendance_summary(date=None, person_name=None):
    """Obtient un résumé de la présence"""
    if not os.path.exists(LOG_FILE):
        print("❌ Aucun fichier de logs trouvé.")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(LOG_FILE, encoding='utf-8')
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df = df.dropna(subset=['DateTime'])
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        day_logs = df[df['DateTime'].dt.strftime('%Y-%m-%d') == date].copy()
        
        if person_name:
            day_logs = day_logs[day_logs['Nom'] == person_name]
        
        if day_logs.empty:
            print(f"❌ Aucun log trouvé pour {person_name or 'toutes les personnes'} le {date}")
            return pd.DataFrame()
        
        summary = day_logs.groupby('Nom').agg({
            'Action': 'count',
            'DateTime': ['min', 'max']
        }).round(2)
        
        summary.columns = ['Nombre_détections', 'Premier_datetime', 'Dernier_datetime']
        summary['Durée_présence'] = summary.apply(
            lambda row: str(row['Dernier_datetime'] - row['Premier_datetime']).split('.')[0], 
            axis=1
        )
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
        df = pd.read_csv(LOG_FILE, encoding='utf-8')
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df = df.dropna(subset=['DateTime'])
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        week_logs = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
        
        if week_logs.empty:
            return pd.DataFrame()
        
        week_logs['Date'] = week_logs['DateTime'].dt.strftime('%Y-%m-%d')
        daily_stats = week_logs.groupby(['Date', 'Nom']).size().unstack(fill_value=0)
        
        return daily_stats
        
    except Exception as e:
        print(f"❌ Erreur calcul stats hebdomadaires: {e}")
        return pd.DataFrame()

def clean_old_logs(days_to_keep=30):
    """Nettoie les anciens logs"""
    if not os.path.exists(LOG_FILE):
        print("📁 Aucun fichier de logs à nettoyer.")
        return
    
    try:
        df = pd.read_csv(LOG_FILE, encoding='utf-8')
        if df.empty:
            print("📁 Fichier de logs vide.")
            return
        
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df = df.dropna(subset=['DateTime'])
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        recent_logs = df[df['DateTime'] >= cutoff_date]
        removed_count = len(df) - len(recent_logs)
        
        if removed_count > 0:
            recent_logs.to_csv(LOG_FILE, index=False)
            print(f"🧹 {removed_count} anciens logs supprimés (plus de {days_to_keep} jours)")
        else:
            print(f"✅ Aucun log ancien à supprimer (seuil: {days_to_keep} jours)")
            
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage des logs: {e}")

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

def export_attendance_report(start_date=None, end_date=None, format='csv'):
    """Exporte un rapport de présence"""
    if not os.path.exists(LOG_FILE):
        print("❌ Aucun fichier de logs trouvé.")
        return None
    
    try:
        df = pd.read_csv(LOG_FILE, encoding='utf-8')
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df = df.dropna(subset=['DateTime'])
        
        if start_date:
            start_dt = pd.to_datetime(start_date)
            df = df[df['DateTime'] >= start_dt]
        
        if end_date:
            end_dt = pd.to_datetime(end_date) + timedelta(days=1)
            df = df[df['DateTime'] < end_dt]
        
        if df.empty:
            print("❌ Aucune donnée dans la période spécifiée.")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        period_str = f"_{start_date or 'debut'}_to_{end_date or 'fin'}"
        filename = f"rapport_presence{period_str}_{timestamp}"
        
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
    """Dessine un rectangle autour d'un visage avec le nom"""
    top, right, bottom, left = face_info['location']
    name = face_info['name']
    confidence = face_info.get('confidence', 0)
    
    color = (0, 255, 0) if face_info.get('is_known', False) else (0, 0, 255)
    text_color = (255, 255, 255)
    
    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
    
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.6
    thickness = 1
    
    text = f"{name} ({confidence:.2f})" if draw_confidence and face_info.get('is_known', False) else name
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    cv2.rectangle(frame, (left, bottom - text_height - 10), (left + text_width, bottom), color, cv2.FILLED)
    cv2.putText(frame, text, (left, bottom - 5), font, font_scale, text_color, thickness)
    
    return frame

if __name__ == "__main__":
    print("🔍 Test des fonctions utilitaires...")
    print("=" * 50)
    
    config = load_config()
    print(f"⚙️ Configuration chargée: {config}")
    
    print("\n📊 Validation des encodages:")
    stats = validate_encodings(verbose=True)
    
    if stats['valid']:
        print(f"\n✅ Validation réussie!")
        print(f"\n📈 Résumé de présence d'aujourd'hui:")
        summary = get_attendance_summary()
        if not summary.empty:
            print(summary)
        else:
            print("Aucune donnée de présence aujourd'hui.")
        
        print(f"\n📅 Statistiques de la semaine:")
        weekly = get_weekly_stats()
        if not weekly.empty:
            print(weekly)
        else:
            print("Aucune donnée cette semaine.")
            
    else:
        print(f"\n❌ Validation échouée!")
        print("💡 Exécutez encode_faces_copy.py pour créer les encodages")
    
    print("\n" + "=" * 50)