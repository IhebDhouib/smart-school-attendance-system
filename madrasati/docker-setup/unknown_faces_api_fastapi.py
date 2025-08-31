from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import glob
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UNKNOWN_FACES_DIR = "unknown_faces"

@app.get("/api/unknown-faces")
def get_unknown_faces():
    if not os.path.exists(UNKNOWN_FACES_DIR):
        os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)
        return {"faces": [], "total": 0, "message": "Unknown faces directory created"}
    image_extensions = ['*.jpg', '*.jpeg', '*.png']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(UNKNOWN_FACES_DIR, ext)))
    faces = []
    for file_path in image_files:
        filename = os.path.basename(file_path)
        stats = os.stat(file_path)
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
                        timestamp = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
                    except ValueError:
                        pass
        faces.append({
            'id': unknown_id,
            'filename': filename,
            'timestamp': timestamp.isoformat(),
            'size': stats.st_size,
            'path': f'/api/unknown-faces/image/{filename}'
        })
    faces.sort(key=lambda x: x['timestamp'], reverse=True)
    return {"faces": faces, "total": len(faces), "directory": UNKNOWN_FACES_DIR}

@app.get("/api/unknown-faces/image/{filename}")
def get_unknown_face_image(filename: str):
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = os.path.join(UNKNOWN_FACES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path, media_type="image/jpeg")

@app.delete("/api/unknown-faces/{filename}")
def delete_unknown_face(filename: str):
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = os.path.join(UNKNOWN_FACES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    os.remove(file_path)
    return {"message": "Unknown face deleted successfully", "filename": filename}

@app.get("/api/unknown-faces/stats")
def get_unknown_faces_stats():
    if not os.path.exists(UNKNOWN_FACES_DIR):
        return {"total": 0, "today": 0, "this_week": 0, "directory_exists": False}
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
    return {"total": total, "today": today, "this_week": this_week, "directory_exists": True}
