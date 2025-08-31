#!/usr/bin/env python3
"""
Student API Test Script
======================
This script tests the student creation API to help debug the 400 error.
"""

import requests
import json

def test_student_api():
    """Test adding a student via the API"""
    
    # API endpoint
    url = "http://localhost:3000/api/students"
    
    # Test data - using multipart form data like the frontend
    data = {
        'matricule': 'TEST001',
        'fullName': 'Test Student',
        'nomPere': 'Test Father',
        'dateNaissance': '2010-01-01',
        'classId': '68ab79410f48d3811144cf8b'
    }
    
    print("🔬 Testing Student API")
    print("=" * 30)
    print(f"URL: {url}")
    print(f"Data: {data}")
    print()
    
    try:
        # Test with multipart form data (like frontend)
        response = requests.post(url, data=data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 201:
            print("✅ Student created successfully!")
            print(f"Response Data: {response.json()}")
        else:
            print("❌ Error creating student")
            try:
                error_data = response.json()
                print(f"Error Details: {error_data}")
            except:
                print(f"Raw Error: {response.text}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_student_api()
