#!/usr/bin/env python3
"""
Simple Flask API to serve unknown faces from the face detection container
"""
import os
import json
import glob
from datetime import datetime
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for Angular frontend

UNKNOWN_FACES_DIR = "unknown_faces"

@app.route('/api/unknown-faces', methods=['GET'])
def get_unknown_faces():
    """Get list of all unknown faces"""
    try:
        # Ensure directory exists
        if not os.path.exists(UNKNOWN_FACES_DIR):
            os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)
            return jsonify({
                'faces': [],
                'total': 0,
                'message': 'Unknown faces directory created'
            })
        
        # Get all image files
        image_extensions = ['*.jpg', '*.jpeg', '*.png']
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(UNKNOWN_FACES_DIR, ext)))
        
        faces = []
        for file_path in image_files:
            filename = os.path.basename(file_path)
            stats = os.stat(file_path)
            
            # Parse filename to extract info (format: inconnu_XXXXXXXX_YYYYMMDD_HHMMSS.jpg)
            parts = filename.replace('.jpg', '').replace('.jpeg', '').replace('.png', '').split('_')
            unknown_id = 'unknown'
            timestamp = datetime.fromtimestamp(stats.st_mtime)
            
            if len(parts) >= 3:
                unknown_id = f"{parts[0]}_{parts[1]}"
                if len(parts) >= 4:
                    date_str = parts[2]
                    time_str = parts[3]
                    
                    if len(date_str) == 8 and len(time_str) == 6:
                        try:
                            year = date_str[:4]
                            month = date_str[4:6]
                            day = date_str[6:8]
                            hour = time_str[:2]
                            minute = time_str[2:4]
                            second = time_str[4:6]
                            
                            timestamp = datetime(int(year), int(month), int(day), 
                                               int(hour), int(minute), int(second))
                        except ValueError:
                            pass  # Use file modification time
            
            faces.append({
                'id': unknown_id,
                'filename': filename,
                'timestamp': timestamp.isoformat(),
                'size': stats.st_size,
                'path': f'/api/unknown-faces/image/{filename}'
            })
        
        # Sort by timestamp (newest first)
        faces.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'faces': faces,
            'total': len(faces),
            'directory': UNKNOWN_FACES_DIR
        })
        
    except Exception as e:
        print(f"Error getting unknown faces: {e}")
        return jsonify({
            'message': 'Error getting unknown faces',
            'error': str(e)
        }), 500

@app.route('/api/unknown-faces/image/<filename>', methods=['GET'])
def get_unknown_face_image(filename):
    """Serve an unknown face image"""
    try:
        # Security check
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'message': 'Invalid filename'}), 400
        
        file_path = os.path.join(UNKNOWN_FACES_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'message': 'Image not found'}), 404
        
        return send_file(file_path, mimetype='image/jpeg')
        
    except Exception as e:
        print(f"Error serving image {filename}: {e}")
        return jsonify({
            'message': 'Error serving image',
            'error': str(e)
        }), 500

@app.route('/api/unknown-faces/<filename>', methods=['DELETE'])
def delete_unknown_face(filename):
    """Delete an unknown face image"""
    try:
        # Security check
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'message': 'Invalid filename'}), 400
        
        file_path = os.path.join(UNKNOWN_FACES_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'message': 'Image not found'}), 404
        
        os.remove(file_path)
        
        return jsonify({
            'message': 'Unknown face deleted successfully',
            'filename': filename
        })
        
    except Exception as e:
        print(f"Error deleting image {filename}: {e}")
        return jsonify({
            'message': 'Error deleting unknown face',
            'error': str(e)
        }), 500

@app.route('/api/unknown-faces/stats', methods=['GET'])
def get_unknown_faces_stats():
    """Get statistics about unknown faces"""
    try:
        if not os.path.exists(UNKNOWN_FACES_DIR):
            return jsonify({
                'total': 0,
                'today': 0,
                'this_week': 0,
                'directory_exists': False
            })
        
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            image_files.extend(glob.glob(os.path.join(UNKNOWN_FACES_DIR, ext)))
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start.replace(day=today_start.day - today_start.weekday())
        
        total = len(image_files)
        today = 0
        this_week = 0
        
        for file_path in image_files:
            stats = os.stat(file_path)
            file_time = datetime.fromtimestamp(stats.st_mtime)
            
            if file_time >= today_start:
                today += 1
            if file_time >= week_start:
                this_week += 1
        
        return jsonify({
            'total': total,
            'today': today,
            'this_week': this_week,
            'directory_exists': True
        })
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({
            'message': 'Error getting statistics',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Unknown Faces API server...")
    app.run(host='0.0.0.0', port=5001, debug=True)
