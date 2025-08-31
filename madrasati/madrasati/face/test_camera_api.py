#!/usr/bin/env python3
"""
Test script pour vérifier l'intégration de l'API des caméras
"""

import requests
import json

BACKEND_URL = "http://localhost:3000"

def test_camera_api():
    """Test de l'API des caméras"""
    try:
        print("🔄 Test de connexion à l'API des caméras...")
        response = requests.get(f"{BACKEND_URL}/api/cameras", timeout=10)
        
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            cameras = response.json()
            print(f"✅ Récupéré {len(cameras)} caméra(s)")
            
            for i, camera in enumerate(cameras):
                print(f"\n📹 Caméra {i+1}:")
                print(f"  - Nom: {camera.get('name', 'N/A')}")
                print(f"  - IP: {camera.get('ip', 'N/A')}")
                print(f"  - Port: {camera.get('port', 'N/A')}")
                print(f"  - Classe: {camera.get('classroom', 'N/A')}")
                print(f"  - Status: {camera.get('status', 'N/A')}")
                
                # Test de construction d'URL
                username = camera.get('username', '')
                password = camera.get('password', '')
                ip = camera.get('ip', '')
                port = camera.get('port', 8080)
                
                if username and password:
                    camera_url = f"http://{username}:{password}@{ip}:{port}/video"
                else:
                    camera_url = f"http://{ip}:{port}/video"
                    
                print(f"  - URL construite: {camera_url}")
                
                # Classifier les caméras
                camera_name_lower = camera.get('name', '').lower()
                if any(keyword in camera_name_lower for keyword in ['entry', 'entrée', 'entree', 'entrada', 'input']):
                    camera_type = "entrée"
                elif any(keyword in camera_name_lower for keyword in ['exit', 'sortie', 'salida', 'output']):
                    camera_type = "sortie"
                else:
                    camera_type = "entrée (par défaut)"
                    
                print(f"  - Type détecté: {camera_type}")
            
            return cameras
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        return []

if __name__ == "__main__":
    test_camera_api()
