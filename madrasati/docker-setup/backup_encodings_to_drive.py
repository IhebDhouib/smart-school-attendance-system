#!/usr/bin/env python3
"""
Google Drive Backup for Face Encodings

This script automatically backs up the face encodings file to Google Drive
whenever it's updated. Can be run manually or scheduled as a cron job.

Usage:
    python backup_encodings_to_drive.py

Requirements:
    pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
"""

import os
import sys
import json
import pickle
import datetime
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class FaceEncodingsBackup:
    def __init__(self, service_account_path=None, service_account_json=None):
        self.service_account_path = service_account_path
        self.service_account_json = service_account_json
        self.drive_service = None
        self.parent_folder_id = None
        
    def initialize_drive_service(self):
        """Initialize Google Drive API service"""
        try:
            # Load credentials
            if self.service_account_json:
                # From JSON string (environment variable)
                credentials_info = json.loads(self.service_account_json)
                credentials = Credentials.from_service_account_info(
                    credentials_info, 
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
            elif self.service_account_path and os.path.exists(self.service_account_path):
                # From file
                credentials = Credentials.from_service_account_file(
                    self.service_account_path,
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
            else:
                raise ValueError("No valid service account credentials provided")
            
            # Build the service
            self.drive_service = build('drive', 'v3', credentials=credentials)
            
            # Create or find the main backup folder
            self.parent_folder_id = self._create_or_find_folder('Madrasati_Encodings_Backup')
            
            print(f"✅ Google Drive service initialized successfully")
            print(f"   Parent folder ID: {self.parent_folder_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Google Drive service: {e}")
            return False
    
    def _create_or_find_folder(self, folder_name, parent_id=None):
        """Create or find a folder in Google Drive"""
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                print(f"Found existing folder: {folder_name}")
                return folders[0]['id']
            
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id] if parent_id else None
            }
            
            if not parent_id:
                del folder_metadata['parents']
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            print(f"Created new folder: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except HttpError as error:
            print(f"Error creating/finding folder {folder_name}: {error}")
            raise
    
    def backup_encodings_file(self, encodings_file_path):
        """Backup the face encodings file to Google Drive"""
        if not self.drive_service:
            print("Google Drive service not initialized")
            return False
        
        if not os.path.exists(encodings_file_path):
            print(f"Encodings file not found: {encodings_file_path}")
            return False
        
        try:
            # Read encodings file to get statistics
            stats = self._get_encodings_statistics(encodings_file_path)
            
            # Create filename with timestamp and stats
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(os.path.basename(encodings_file_path))[0]
            filename = f"{base_name}_backup_{timestamp}_{stats['total_encodings']}enc_{stats['unique_students']}students.pkl"
            
            # Upload file
            file_metadata = {
                'name': filename,
                'parents': [self.parent_folder_id],
                'description': f"Face encodings backup - {stats['total_encodings']} encodings for {stats['unique_students']} students"
            }
            
            media = MediaFileUpload(
                encodings_file_path,
                mimetype='application/octet-stream',
                resumable=True
            )
            
            print(f"📤 Uploading {filename}...")
            print(f"   File size: {os.path.getsize(encodings_file_path)} bytes")
            print(f"   Encodings: {stats['total_encodings']}")
            print(f"   Students: {stats['unique_students']}")
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, size'
            ).execute()
            
            print(f"✅ Backup completed successfully!")
            print(f"   File ID: {file.get('id')}")
            print(f"   File Name: {file.get('name')}")
            print(f"   View Link: {file.get('webViewLink')}")
            print(f"   Upload Size: {file.get('size')} bytes")
            
            return {
                'success': True,
                'file_id': file.get('id'),
                'filename': file.get('name'),
                'web_view_link': file.get('webViewLink'),
                'stats': stats
            }
            
        except HttpError as error:
            print(f"❌ Upload failed: {error}")
            return {'success': False, 'error': str(error)}
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_encodings_statistics(self, encodings_file_path):
        """Get statistics from the encodings file"""
        try:
            with open(encodings_file_path, 'rb') as f:
                data = pickle.load(f)
            
            embeddings = data.get('embeddings', [])
            names = data.get('names', [])
            
            return {
                'total_encodings': len(embeddings),
                'unique_students': len(set(names)) if names else 0,
                'students': list(set(names)) if names else []
            }
        except Exception as e:
            print(f"⚠️  Could not read encodings statistics: {e}")
            return {
                'total_encodings': 0,
                'unique_students': 0,
                'students': []
            }
    
    def list_backups(self):
        """List all backup files in Google Drive"""
        if not self.drive_service:
            print("Google Drive service not initialized")
            return []
        
        try:
            query = f"'{self.parent_folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name, createdTime, modifiedTime, size)',
                orderBy='modifiedTime desc'
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                print("No backup files found")
                return []
            
            print(f"Found {len(files)} backup files:")
            for i, file in enumerate(files[:10]):  # Show first 10
                created = datetime.datetime.fromisoformat(file['createdTime'].replace('Z', '+00:00'))
                size_mb = int(file.get('size', 0)) / (1024 * 1024)
                print(f"  {i+1}. {file['name']}")
                print(f"     Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"     Size: {size_mb:.2f} MB")
                print()
            
            return files
            
        except HttpError as error:
            print(f"Error listing backups: {error}")
            return []

def main():
    """Main function"""
    print("🚀 Face Encodings Google Drive Backup")
    print("=" * 50)
    
    # Configuration
    encodings_file = os.getenv('ENCODINGS_FILE_ARCFACE', 'encodings_arcface.pkl')
    service_account_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH')
    service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')
    
    # Make encodings file path absolute if it exists
    if not os.path.isabs(encodings_file):
        # Try different common locations
        possible_paths = [
            encodings_file,  # Current directory
            os.path.join('..', 'face', encodings_file),  # Face service directory
            os.path.join('face', encodings_file),  # Face directory
            os.path.join('/app/madrasati/face', encodings_file),  # Docker path
        ]
        
        encodings_file = None
        for path in possible_paths:
            if os.path.exists(path):
                encodings_file = os.path.abspath(path)
                break
        
        if not encodings_file:
            print(f"❌ Encodings file not found in any of these locations:")
            for path in possible_paths:
                print(f"   - {os.path.abspath(path)}")
            sys.exit(1)
    
    print(f"📁 Encodings file: {encodings_file}")
    
    # Check if backup is enabled
    if os.getenv('ENABLE_GOOGLE_DRIVE_BACKUP', 'false').lower() != 'true':
        print("⚠️  Google Drive backup is disabled (ENABLE_GOOGLE_DRIVE_BACKUP=false)")
        print("💡 Set ENABLE_GOOGLE_DRIVE_BACKUP=true to enable")
        sys.exit(0)
    
    # Initialize backup service
    backup_service = FaceEncodingsBackup(
        service_account_path=service_account_path,
        service_account_json=service_account_json
    )
    
    if not backup_service.initialize_drive_service():
        print("❌ Failed to initialize Google Drive service")
        sys.exit(1)
    
    # Perform backup
    result = backup_service.backup_encodings_file(encodings_file)
    
    if result['success']:
        print(f"\n🎉 Backup completed successfully!")
        print(f"📊 Statistics: {result['stats']['total_encodings']} encodings for {result['stats']['unique_students']} students")
    else:
        print(f"\n❌ Backup failed: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()