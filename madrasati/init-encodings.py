#!/usr/bin/env python3
"""
Initialize the shared encodings volume with the existing encodings.pkl file
"""
import os
import shutil
import sys

def initialize_encodings():
    """Copy the existing encodings.pkl to the shared volume location"""
    
    # Source file path (in the container)
    source_file = "/app/encodings.pkl"
    
    # Destination directory and file path (shared volume)
    dest_dir = "/app/encodings"
    dest_file = "/app/encodings/encodings.pkl"
    
    try:
        # Create the encodings directory if it doesn't exist
        os.makedirs(dest_dir, exist_ok=True)
        print(f"✅ Created directory: {dest_dir}")
        
        # Check if source file exists
        if os.path.exists(source_file):
            # Copy the encodings file to the shared volume
            shutil.copy2(source_file, dest_file)
            print(f"✅ Copied {source_file} to {dest_file}")
            
            # Verify the copy was successful
            if os.path.exists(dest_file):
                file_size = os.path.getsize(dest_file)
                print(f"✅ Shared encodings file initialized successfully ({file_size} bytes)")
                return True
            else:
                print(f"❌ Failed to create {dest_file}")
                return False
        else:
            print(f"⚠️  Source file {source_file} not found")
            # Create an empty encodings file structure
            import pickle
            empty_data = {"encodings": [], "names": []}
            with open(dest_file, 'wb') as f:
                pickle.dump(empty_data, f)
            print(f"✅ Created empty encodings file at {dest_file}")
            return True
            
    except Exception as e:
        print(f"❌ Error initializing encodings: {str(e)}")
        return False

if __name__ == "__main__":
    success = initialize_encodings()
    sys.exit(0 if success else 1)
