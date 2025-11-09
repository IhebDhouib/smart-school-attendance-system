#!/usr/bin/env python3
"""
Clean up duplicate encodings from encodings_arcface.pkl
Removes duplicate encodings for students who were encoded multiple times
"""
import os
import pickle
import numpy as np
from collections import Counter
from datetime import datetime

# Configuration
ENCODINGS_FILE = os.getenv("ENCODINGS_FILE_ARCFACE", "/app/madrasati/face/encodings_arcface.pkl")

def load_encodings():
    """Load current encodings from file"""
    try:
        if not os.path.exists(ENCODINGS_FILE):
            print(f"❌ Encodings file not found: {ENCODINGS_FILE}")
            return None, None
            
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            embeddings = data.get("embeddings", [])
            names = data.get("names", [])
            
        print(f"📁 Loaded {len(embeddings)} encodings for {len(set(names))} unique students")
        return embeddings, names
    except Exception as e:
        print(f"❌ Error loading encodings: {e}")
        return None, None

def cleanup_duplicates(embeddings, names):
    """
    Remove duplicate encodings, keeping only unique ones per student
    Strategy: For each student, keep only distinct embeddings (remove exact duplicates)
    """
    print("\n🔍 Analyzing duplicates...")
    
    # Count encodings per student
    name_counts = Counter(names)
    print("\n📊 Current encoding distribution:")
    for name, count in sorted(name_counts.items()):
        print(f"   - {name}: {count} encoding(s)")
    
    # Group embeddings by student
    student_embeddings = {}
    for i, name in enumerate(names):
        if name not in student_embeddings:
            student_embeddings[name] = []
        student_embeddings[name].append((i, embeddings[i]))
    
    # Remove exact duplicates while keeping unique encodings
    cleaned_embeddings = []
    cleaned_names = []
    removed_count = 0
    
    print("\n🧹 Removing duplicate encodings...")
    for name, emb_list in sorted(student_embeddings.items()):
        unique_embeddings = []
        seen_embeddings = []
        
        for idx, emb in emb_list:
            emb_array = np.asarray(emb, dtype=np.float32)
            
            # Check if this embedding is a duplicate
            is_duplicate = False
            for seen_emb in seen_embeddings:
                # Compare with very high threshold (0.999) to only remove exact duplicates
                similarity = np.dot(emb_array, seen_emb)
                if similarity > 0.999:  # Almost identical
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_embeddings.append(emb)
                seen_embeddings.append(emb_array)
            else:
                removed_count += 1
        
        # Add unique encodings to cleaned lists
        for emb in unique_embeddings:
            cleaned_embeddings.append(emb)
            cleaned_names.append(name)
        
        original_count = len(emb_list)
        unique_count = len(unique_embeddings)
        if original_count > unique_count:
            print(f"   - {name}: {original_count} → {unique_count} (removed {original_count - unique_count} duplicates)")
    
    return cleaned_embeddings, cleaned_names, removed_count

def save_cleaned_encodings(embeddings, names):
    """Save cleaned encodings to file"""
    try:
        # Backup original file
        backup_file = f"{ENCODINGS_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(ENCODINGS_FILE, "rb") as src, open(backup_file, "wb") as dst:
            dst.write(src.read())
        print(f"\n💾 Backup created: {backup_file}")
        
        # Save cleaned encodings
        data = {
            'embeddings': embeddings,
            'names': names,
            'model': 'arcface',
            'model_name': 'ArcFace (InsightFace)',
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_faces': len(embeddings),
            'unique_students': len(set(names)),
            'embedding_dimension': len(embeddings[0]) if embeddings else 0,
            'cleaned': True
        }
        
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(data, f)
            
        print(f"✅ Cleaned encodings saved to {ENCODINGS_FILE}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving cleaned encodings: {e}")
        return False

def main():
    """Main function"""
    print("🧹 Starting duplicate encoding cleanup...")
    print(f"📁 Encodings file: {ENCODINGS_FILE}")
    
    # Load current encodings
    embeddings, names = load_encodings()
    if embeddings is None or names is None:
        print("❌ Failed to load encodings. Aborting.")
        return False
    
    original_count = len(embeddings)
    original_unique = len(set(names))
    
    # Clean up duplicates
    cleaned_embeddings, cleaned_names, removed_count = cleanup_duplicates(embeddings, names)
    
    final_count = len(cleaned_embeddings)
    final_unique = len(set(cleaned_names))
    
    print(f"\n📊 Cleanup Results:")
    print(f"   Original: {original_count} encodings ({original_unique} unique students)")
    print(f"   Cleaned: {final_count} encodings ({final_unique} unique students)")
    print(f"   Removed: {removed_count} duplicate encodings")
    
    if removed_count == 0:
        print("\n✅ No duplicates found - encodings file is already clean!")
        return True
    
    # Save cleaned encodings
    if save_cleaned_encodings(cleaned_embeddings, cleaned_names):
        print(f"\n🎉 Successfully cleaned {removed_count} duplicate encodings!")
        print(f"🎯 Face recognition will now use {final_count} unique encodings")
        
        # Show final distribution
        name_counts = Counter(cleaned_names)
        print("\n📊 Final encoding distribution:")
        for name, count in sorted(name_counts.items()):
            print(f"   - {name}: {count} encoding(s)")
        
        return True
    else:
        print("\n❌ Failed to save cleaned encodings")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
