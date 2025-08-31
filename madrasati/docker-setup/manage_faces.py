#!/usr/bin/env python3
"""
Face Recognition Data Management Script
======================================

This script helps manage face recognition data for the Madrasati system.
It can clear all face encodings or show current data.

Usage:
    python manage_faces.py [action]
    
Actions:
    - show: Display current face recognition data
    - clear: Remove all face encodings (start fresh)
    - backup: Create a backup of current encodings
"""

import os
import pickle
import sys
import shutil
from datetime import datetime

class FaceDataManager:
    def __init__(self):
        self.encodings_path = "/app/encodings/encodings.pkl"
        self.backup_dir = "/app/encodings/backups"
        
    def show_current_data(self):
        """Display current face recognition data"""
        try:
            if not os.path.exists(self.encodings_path):
                print("❌ No encodings file found")
                return
                
            with open(self.encodings_path, 'rb') as f:
                data = pickle.load(f)
            
            names = data.get('names', [])
            encodings = data.get('encodings', [])
            
            print(f"📊 Current Face Recognition Data:")
            print(f"   Total encodings: {len(encodings)}")
            print(f"   Total names: {len(names)}")
            
            if names:
                # Count unique students
                unique_students = {}
                for name in names:
                    unique_students[name] = unique_students.get(name, 0) + 1
                
                print(f"\n👥 Students in database:")
                for student_id, count in unique_students.items():
                    print(f"   - {student_id}: {count} face encodings")
            else:
                print("   No students registered")
                
        except Exception as e:
            print(f"❌ Error reading encodings: {e}")
    
    def create_backup(self):
        """Create a backup of current encodings"""
        try:
            if not os.path.exists(self.encodings_path):
                print("❌ No encodings file found to backup")
                return False
                
            os.makedirs(self.backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.backup_dir}/encodings_backup_{timestamp}.pkl"
            
            shutil.copy2(self.encodings_path, backup_path)
            print(f"✅ Backup created: {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            return False
    
    def clear_all_data(self):
        """Clear all face recognition data"""
        try:
            # Create empty encodings structure
            empty_data = {
                "encodings": [],
                "names": []
            }
            
            with open(self.encodings_path, 'wb') as f:
                pickle.dump(empty_data, f)
            
            print("✅ All face recognition data cleared")
            print("   The system is now ready for new student registrations")
            return True
            
        except Exception as e:
            print(f"❌ Error clearing data: {e}")
            return False
    
    def run(self, action=None):
        """Main execution function"""
        if not action:
            action = "show"
        
        print("🎯 MADRASATI FACE DATA MANAGER")
        print("=" * 40)
        
        if action == "show":
            self.show_current_data()
        elif action == "clear":
            print("⚠️  WARNING: This will remove ALL face recognition data!")
            print("   All registered students will need to re-register their faces.")
            
            # Show current data first
            self.show_current_data()
            
            confirm = input("\nAre you sure you want to clear all data? (type 'YES' to confirm): ")
            if confirm == "YES":
                # Create backup first
                print("\n📦 Creating backup before clearing...")
                if self.create_backup():
                    print("\n🗑️  Clearing all face data...")
                    if self.clear_all_data():
                        print("\n✅ Operation completed successfully!")
                        print("   Face detection system reset to initial state.")
                    else:
                        print("\n❌ Failed to clear data")
                else:
                    print("\n❌ Failed to create backup. Operation cancelled.")
            else:
                print("Operation cancelled.")
        elif action == "backup":
            self.create_backup()
        else:
            print(f"❌ Unknown action: {action}")
            print("Available actions: show, clear, backup")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "show"
    manager = FaceDataManager()
    manager.run(action)
