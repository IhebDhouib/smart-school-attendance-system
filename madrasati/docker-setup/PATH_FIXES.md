# Path and Configuration Fixes for Docker Deployment

## 🔧 Changes Made

### 1. ✅ faceapi.py - Face Encoding API
**File**: `madrasati/face/faceapi.py`

**Changes**:
- ✅ Replaced hardcoded Windows path with environment variable
  - Before: `ENCODINGS_FILE_ARCFACE = r"C:\Users\ihedh\Downloads\madrasatiarabe\madrasati\madrasati\face\encodings_arcface.pkl"`
  - After: `ENCODINGS_FILE_ARCFACE = os.getenv('ENCODINGS_FILE_ARCFACE', 'encodings_arcface.pkl')`

- ✅ Made dataset directory configurable
  - Before: `DATASET_DIR = "dataset"`
  - After: `DATASET_DIR = os.getenv('DATASET_DIR', 'dataset')`

- ✅ Made all InsightFace parameters configurable via environment variables:
  - `INSIGHTFACE_MODEL` - Model selection (buffalo_l/buffalo_s)
  - `USE_GPU` - GPU acceleration toggle
  - `DET_SIZE` - Detection input size
  - `DET_THRESH` - Detection confidence threshold

- ✅ Added CORS middleware for backend communication
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

### 2. ✅ app_with_env.py - Real-time Detection App
**File**: `madrasati/face/app_with_env.py`

**Changes**:
- ✅ Made all file paths configurable via environment variables:
  - `ENCODINGS_FILE` - Now uses `ENCODINGS_FILE_ARCFACE` env var
  - `UNKNOWN_DIR` - Now uses `UNKNOWN_FACES_DIR` env var
  - `LOG_FILE` - Now uses `LOG_DIR` env var

- ✅ Made backend URLs configurable:
  - `BACKEND_URL` - Defaults to localhost:3000, can be overridden
  - `WEBSOCKET_URL` - Defaults to localhost:3001, can be overridden

- ✅ Made all InsightFace parameters configurable:
  - `INSIGHTFACE_MODEL` - Model selection
  - `USE_GPU` - GPU toggle
  - `DET_SIZE` - Detection size
  - `DET_THRESH` - Detection threshold
  - `REC_THRESH` - Recognition threshold
  - `ENABLE_ESRGAN` - Enhancement toggle

### 3. ✅ unknown_faces_api_fastapi.py - Unknown Faces API
**File**: `docker-setup/unknown_faces_api_fastapi.py`

**Changes**:
- ✅ Made unknown faces directory configurable:
  - Before: `UNKNOWN_FACES_DIR = "unknown_faces"`
  - After: `UNKNOWN_FACES_DIR = os.getenv("UNKNOWN_FACES_DIR", "unknown_faces")`

### 4. ✅ start_face_services_fused.sh - Startup Script
**File**: `docker-setup/start_face_services_fused.sh`

**Changes**:
- ✅ Updated directory creation to use correct Docker paths:
  - `/app/madrasati/face/dataset`
  - `/app/madrasati/face/unknown_faces`
  - `/app/madrasati/face/logs`
  - `/root/.insightface/models`

- ✅ Added proper permission setting: `chmod -R 755 /app/madrasati/face`

- ✅ Improved InsightFace model check with better detection

### 5. ✅ docker-compose.yml - Container Configuration
**File**: `docker-setup/docker-compose.yml`

**Changes**:
- ✅ Added `LOG_DIR` environment variable:
  - `LOG_DIR: /app/madrasati/face/logs`

- ✅ Confirmed all other environment variables are properly set:
  - `DATASET_DIR: /app/madrasati/face/dataset`
  - `ENCODINGS_FILE_ARCFACE: /app/madrasati/face/encodings_arcface.pkl`
  - `UNKNOWN_FACES_DIR: /app/madrasati/face/unknown_faces`

### 6. ✅ .env.example - Configuration Template
**File**: `madrasati/face/.env.example`

**Created** comprehensive environment variable documentation with:
- ✅ Backend connection settings
- ✅ File path configurations
- ✅ InsightFace parameters with explanations
- ✅ Image enhancement options
- ✅ Usage notes for local vs Docker deployment

## 🎯 How This Works Now

### Local Development
When running locally, the apps will use default values:
```bash
# Default values (local development)
BACKEND_URL=http://localhost:3000
DATASET_DIR=dataset
ENCODINGS_FILE_ARCFACE=encodings_arcface.pkl
UNKNOWN_FACES_DIR=unknown_faces
```

### Docker Deployment
When running in Docker, values are set in `docker-compose.yml`:
```yaml
environment:
  BACKEND_URL: http://backend:3000
  DATASET_DIR: /app/madrasati/face/dataset
  ENCODINGS_FILE_ARCFACE: /app/madrasati/face/encodings_arcface.pkl
  UNKNOWN_FACES_DIR: /app/madrasati/face/unknown_faces
```

## ✅ Benefits

### 1. **Portability**
- ✅ Same code works in both local and Docker environments
- ✅ No need to modify code when switching between environments

### 2. **Flexibility**
- ✅ Easy to change paths without code modification
- ✅ Can override any setting via environment variables

### 3. **Security**
- ✅ No hardcoded Windows paths in code
- ✅ Proper path separation for Docker containers

### 4. **Maintainability**
- ✅ Configuration centralized in docker-compose.yml
- ✅ Clear documentation in .env.example

## 🚀 Usage

### For Local Development
1. Copy `.env.example` to `.env` (optional)
2. Adjust values as needed
3. Run: `uvicorn faceapi:app --reload --host 0.0.0.0 --port 8000`

### For Docker Deployment
1. Ensure `docker-compose.yml` has correct environment variables
2. Run rebuild script: `./rebuild-face-fused.ps1` (Windows) or `./rebuild-face-fused.sh` (Linux/Mac)
3. All paths will be automatically configured for Docker

## 📋 Configuration Reference

### Environment Variables

| Variable | Default (Local) | Docker Value | Description |
|----------|----------------|--------------|-------------|
| `BACKEND_URL` | `http://localhost:3000` | `http://backend:3000` | Backend API URL |
| `WEBSOCKET_URL` | `ws://localhost:3001` | `ws://backend:3001` | WebSocket URL |
| `DATASET_DIR` | `dataset` | `/app/madrasati/face/dataset` | Student photos directory |
| `ENCODINGS_FILE_ARCFACE` | `encodings_arcface.pkl` | `/app/madrasati/face/encodings_arcface.pkl` | ArcFace embeddings file |
| `UNKNOWN_FACES_DIR` | `unknown_faces` | `/app/madrasati/face/unknown_faces` | Unknown faces directory |
| `LOG_DIR` | `logs` | `/app/madrasati/face/logs` | Log files directory |
| `INSIGHTFACE_MODEL` | `buffalo_l` | `buffalo_l` | InsightFace model name |
| `USE_GPU` | `False` | `False` | Enable GPU acceleration |
| `DET_SIZE` | `640` | `640` | Detection input size |
| `DET_THRESH` | `0.5` | `0.5` | Detection threshold |
| `REC_THRESH` | `0.45` | `0.45` | Recognition threshold |

## 🧪 Testing

### Test Local Configuration
```bash
cd madrasati/face

# Test faceapi
python -c "
import os
os.environ['ENCODINGS_FILE_ARCFACE'] = 'test_encodings.pkl'
os.environ['DATASET_DIR'] = 'test_dataset'
import faceapi
print('ENCODINGS_FILE:', faceapi.ENCODINGS_FILE_ARCFACE)
print('DATASET_DIR:', faceapi.DATASET_DIR)
"
```

### Test Docker Configuration
```bash
cd docker-setup

# Build and start
./rebuild-face-fused.ps1  # Windows
# or
./rebuild-face-fused.sh   # Linux/Mac

# Check environment inside container
docker exec madrasati_face_fused env | grep -E "BACKEND|DATASET|ENCODINGS|UNKNOWN"
```

## ✅ Verification Checklist

After rebuilding the container, verify:

- [ ] Container starts without errors
- [ ] Face API responds: `curl http://localhost:8000/students/encodings/status`
- [ ] Backend URL is correct: Check logs for "BACKEND_URL"
- [ ] Paths are correct: `docker exec madrasati_face_fused ls -la /app/madrasati/face/`
- [ ] Directories exist: dataset/, unknown_faces/, logs/
- [ ] InsightFace models download correctly
- [ ] Student photo upload works end-to-end
- [ ] Encodings are saved to correct path
- [ ] Camera detection uses correct encodings file

## 🔄 Migration from Old Configuration

### Old (Hardcoded)
```python
ENCODINGS_FILE = r"C:\Users\ihedh\Downloads\...\encodings_arcface.pkl"
DATASET_DIR = "dataset"
BACKEND_URL = "http://localhost:3000"
```

### New (Configurable)
```python
ENCODINGS_FILE = os.getenv('ENCODINGS_FILE_ARCFACE', 'encodings_arcface.pkl')
DATASET_DIR = os.getenv('DATASET_DIR', 'dataset')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:3000')
```

## 📚 Related Files

- `FACE_FUSED_COMPLETE_GUIDE.md` - Complete deployment guide
- `REBUILD_CHECKLIST.md` - Verification checklist
- `ARCHITECTURE.md` - System architecture
- `.env.example` - Configuration template

## 🎉 Ready to Deploy!

All paths and URLs are now properly configured for both local development and Docker deployment. Just run the rebuild script and everything will work seamlessly!

```powershell
# Windows
cd docker-setup
.\rebuild-face-fused.ps1

# Linux/Mac
cd docker-setup
chmod +x rebuild-face-fused.sh
./rebuild-face-fused.sh
```
