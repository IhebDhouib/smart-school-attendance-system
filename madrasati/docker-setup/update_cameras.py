#!/usr/bin/env python3
"""
Camera IP Configuration Update Script for Madrasati
===================================================

This script provides an easy way to update camera IP addresses in one place.
Run this script whenever you need to change camera IPs.

Usage:
    python update_cameras.py

The script will:
1. Show current camera configurations
2. Allow you to update IP addresses
3. Restart the face-detection container automatically
4. Show the new configuration
"""

import os
import subprocess
import sys
import re

class CameraUpdater:
    def __init__(self):
        self.env_file = ".env"
        self.docker_compose_path = "."
        
    def read_env_file(self):
        """Read the current .env file and extract camera settings"""
        if not os.path.exists(self.env_file):
            print(f"❌ Error: {self.env_file} file not found!")
            return None
            
        cameras = {}
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if 'CAMERA' in key:
                            cameras[key] = value
        return cameras
    
    def display_current_config(self):
        """Display current camera configuration"""
        cameras = self.read_env_file()
        if not cameras:
            return False
            
        print("\n" + "="*60)
        print("🎥 CURRENT CAMERA CONFIGURATION")
        print("="*60)
        
        entry_cameras = {k: v for k, v in cameras.items() if 'ENTRY' in k}
        exit_cameras = {k: v for k, v in cameras.items() if 'EXIT' in k}
        
        print("\n📥 ENTRY CAMERAS (Students entering):")
        for key, value in entry_cameras.items():
            print(f"   {key}: {value}")
        
        print("\n📤 EXIT CAMERAS (Students leaving):")
        for key, value in exit_cameras.items():
            print(f"   {key}: {value}")
        
        print("\n" + "="*60)
        return True
    
    def update_camera_ip(self, camera_key, new_ip):
        """Update a specific camera IP in the .env file"""
        with open(self.env_file, 'r') as f:
            content = f.read()
        
        # Pattern to match the camera line
        pattern = f'^{camera_key}=.*$'
        replacement = f'{camera_key}={new_ip}'
        
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        with open(self.env_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated {camera_key} to {new_ip}")
    
    def interactive_update(self):
        """Interactive camera IP update"""
        print("\n🔧 CAMERA IP UPDATE WIZARD")
        print("-" * 40)
        
        # Show current config
        if not self.display_current_config():
            return False
        
        print("\nWhat would you like to update?")
        print("1. Entry Camera 1 (Main entrance)")
        print("2. Exit Camera 1 (Main exit)")
        print("3. Both cameras")
        print("4. Custom update")
        print("0. Exit without changes")
        
        choice = input("\nEnter your choice (0-4): ").strip()
        
        if choice == '0':
            print("No changes made.")
            return False
        elif choice == '1':
            new_ip = input("Enter new IP for Entry Camera 1 (format: http://IP:PORT/video): ").strip()
            if self.validate_ip_format(new_ip):
                self.update_camera_ip('ENTRY_CAMERA_1', new_ip)
                return True
        elif choice == '2':
            new_ip = input("Enter new IP for Exit Camera 1 (format: http://IP:PORT/video): ").strip()
            if self.validate_ip_format(new_ip):
                self.update_camera_ip('EXIT_CAMERA_1', new_ip)
                return True
        elif choice == '3':
            entry_ip = input("Enter new IP for Entry Camera 1: ").strip()
            exit_ip = input("Enter new IP for Exit Camera 1: ").strip()
            if self.validate_ip_format(entry_ip) and self.validate_ip_format(exit_ip):
                self.update_camera_ip('ENTRY_CAMERA_1', entry_ip)
                self.update_camera_ip('EXIT_CAMERA_1', exit_ip)
                return True
        elif choice == '4':
            print("\nAvailable camera variables:")
            cameras = self.read_env_file()
            for i, key in enumerate(cameras.keys(), 1):
                print(f"{i}. {key}")
            
            var_choice = input("Enter the number of the variable to update: ").strip()
            try:
                var_index = int(var_choice) - 1
                var_name = list(cameras.keys())[var_index]
                new_value = input(f"Enter new value for {var_name}: ").strip()
                self.update_camera_ip(var_name, new_value)
                return True
            except (ValueError, IndexError):
                print("❌ Invalid selection")
                return False
        
        return False
    
    def validate_ip_format(self, ip_string):
        """Basic validation of IP format"""
        if not ip_string:
            print("❌ IP cannot be empty")
            return False
        
        # Allow numeric values for USB cameras
        if ip_string.isdigit():
            return True
        
        # Check for http format
        if not ip_string.startswith('http://'):
            print("❌ IP cameras should start with 'http://'")
            return False
        
        return True
    
    def restart_face_detection(self):
        """Restart the face-detection container"""
        print("\n🔄 Restarting face-detection container...")
        try:
            result = subprocess.run(['docker-compose', 'restart', 'face-detection'], 
                                  capture_output=True, text=True, cwd=self.docker_compose_path)
            if result.returncode == 0:
                print("✅ Face-detection container restarted successfully")
                return True
            else:
                print(f"❌ Error restarting container: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error running docker-compose: {e}")
            return False
    
    def show_logs(self):
        """Show recent face-detection logs"""
        print("\n📋 Recent face-detection logs:")
        print("-" * 40)
        try:
            result = subprocess.run(['docker-compose', 'logs', '--tail=10', 'face-detection'], 
                                  capture_output=True, text=True, cwd=self.docker_compose_path)
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"❌ Error getting logs: {result.stderr}")
        except Exception as e:
            print(f"❌ Error running docker-compose: {e}")
    
    def run(self):
        """Main execution function"""
        print("🎥 MADRASATI CAMERA IP UPDATER")
        print("="*50)
        
        # Show current configuration
        if not self.display_current_config():
            return
        
        # Interactive update
        if self.interactive_update():
            print("\n✅ Configuration updated!")
            
            # Show new configuration
            self.display_current_config()
            
            # Ask if user wants to restart container
            restart = input("\nRestart face-detection container now? (y/N): ").strip().lower()
            if restart in ['y', 'yes']:
                if self.restart_face_detection():
                    # Show logs after restart
                    import time
                    time.sleep(2)  # Wait a moment for container to start
                    self.show_logs()
            else:
                print("⚠️  Remember to restart the container to apply changes:")
                print("   docker-compose restart face-detection")

if __name__ == "__main__":
    updater = CameraUpdater()
    updater.run()
