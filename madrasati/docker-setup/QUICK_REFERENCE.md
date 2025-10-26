# 🚀 Quick Reference: Face-Fused Container Rebuild

## ✅ What Was Fixed

### Path Configuration
- ✅ Removed hardcoded Windows path from `faceapi.py`
- ✅ Added environment variable support for all paths
- ✅ Works seamlessly in both local and Docker environments

### Configuration Files Updated
1. **faceapi.py** - Face Encoding API
   - CORS middleware added
   - All paths use environment variables
   - InsightFace parameters configurable

2. **app_with_env.py** - Real-time Detection
   - Backend URLs configurable
   - All paths use environment variables
   - All thresholds configurable

3. **unknown_faces_api_fastapi.py** - Unknown Faces API
   - Directory path configurable

4. **docker-compose.yml** - Container Config
   - All environment variables properly set
   - LOG_DIR added

5. **start_face_services_fused.sh** - Startup Script
   - Correct Docker paths
   - Proper permission setting
   - Model download check

## 🏃 Quick Deploy (3 Commands)

### Windows PowerShell
```powershell
cd C:\Users\ihedh\Downloads\madrasatiarabe\madrasati\docker-setup
.\rebuild-face-fused.ps1
docker-compose logs -f face-fused
```

### Linux/Mac
```bash
cd madrasati/docker-setup
chmod +x rebuild-face-fused.sh
./rebuild-face-fused.sh
docker-compose logs -f face-fused
```

## ✅ Quick Verification (5 Tests)

### 1. Container Status
```bash
docker-compose ps face-fused
# Expected: Status = Up
```

### 2. Face API Health
```bash
curl http://localhost:8000/students/encodings/status
# Expected: {"status":"ok","model":"arcface",...}
```

### 3. Unknown API Health
```bash
curl http://localhost:5001/api/unknown-faces
# Expected: {"faces":[],"total":0}
```

### 4. Environment Variables
```bash
docker exec madrasati_face_fused env | grep BACKEND
docker exec madrasati_face_fused env | grep DATASET
# Expected: See all configured variables
```

### 5. File Structure
```bash
docker exec madrasati_face_fused ls -la /app/madrasati/face/
# Expected: See dataset/, unknown_faces/, logs/ directories
```

## 🎯 Configuration Quick Reference

### Local Development (.env or defaults)
```bash
BACKEND_URL=http://localhost:3000
DATASET_DIR=dataset
ENCODINGS_FILE_ARCFACE=encodings_arcface.pkl
UNKNOWN_FACES_DIR=unknown_faces
LOG_DIR=logs
```

### Docker Deployment (docker-compose.yml)
```yaml
BACKEND_URL: http://backend:3000
DATASET_DIR: /app/madrasati/face/dataset
ENCODINGS_FILE_ARCFACE: /app/madrasati/face/encodings_arcface.pkl
UNKNOWN_FACES_DIR: /app/madrasati/face/unknown_faces
LOG_DIR: /app/madrasati/face/logs
```

## 🔧 Tuning Parameters

### Detection Sensitivity
```yaml
DET_THRESH: 0.5  # Lower = more sensitive (0.3-0.7)
```

### Recognition Strictness
```yaml
REC_THRESH: 0.45  # Higher = stricter (0.35-0.55)
```

### Performance
```yaml
DET_SIZE: 640      # 320=fast, 640=accurate
INSIGHTFACE_MODEL: buffalo_l  # buffalo_s=fast, buffalo_l=accurate
```

## 🐛 Common Issues & Fixes

### Issue: Container won't start
```bash
# Check logs
docker-compose logs face-fused

# Check ports
netstat -an | grep 8000
netstat -an | grep 5001

# Restart
docker-compose restart face-fused
```

### Issue: APIs not responding
```bash
# Enter container
docker exec -it madrasati_face_fused bash

# Test inside
curl http://localhost:8000/students/encodings/status
curl http://localhost:5001/api/unknown-faces

# Check processes
ps aux | grep uvicorn
```

### Issue: Wrong paths
```bash
# Check environment
docker exec madrasati_face_fused env | grep -E "DIR|FILE|URL"

# Check directories exist
docker exec madrasati_face_fused ls -la /app/madrasati/face/
```

### Issue: No faces detected
```bash
# Lower detection threshold
# Edit docker-compose.yml:
DET_THRESH: 0.3

# Restart
docker-compose restart face-fused
```

## 📋 End-to-End Test Checklist

- [ ] 1. Rebuild container (5-10 min first time)
- [ ] 2. Check container status (Up)
- [ ] 3. Test Face API (200 OK)
- [ ] 4. Test Unknown API (200 OK)
- [ ] 5. Verify environment variables
- [ ] 6. Upload student via frontend
- [ ] 7. Check encodings created (512-dim)
- [ ] 8. Test camera detection (if available)
- [ ] 9. Check unknown faces captured
- [ ] 10. Monitor logs for errors

## 🎉 Success Indicators

✅ Container shows "Up" status
✅ Both APIs respond with 200 OK
✅ No errors in logs
✅ Environment variables correct
✅ Directories exist in container
✅ Student uploads work
✅ Encodings show 512-dim embeddings
✅ Camera detection identifies faces

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `PATH_FIXES.md` | Detailed path configuration changes |
| `FACE_FUSED_COMPLETE_GUIDE.md` | Comprehensive deployment guide |
| `REBUILD_CHECKLIST.md` | Step-by-step verification |
| `ARCHITECTURE.md` | System architecture overview |
| `REBUILD_SUMMARY.md` | What was changed and why |
| `.env.example` | Configuration template |

## 🆘 Need Help?

1. Check logs: `docker-compose logs -f face-fused`
2. Review PATH_FIXES.md for configuration details
3. Check FACE_FUSED_COMPLETE_GUIDE.md troubleshooting section
4. Verify environment variables in docker-compose.yml
5. Test APIs manually with curl/PowerShell

## ⚡ One-Liner Commands

```bash
# Full rebuild and test
docker-compose down face-fused && docker-compose build --no-cache face-fused && docker-compose up -d face-fused && sleep 10 && curl http://localhost:8000/students/encodings/status

# Check everything
docker exec madrasati_face_fused bash -c "ls -la /app/madrasati/face/ && env | grep -E 'BACKEND|DATASET|ENCODINGS|UNKNOWN' && ps aux | grep uvicorn"

# Watch logs live
docker-compose logs -f face-fused | grep -E "✅|❌|🔧|⚠️"
```

---

**Ready to deploy!** Just run the rebuild script and follow the checklist. 🚀
