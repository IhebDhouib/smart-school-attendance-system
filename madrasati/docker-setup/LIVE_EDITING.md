# 🔄 Live Code Editing Guide - No Rebuild Needed!

## ✅ What's Configured

The face-fused container now mounts your local code as volumes, allowing you to edit Python files **without rebuilding the Docker image**.

### Mounted Directories

```yaml
volumes:
  # Live code editing - changes reflect immediately
  - ../madrasati/face:/app/madrasati/face
  - ./unknown_faces_api_fastapi.py:/app/docker-setup/unknown_faces_api_fastapi.py
  
  # Persistent data (survives container restarts)
  - face_encodings:/app/madrasati/face/encodings
  - face_unknown:/app/madrasati/face/unknown_faces
  - face_logs:/app/madrasati/face/logs
```

### Auto-Reload Enabled

Both FastAPI services run with `--reload` flag:
- ✅ **Face API** - Changes to `faceapi.py` auto-reload
- ✅ **Unknown API** - Changes to `unknown_faces_api_fastapi.py` auto-reload
- ⚠️ **Detection App** - Changes to `app_with_env.py` require manual restart (see below)

## 📝 How to Edit Code

### 1. Edit Files Locally

Simply edit the Python files in your local workspace:

**Windows:**
```
C:\Users\ihedh\Downloads\madrasatiarabe\madrasati\madrasati\face\
├── faceapi.py           ← Edit this (auto-reloads)
├── app_with_env.py      ← Edit this (manual restart)
├── utils.py             ← Edit this (restart services)
└── ...
```

**Docker-setup:**
```
C:\Users\ihedh\Downloads\madrasatiarabe\madrasati\docker-setup\
└── unknown_faces_api_fastapi.py  ← Edit this (auto-reloads)
```

### 2. See Changes Immediately

**For FastAPI files** (`faceapi.py` and `unknown_faces_api_fastapi.py`):
- Save the file
- Uvicorn automatically detects changes and reloads (2-3 seconds)
- Watch logs: `docker-compose logs -f face-fused`

**For Detection App** (`app_with_env.py`):
- Save the file
- Restart the detection app manually (see below)

## 🔄 Restart Services (When Needed)

### Restart Specific Service

**Face API only:**
```bash
docker exec madrasati_face_fused pkill -f "uvicorn faceapi"
# Service auto-restarts via monitoring script
```

**Unknown API only:**
```bash
docker exec madrasati_face_fused pkill -f "uvicorn unknown_faces"
# Service auto-restarts via monitoring script
```

**Detection App only:**
```bash
docker exec madrasati_face_fused pkill -f "app_with_env.py"
# Service auto-restarts via monitoring script
```

### Restart All Services

**Quick restart (keeps container running):**
```bash
docker-compose restart face-fused
```

**Full restart (container recreated):**
```bash
docker-compose down face-fused
docker-compose up -d face-fused
```

## 🧪 Testing Your Changes

### 1. Edit a File

Edit `faceapi.py` and add a test print statement:

```python
@app.get("/students/encodings/status")
async def get_encodings_status(model: str = 'arcface'):
    """Get status of ArcFace encodings"""
    print("🧪 TEST: Status endpoint called!")  # Add this line
    try:
        # ... rest of the code
```

### 2. Watch Logs

```bash
docker-compose logs -f face-fused
```

You'll see:
```
face-fused | INFO:     Will watch for changes in these directories: ['/app/madrasati/face']
face-fused | INFO:     Uvicorn running on http://0.0.0.0:8000
face-fused | Detected file change, reloading...
face-fused | INFO:     Application shutdown
face-fused | INFO:     Application startup
```

### 3. Test the Change

```bash
curl http://localhost:8000/students/encodings/status
```

Check logs for your test print statement.

## 📊 What Requires Rebuild vs Restart

### ✅ No Rebuild Needed (Just Edit & Save)
- Python code changes (`*.py`)
- Configuration values in code
- Function logic changes
- API endpoint changes
- Threshold adjustments

### 🔄 Restart Service (No Rebuild)
- Detection app changes
- Imported module changes
- Adding new dependencies to existing code

### 🔨 Rebuild Required
- New Python packages in `requirements-fused.txt`
- Dockerfile changes
- System dependencies (apt packages)
- Base image changes

## 💡 Development Workflow

### Typical Edit Cycle

```bash
# 1. Start containers (one time)
docker-compose up -d face-fused

# 2. Watch logs in one terminal
docker-compose logs -f face-fused

# 3. Edit code in VS Code (another terminal/window)
code madrasati/face/faceapi.py

# 4. Save file → Auto-reload happens

# 5. Test changes
curl http://localhost:8000/students/encodings/status

# 6. Repeat steps 3-5 as needed

# 7. When done, commit changes
git add madrasati/face/faceapi.py
git commit -m "Updated face API endpoints"
```

### Quick Test Loop

```bash
# Terminal 1: Watch logs
docker-compose logs -f face-fused | grep -E "🧪|✅|❌"

# Terminal 2: Edit and test
code faceapi.py
# Save file
sleep 3  # Wait for reload
curl http://localhost:8000/students/encodings/status
```

## 🐛 Troubleshooting Live Editing

### Changes Not Reflected

**Check volume mount:**
```bash
# List mounted volumes
docker inspect madrasati_face_fused | grep -A 10 "Mounts"

# Verify file inside container matches local
docker exec madrasati_face_fused cat /app/madrasati/face/faceapi.py | head -n 20
```

**Force reload:**
```bash
# Touch the file to trigger reload
docker exec madrasati_face_fused touch /app/madrasati/face/faceapi.py
```

### Service Not Auto-Restarting

**Check monitoring script:**
```bash
# View process tree
docker exec madrasati_face_fused ps auxf

# Check if monitoring is running
docker exec madrasati_face_fused pgrep -f start_face_services
```

### Syntax Errors After Edit

**Check logs for errors:**
```bash
docker-compose logs face-fused | tail -50
```

**Validate syntax locally first:**
```bash
cd madrasati/face
python -m py_compile faceapi.py
python -m py_compile app_with_env.py
```

## 📋 Common Edit Scenarios

### 1. Change Detection Threshold

**Edit:** `madrasati/face/faceapi.py` or `app_with_env.py`

```python
# Old
DET_THRESH = float(os.getenv("DET_THRESH", "0.5"))

# New (more sensitive)
DET_THRESH = float(os.getenv("DET_THRESH", "0.3"))
```

**Result:** Auto-reloads for faceapi.py, restart needed for app_with_env.py

### 2. Add Debug Logging

**Edit:** Any `.py` file

```python
# Add at function start
print(f"🔍 DEBUG: Processing {matricule} with params: {locals()}")
```

**Result:** Auto-reloads, immediately visible in logs

### 3. Modify API Response

**Edit:** `madrasati/face/faceapi.py`

```python
# Add field to response
return {
    "status": "ok",
    "model": "arcface",
    "debug_info": "Added during development"  # New field
}
```

**Result:** Auto-reloads, test with curl

### 4. Update Image Enhancement

**Edit:** `madrasati/face/app_with_env.py`

```python
# Change enhancement parameters
CLAHE_CLIP_LIMIT = 2.5  # Increased from 2.0
```

**Result:** Need to restart detection app

## 🎯 Best Practices

### Do's ✅
- Edit code locally in VS Code
- Watch logs while testing
- Test changes with curl/PowerShell
- Commit working changes frequently
- Use print statements for debugging
- Validate syntax before saving

### Don'ts ❌
- Don't edit files inside container directly
- Don't forget to save files after editing
- Don't add new packages without rebuilding
- Don't ignore syntax errors in logs
- Don't restart container unnecessarily

## 🚀 Quick Commands Reference

```bash
# Watch logs with colors
docker-compose logs -f face-fused | grep --color=auto -E "INFO|ERROR|WARNING|🔧|✅|❌"

# Test Face API
curl http://localhost:8000/students/encodings/status | jq

# Test Unknown API
curl http://localhost:5001/api/unknown-faces | jq

# Check if reload is working
docker-compose logs face-fused | grep "Detected file change"

# Force reload all services
docker-compose restart face-fused

# Enter container for debugging
docker exec -it madrasati_face_fused bash
```

## 📊 Performance Impact

| Action | Time | Impact |
|--------|------|--------|
| Edit & Save | Instant | None |
| Auto-Reload (FastAPI) | 2-3 sec | Brief API downtime |
| Restart Service | 5-10 sec | Service unavailable |
| Restart Container | 10-20 sec | All services restart |
| Rebuild Image | 5-10 min | Full downtime |

## ✅ Verification

After setup, verify live editing works:

1. **Edit faceapi.py:**
   ```python
   # Add to any endpoint
   print("🧪 Live editing works!")
   ```

2. **Save file and watch logs:**
   ```bash
   docker-compose logs -f face-fused
   ```

3. **See reload message:**
   ```
   INFO: Detected file change, reloading...
   ```

4. **Test endpoint:**
   ```bash
   curl http://localhost:8000/students/encodings/status
   ```

5. **See your print in logs:**
   ```
   🧪 Live editing works!
   ```

🎉 **You're ready for rapid development!** Edit code and see changes instantly without rebuilding Docker images.
