#!/usr/bin/env python3
"""
Sync face encodings with database - remove encodings for deleted students
"""
import os
import pickle
import requests
import sys
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")
# ✅ Utiliser encodings_arcface.pkl (InsightFace) au lieu de encodings.pkl
# Use environment variable or Docker container path
ENCODINGS_FILE = os.getenv("ENCODINGS_FILE_ARCFACE", "/app/face/encodings_arcface.pkl")

def fetch_active_students():
    """Fetch all active students from the database (only those with photos)"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/students", timeout=10)
        if response.status_code == 200:
            students = response.json()
            # Extract matricule only for students who have photos
            active_matricules = [
                str(student.get('matricule')) 
                for student in students 
                if student.get('matricule') and student.get('photos') and len(student.get('photos', [])) > 0
            ]
            total_students = len(students)
            students_with_photos = len(active_matricules)
            print(f"✅ Found {total_students} students in database")
            print(f"   📸 {students_with_photos} students have photos")
            print(f"   ⚪ {total_students - students_with_photos} students without photos (will be ignored)")
            return set(active_matricules)  # Use set for faster lookup
        else:
            print(f"❌ Error fetching students: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")
        return None

def load_current_encodings():
    """Load current encodings from file"""
    try:
        if not os.path.exists(ENCODINGS_FILE):
            print(f"❌ Encodings file not found: {ENCODINGS_FILE}")
            return None, None
            
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            # ✅ Utiliser 'embeddings' (clé InsightFace) au lieu de 'encodings'
            encodings = data.get("embeddings", [])
            names = data.get("names", [])
            
        print(f"📁 Loaded {len(encodings)} encodings for {len(set(names))} unique students")
        return encodings, names
    except Exception as e:
        print(f"❌ Error loading encodings: {e}")
        return None, None

def sync_encodings_with_database():
    """Remove encodings for students that no longer exist in the database"""
    
    print("🔄 Starting encoding synchronization with database...")
    
    # Get active students from database
    active_students = fetch_active_students()
    if active_students is None:
        print("❌ Could not fetch students from database. Aborting sync.")
        return False
    
    # Load current encodings
    encodings, names = load_current_encodings()
    if encodings is None or names is None:
        print("❌ Could not load current encodings. Aborting sync.")
        return False
    
    # Check which students in encodings are still active
    original_count = len(encodings)
    original_unique = len(set(names))
    
    # Filter encodings to keep only active students
    synced_encodings = []
    synced_names = []
    removed_students = set()
    
    for i, student_id in enumerate(names):
        if str(student_id) in active_students:
            synced_encodings.append(encodings[i])
            synced_names.append(names[i])
        else:
            removed_students.add(str(student_id))
    
    # Show synchronization results
    final_count = len(synced_encodings)
    final_unique = len(set(synced_names))
    removed_count = len(removed_students)
    
    print(f"\n📊 Synchronization Results:")
    print(f"   Original encodings: {original_count} ({original_unique} unique students)")
    print(f"   Active students with photos in DB: {len(active_students)}")
    print(f"   Synced encodings: {final_count} ({final_unique} unique students)")
    print(f"   Removed encodings: {original_count - final_count}")
    
    if removed_students:
        print(f"\n🗑️  Removed students (deleted or without photos):")
        for student_id in sorted(removed_students):
            print(f"      - {student_id}")
    
    # Save the synchronized encodings
    if final_count < original_count:
        try:
            # Backup original file
            backup_file = f"{ENCODINGS_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(ENCODINGS_FILE, "rb") as src, open(backup_file, "wb") as dst:
                dst.write(src.read())
            print(f"💾 Backup created: {backup_file}")
            
            # Save synchronized encodings
            # ✅ Utiliser 'embeddings' (clé InsightFace) pour cohérence
            synced_data = {
                "embeddings": synced_encodings,
                "names": synced_names
            }
            
            with open(ENCODINGS_FILE, "wb") as f:
                pickle.dump(synced_data, f)
                
            print(f"✅ Synchronized encodings saved to {ENCODINGS_FILE}")
            print(f"🎯 Face recognition will now only detect {final_unique} active students")
            return True
            
        except Exception as e:
            print(f"❌ Error saving synchronized encodings: {e}")
            return False
    else:
        print("✅ No synchronization needed - all encoded students are active in database")
        return True

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python sync_encodings_with_db.py")
        print("Removes face encodings for students that have been deleted from the database")
        return
    
    success = sync_encodings_with_database()
    if success:
        print("🎉 Encoding synchronization completed successfully!")
        sys.exit(0)
    else:
        print("❌ Encoding synchronization failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
