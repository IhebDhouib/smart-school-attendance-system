# Face-Fused Container - Complete Setup Guide

## 🎯 Overview

The face-fused container is an all-in-one service that includes:
1. **Face Encoding API** (port 8000) - Handles student photo uploads and ArcFace encoding
2. **Unknown Faces API** (port 5001) - Manages unrecognized faces detected by cameras
3. **Real-time Face Detection** - Monitors camera feeds and sends attendance via WebSocket

## 🔧 Technology Stack

### Face Recognition (Modern Pipeline)
- **RetinaFace** - Face detection (via InsightFace)
- **ArcFace** - Face recognition with 512-dim embeddings
- **onnxruntime** - Optimized inference engine

### Why InsightFace?
Replaced the old `face_recognition` (dlib) library with InsightFace for:
- ✅ Better accuracy at distance (3+ meters)
- ✅ Improved outdoor/low-light performance
- ✅ Modern neural network architecture
- ✅ 512-dimensional embeddings (vs 128-dim)
- ✅ Faster inference with ONNX runtime

## 📦 What's Included

### Files Updated
```
docker-setup/
├── Dockerfile.face-fused              # Updated with InsightFace
├── docker-compose.yml                 # Updated face-fused service config
├── start_face_services_fused.sh       # Startup script with monitoring
├── rebuild-face-fused.sh              # Linux/Mac rebuild script
├── rebuild-face-fused.ps1             # Windows PowerShell rebuild script
└── unknown_faces_api_fastapi.py       # Unknown faces management

madrasati/face/
├── faceapi.py                         # Face encoding API (updated for ArcFace)
├── app_with_env.py                    # Real-time detection (updated for RetinaFace)
├── requirements-fused.txt             # Combined requirements with InsightFace
└── requirements_insightface.txt       # InsightFace-specific requirements
```

## 🚀 Quick Start

### Option 1: Use the Rebuild Script (Recommended)

**Windows PowerShell:**
```powershell
cd C:\Users\ihedh\Downloads\madrasatiarabe\madrasati\docker-setup
.\rebuild-face-fused.ps1
```

**Linux/Mac:**
```bash
cd ~/madrasatiarabe/madrasati/docker-setup
chmod +x rebuild-face-fused.sh
./rebuild-face-fused.sh
```

### Option 2: Manual Docker Commands

```bash
cd docker-setup

# Stop and remove old container
docker-compose stop face-fused
docker-compose rm -f face-fused

# Remove old image
docker rmi madrasati_face_fused

# Build with no cache (recommended for updates)
docker-compose build --no-cache face-fused

# Start the service
docker-compose up -d face-fused

# View logs
docker-compose logs -f face-fused
```

## 🔍 Verification Steps

### 1. Check Container Status
```bash
docker-compose ps face-fused
```
Should show status as "Up"

### 2. Test Face Encoding API
```bash
# Linux/Mac
curl http://localhost:8000/students/encodings/status

# Windows PowerShell
Invoke-WebRequest http://localhost:8000/students/encodings/status
```

Expected response:
```json
{
  "status": "ok",
  "model": "arcface",
  "model_name": "ArcFace (512-dim)",
  "embedding_dimension": 512,
  "total_faces": 0,
  "unique_students": 0,
  "dataset_students": 0
}
```

### 3. Test Unknown Faces API
```bash
# Linux/Mac
curl http://localhost:5001/api/unknown-faces

# Windows PowerShell
Invoke-WebRequest http://localhost:5001/api/unknown-faces
```

### 4. Check Logs for Startup Messages
```bash
docker-compose logs face-fused
```

Look for these success messages:
```
🚀 Starting Madrasati Face Services (Fused Container)
🔧 Initializing InsightFace (RetinaFace + ArcFace)...
✅ InsightFace initialized successfully!
✅ Face API started with PID ...
✅ Unknown Faces API started with PID ...
✅ Face Detection App started with PID ...
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│          Madrasati Face-Fused Container                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Face Encoding API (port 8000)                  │  │
│  │  - Handles student photo uploads                │  │
│  │  - Encodes faces with RetinaFace + ArcFace      │  │
│  │  - Saves 512-dim embeddings to encodings.pkl    │  │
│  └─────────────────────────────────────────────────┘  │
│                          │                              │
│                          │                              │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Unknown Faces API (port 5001)                  │  │
│  │  - Serves unrecognized face images              │  │
│  │  - Allows review and deletion                   │  │
│  └─────────────────────────────────────────────────┘  │
│                          │                              │
│                          │                              │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Real-time Face Detection (app_with_env.py)     │  │
│  │  - Monitors camera feeds                        │  │
│  │  - Detects faces with RetinaFace                │  │
│  │  - Matches with ArcFace embeddings              │  │
│  │  - Sends attendance via WebSocket               │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## ⚙️ Configuration

### Environment Variables

Set in `docker-compose.yml`:

```yaml
environment:
  # Backend connection
  BACKEND_URL: http://backend:3000
  WEBSOCKET_URL: ws://backend:3001
  
  # InsightFace configuration
  INSIGHTFACE_MODEL: buffalo_l        # or buffalo_s for faster inference
  USE_GPU: "False"                    # Set to True if CUDA available
  DET_SIZE: 640                       # Detection input size (320/640)
  DET_THRESH: 0.5                     # Detection confidence threshold
  REC_THRESH: 0.45                    # Recognition similarity threshold
  
  # Paths
  DATASET_DIR: /app/madrasati/face/dataset
  ENCODINGS_FILE_ARCFACE: /app/madrasati/face/encodings_arcface.pkl
  UNKNOWN_FACES_DIR: /app/madrasati/face/unknown_faces
```

### Tuning Parameters

**DET_THRESH** (Detection Threshold)
- Range: 0.0 - 1.0
- Lower = More detections (more false positives)
- Higher = Fewer detections (may miss faces)
- Recommended: 0.5 for normal conditions, 0.3 for challenging conditions

**REC_THRESH** (Recognition Threshold)
- Range: 0.0 - 1.0 (cosine similarity)
- Higher = More strict matching
- Lower = More lenient matching
- Recommended: 0.45 (balanced), 0.55 (strict), 0.35 (lenient)

**DET_SIZE** (Detection Resolution)
- Options: 320, 640
- 320 = Faster, less accurate
- 640 = Slower, more accurate
- Recommended: 640 for production

**INSIGHTFACE_MODEL**
- `buffalo_l` = Large model (more accurate)
- `buffalo_s` = Small model (faster)
- Recommended: buffalo_l for production

## 🔄 Data Flow

### Student Registration Flow
```
1. User uploads photo via Angular frontend
   ↓
2. Node.js backend receives upload (port 3000)
   ↓
3. Backend forwards to Face API (port 8000)
   ↓
4. Face API detects face with RetinaFace
   ↓
5. Face API extracts 512-dim ArcFace embedding
   ↓
6. Embedding saved to encodings_arcface.pkl
   ↓
7. Backend saves student to MongoDB
```

### Real-time Attendance Flow
```
1. Camera captures frame
   ↓
2. app_with_env.py detects faces with RetinaFace
   ↓
3. Extracts ArcFace embeddings (512-dim)
   ↓
4. Compares with stored encodings (cosine similarity)
   ↓
5. If match found (similarity > REC_THRESH):
   - Sends attendance via WebSocket to backend
   Else:
   - Saves to unknown_faces directory
```

## 📊 Volumes & Persistence

```yaml
volumes:
  face_encodings:/app/madrasati/face/encodings      # Persistent encodings
  face_unknown:/app/madrasati/face/unknown_faces    # Unknown faces storage
  face_logs:/app/madrasati/face/logs                # Application logs
```

These volumes persist data across container restarts.

## 🛠️ Troubleshooting

### Problem: Container keeps restarting
```bash
# Check logs for errors
docker-compose logs --tail=100 face-fused

# Common issues:
# - Missing camera device (/dev/video0)
# - Port already in use (8000 or 5001)
# - InsightFace models not downloading
```

### Problem: No faces detected
```bash
# Enter container
docker exec -it madrasati_face_fused bash

# Check camera
ls -l /dev/video*

# Test camera manually
python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"

# Lower detection threshold
# Edit docker-compose.yml: DET_THRESH: 0.3
docker-compose restart face-fused
```

### Problem: Face API not responding
```bash
# Check if API is running
docker exec madrasati_face_fused ps aux | grep uvicorn

# Test API inside container
docker exec madrasati_face_fused curl http://localhost:8000/students/encodings/status

# Check firewall/ports
netstat -an | grep 8000
```

### Problem: Low recognition accuracy
1. Check if you have enough training photos per student (recommended: 3-5)
2. Ensure photos are clear and face is visible
3. Adjust REC_THRESH (lower = more lenient)
4. Rebuild encodings after adding more photos:
   ```bash
   curl -X POST http://localhost:8000/students/encodings/rebuild
   ```

### Problem: InsightFace models not downloading
```bash
# Enter container
docker exec -it madrasati_face_fused bash

# Manually download models
cd /root/.insightface
wget https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
unzip buffalo_l.zip

# Restart services
exit
docker-compose restart face-fused
```

## 📈 Performance Tips

### For Better Accuracy
- Use DET_SIZE=640
- Use INSIGHTFACE_MODEL=buffalo_l
- Capture 3-5 photos per student from different angles
- Ensure good lighting during photo capture
- REC_THRESH=0.50 (strict matching)

### For Better Speed
- Use DET_SIZE=320
- Use INSIGHTFACE_MODEL=buffalo_s
- REC_THRESH=0.40 (faster matching)
- Enable GPU if available (USE_GPU=True)

### For Outdoor/Distance
- DET_THRESH=0.3 (more sensitive detection)
- REC_THRESH=0.40 (account for quality variation)
- Use DET_SIZE=640 (better for small faces)
- Consider adding image enhancement (already in app_with_env.py)

## 🔐 Security Notes

1. **Camera Access**: Container needs privileged mode for camera access
2. **Ports**: Face APIs are exposed on localhost only by default
3. **Data Privacy**: Face encodings are stored locally in volumes
4. **Unknown Faces**: Review and delete unknown faces periodically

## 📚 API Documentation

### Face Encoding API (port 8000)
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Key endpoints:
- `POST /students/add` - Add student and encode face
- `GET /students/encodings/status` - Check encoding status
- `POST /students/encodings/rebuild` - Rebuild all encodings
- `DELETE /students/{matricule}` - Delete student and re-encode

### Unknown Faces API (port 5001)
Key endpoints:
- `GET /api/unknown-faces` - List all unknown faces
- `GET /api/unknown-faces/image/{filename}` - Get image
- `DELETE /api/unknown-faces/{filename}` - Delete unknown face
- `GET /api/unknown-faces/stats` - Get statistics

## 🎓 Next Steps

After successful deployment:

1. **Add test student**:
   - Use Angular frontend to add a student with photos
   - Check encoding status: `curl http://localhost:8000/students/encodings/status`

2. **Test camera detection**:
   - Stand in front of camera
   - Check logs: `docker-compose logs -f face-fused`
   - Look for recognition messages

3. **Monitor unknown faces**:
   - Visit: http://localhost:5001/api/unknown-faces
   - Review unrecognized faces
   - Add them to database if needed

4. **Performance tuning**:
   - Monitor logs for detection/recognition times
   - Adjust thresholds based on accuracy needs
   - Consider GPU acceleration for large deployments

## 🆘 Support

If you encounter issues:
1. Check logs: `docker-compose logs -f face-fused`
2. Verify configuration in `docker-compose.yml`
3. Test APIs manually with curl/PowerShell
4. Review this documentation for troubleshooting steps

For detailed migration information, see `RETINAFACE_MIGRATION.md`.
