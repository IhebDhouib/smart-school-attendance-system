# Face-Fused Container Rebuild Checklist

## ✅ Pre-Build Checklist

- [ ] Docker Desktop is running
- [ ] No other services using ports 8000 or 5001
- [ ] Camera `/dev/video0` is available (Linux) or built-in webcam (Windows)
- [ ] At least 2GB free disk space for Docker images
- [ ] Backend service is configured with FACE_API_URL

## 🔨 Build Steps

### Windows (PowerShell)
```powershell
cd C:\Users\ihedh\Downloads\madrasatiarabe\madrasati\docker-setup
.\rebuild-face-fused.ps1
```

### Linux/Mac (Bash)
```bash
cd ~/madrasatiarabe/madrasati/docker-setup
chmod +x rebuild-face-fused.sh
./rebuild-face-fused.sh
```

## ✅ Post-Build Verification

- [ ] Container status shows "Up"
  ```bash
  docker-compose ps face-fused
  ```

- [ ] Face API responds on port 8000
  ```bash
  curl http://localhost:8000/students/encodings/status
  # or PowerShell:
  Invoke-WebRequest http://localhost:8000/students/encodings/status
  ```

- [ ] Unknown Faces API responds on port 5001
  ```bash
  curl http://localhost:5001/api/unknown-faces
  # or PowerShell:
  Invoke-WebRequest http://localhost:5001/api/unknown-faces
  ```

- [ ] Logs show successful startup
  ```bash
  docker-compose logs face-fused | grep "✅"
  ```
  Expected to see:
  - ✅ InsightFace initialized successfully!
  - ✅ Face API started with PID
  - ✅ Unknown Faces API started with PID
  - ✅ Face Detection App started with PID

- [ ] InsightFace models downloaded
  ```bash
  docker exec madrasati_face_fused ls -la /root/.insightface/models/
  ```

## 🧪 Functional Tests

### Test 1: Health Check
```bash
# Face API health
curl http://localhost:8000/students/encodings/status

# Expected: {"status":"ok","model":"arcface",...}
```

### Test 2: API Documentation
```
Open browser: http://localhost:8000/docs
```
Should show FastAPI Swagger UI

### Test 3: Backend Integration
```bash
# Check backend can reach face API
docker exec madrasati_backend curl http://face-fused:8000/students/encodings/status
```

### Test 4: Upload Test Student (via Angular Frontend)
- [ ] Open Angular app in browser
- [ ] Navigate to Students section
- [ ] Add a test student with photo
- [ ] Check backend logs for "Face API Add result"
- [ ] Verify encoding created:
  ```bash
  curl http://localhost:8000/students/encodings/status
  # Should show total_faces > 0
  ```

### Test 5: Camera Detection (if camera available)
- [ ] Check logs for camera initialization:
  ```bash
  docker-compose logs -f face-fused | grep "Camera"
  ```
- [ ] Stand in front of camera
- [ ] Check logs for face detection messages

### Test 6: Unknown Faces
- [ ] Have someone unknown stand in front of camera
- [ ] Check unknown faces directory:
  ```bash
  curl http://localhost:5001/api/unknown-faces
  # Should show captured unknown face
  ```

## 🐛 Troubleshooting Quick Checks

If build fails:
- [ ] Check Docker daemon is running
- [ ] Check internet connectivity (for apt-get and pip)
- [ ] Clear Docker build cache: `docker system prune -a`
- [ ] Check disk space: `docker system df`

If container won't start:
- [ ] Check port conflicts: `netstat -an | grep 8000`
- [ ] Check logs: `docker-compose logs face-fused`
- [ ] Verify volumes exist: `docker volume ls | grep face`
- [ ] Try removing and recreating volumes

If APIs don't respond:
- [ ] Verify container is running: `docker ps | grep face-fused`
- [ ] Check inside container: `docker exec -it madrasati_face_fused bash`
- [ ] Test localhost inside container: `curl http://localhost:8000/students/encodings/status`
- [ ] Check firewall rules

If no faces detected:
- [ ] Lower DET_THRESH to 0.3 in docker-compose.yml
- [ ] Check camera access: `docker exec madrasati_face_fused ls -l /dev/video0`
- [ ] Verify good lighting conditions
- [ ] Check logs for RetinaFace initialization

If recognition accuracy is low:
- [ ] Ensure 3-5 photos per student
- [ ] Check photo quality (clear faces, good lighting)
- [ ] Adjust REC_THRESH (lower = more lenient)
- [ ] Rebuild encodings: `curl -X POST http://localhost:8000/students/encodings/rebuild`

## 📋 Expected Log Output

Successful startup logs should show:
```
🚀 Starting Madrasati Face Services (Fused Container)
==================================================
🔍 Checking InsightFace models...
🔧 Starting Face Encoding API (port 8000)...
✅ Face API started with PID 15
🔧 Starting Unknown Faces API (port 5001)...
✅ Unknown Faces API started with PID 23
🔧 Starting Real-time Face Detection App...
✅ Face Detection App started with PID 31
==================================================
✅ All services started successfully!
   - Face API:        http://0.0.0.0:8000
   - Unknown API:     http://0.0.0.0:5001
   - Detection App:   Running in background
==================================================
```

Face API initialization:
```
🔧 Initializing InsightFace (RetinaFace + ArcFace)...
Applied providers: ['CPUExecutionProvider'], with options: {...}
✅ InsightFace initialized successfully!
   Model: buffalo_l
   Providers: ['CPUExecutionProvider']
INFO:     Started server process [15]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## ✅ Final Checklist

Before marking as complete, verify:
- [ ] All three services are running (face API, unknown API, detection app)
- [ ] No error messages in logs
- [ ] Face API health check passes
- [ ] Backend can communicate with face API
- [ ] Frontend can upload student photos successfully
- [ ] Encodings are created with 512-dimensional ArcFace embeddings
- [ ] Camera detection works (if camera available)
- [ ] Unknown faces are captured when needed

## 🎉 Success Criteria

Your deployment is successful when:
1. ✅ Container runs without errors
2. ✅ All APIs respond correctly
3. ✅ Student photos can be uploaded and encoded
4. ✅ Encodings show 512-dim ArcFace embeddings
5. ✅ Camera detection identifies registered students
6. ✅ Unknown faces are saved correctly

## 📚 Documentation References

- Main guide: `FACE_FUSED_COMPLETE_GUIDE.md`
- Migration details: `RETINAFACE_MIGRATION.md` (in madrasati/face/)
- Backend integration: `routes/student.js` (FACE_API_URL configuration)

## 🆘 Need Help?

1. Check logs: `docker-compose logs -f face-fused`
2. Review troubleshooting section in `FACE_FUSED_COMPLETE_GUIDE.md`
3. Test each service individually
4. Verify environment variables in `docker-compose.yml`
