# Face-Fused Development Setup

This guide explains how to run the face-fused service in development mode with live code reloading.

## 🚀 Quick Start

### Windows
```bash
# Build and run in one command
run-dev.bat

# Or build first, then run
build-dev.bat
docker-compose -f docker-compose.dev.yml up face-fused
```

### Linux/Mac
```bash
# Build and run in one command
./run-dev.sh

# Or build first, then run
./build-dev.sh
docker-compose -f docker-compose.dev.yml up face-fused
```

## 📁 What This Setup Does

### ✅ Development Mode Features
- **Live Code Reloading**: Changes to Python files are reflected immediately
- **Volume Mounting**: Source code is mounted as read-only volumes
- **No Rebuilds**: Edit code without rebuilding Docker images
- **Full Debugging**: Access to all development tools and logs

### 🔧 Mounted Volumes
- `../madrasati/face/` → `/app/face/` (read-only)
- `./app_with_env.py` → `/app/app_with_env.py` (read-only)
- `./sync_encodings_with_db.py` → `/app/sync_encodings_with_db.py` (read-only)
- `./unknown_faces_api_fastapi.py` → `/app/unknown_faces_api_fastapi.py` (read-only)
- Data directories remain read-write for persistence

## 🛠️ Development Workflow

1. **Start Development Environment**:
   ```bash
   run-dev.bat  # Windows
   # or
   ./run-dev.sh  # Linux/Mac
   ```

2. **Edit Code**: Modify any Python file in:
   - `madrasati/face/` (face detection, API, etc.)
   - `docker-setup/app_with_env.py` (main application)
   - `docker-setup/sync_encodings_with_db.py` (sync script)
   - `docker-setup/unknown_faces_api_fastapi.py` (FastAPI service)

3. **See Changes Instantly**: The container automatically uses your updated code

4. **Stop Development**:
   ```bash
   Ctrl+C
   # or
   docker-compose -f docker-compose.dev.yml down
   ```

## 🔄 Switching Between Development and Production

### Development Mode
```bash
# Use development compose file
docker-compose -f docker-compose.dev.yml up face-fused
```

### Production Mode
```bash
# Use production compose file (copies code during build)
docker-compose up face-fused
```

## 📊 Performance Considerations

- **Development**: Slightly slower startup due to volume mounting, but faster iteration
- **Production**: Faster runtime, but requires rebuilds for code changes
- **Data Persistence**: Both modes preserve encodings, unknown faces, and logs

## 🐛 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs face-fused

# Rebuild if needed
docker-compose -f docker-compose.dev.yml build --no-cache face-fused
```

### Code Changes Not Reflecting
```bash
# Restart the service
docker-compose -f docker-compose.dev.yml restart face-fused

# Or check if files are properly mounted
docker exec -it madrasati_face_fused_dev ls -la /app/
```

### Permission Issues
```bash
# Fix file permissions if needed
docker exec -it madrasati_face_fused_dev chmod +x /app/*.py
```

## 📝 File Structure

```
docker-setup/
├── Dockerfile.face-fused          # Production Dockerfile
├── docker-compose.dev.yml         # Development compose
├── docker-compose.yml             # Production compose
├── build-dev.bat/.sh             # Build scripts
├── run-dev.bat/.sh               # Run scripts
└── README-dev.md                 # This file

madrasati/face/                   # Source code (mounted in dev mode)
├── app_with_env.py              # Main application
├── faceapi.py                   # FastAPI service
├── requirements-fused.txt       # Python dependencies
└── ...                          # Other face service files
```

## 🎯 Best Practices

1. **Use Development Mode for Development**: Always use `docker-compose.dev.yml` during development
2. **Commit Clean Code**: Switch to production mode before committing
3. **Monitor Logs**: Use `docker-compose logs -f` to monitor real-time logs
4. **Resource Management**: Stop containers when not in use to free resources

Happy coding! 🚀
