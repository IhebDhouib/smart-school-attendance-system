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

def save_config(config):
    """Sauvegarde la configuration dans le fichier JSON"""

def load_encodings():
    """Charge les encodages depuis le fichier pickle"""

        

def get_weekly_stats():
    """Obtient les statistiques de la semaine"""

def clean_old_logs(days_to_keep=30):
    """Nettoie les anciens logs"""

def validate_encodings(verbose=True):
    """Valide le fichier d'encodages et affiche des statistiques"""

def export_attendance_report(start_date=None, end_date=None, format='csv'):
    """Exporte un rapport de présence"""

def draw_face_box(frame, face_info, draw_confidence=True):
    """Dessine un rectangle autour d'un visage avec le nom"""

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