# 📊 Streamlit Dataset Viewer Setup Guide

## ✅ What Was Added

The Streamlit Dataset Viewer is now integrated into the `face-fused` container, providing real-time monitoring and management capabilities.

## 🚀 How to Run

### 1. Rebuild the Container

```bash
# Stop existing containers
docker-compose down

# Rebuild face-fused container with Streamlit
docker-compose build face-fused

# Start all services
docker-compose up -d
```

### 2. Access the Streamlit Dashboard

Open your browser and go to:
```
http://localhost:8501
```

Or if on a server:
```
http://<server-ip>:8501
```

## 📋 Available Services

| Service | Port | URL |
|---------|------|-----|
| Face API | 8000 | http://localhost:8000 |
| Unknown Faces API | 5001 | http://localhost:5001 |
| **Streamlit Dashboard** | **8501** | **http://localhost:8501** |

## 🎯 Streamlit Features

### 📸 Dataset Images Tab
- View all student photos
- Delete individual images
- Delete entire student folders
- Encode/re-encode students

### 🧠 Encodings Tab
- View all face encodings
- Delete encodings
- Re-encode students
- Inspect encoding values

### 🔍 Compare Tab
- Find missing encodings
- Find orphaned encodings
- Quick encode/delete actions

### 📊 Analysis Tab
- Dataset statistics
- Match rate between photos and encodings
- Student-level breakdown

### 📝 **Logs Tab** (NEW!)
- **Real-time log monitoring**
- View Face API logs
- View Recognition App logs
- View Attendance CSV
- Filter by log level (INFO/WARNING/ERROR)
- Search logs by keyword
- Attendance statistics and charts

## 🛠️ Configuration

### Environment Variables

Add to your `.env` file:

```env
# Streamlit port (default: 8501)
STREAMLIT_PORT=8501
```

### Change Port

Edit `docker-compose.base.yml`:

```yaml
ports:
  - "9000:8501"  # Change 9000 to your desired port
```

## 🔧 Troubleshooting

### Streamlit Not Loading

1. **Check if service is running:**
```bash
docker logs madrasati_face_fused | grep Streamlit
```

2. **Expected output:**
```
📊 Starting Streamlit Dataset Viewer (port 8501)...
✅ Streamlit started with PID 123
```

3. **Check port is exposed:**
```bash
docker port madrasati_face_fused
```

### View Streamlit Logs

```bash
# View all logs
docker logs madrasati_face_fused

# Follow logs in real-time
docker logs -f madrasati_face_fused

# Filter for Streamlit
docker logs madrasati_face_fused | grep streamlit
```

### Restart Just the Streamlit Service

```bash
# Enter container
docker exec -it madrasati_face_fused bash

# Find Streamlit process
ps aux | grep streamlit

# Kill and restart
pkill -f streamlit
cd /app/madrasati/face
streamlit run streamlit_dataset_viewer.py --server.port 8501 --server.address 0.0.0.0 --server.headless true &
```

## 🔄 Auto-Restart

The Streamlit service automatically restarts if it crashes, monitored by the startup script.

## 📦 What Changed

### Files Modified:
1. ✅ `requirements-fused.txt` - Added `streamlit==1.29.0`
2. ✅ `Dockerfile.face-fused` - Exposed port 8501
3. ✅ `start_face_services_fused.sh` - Added Streamlit startup
4. ✅ `docker-compose.base.yml` - Added port mapping
5. ✅ `streamlit_dataset_viewer.py` - Added log monitoring tab

### Services Running in Container:
1. Face Encoding API (port 8000)
2. Unknown Faces API (port 5001)
3. **Streamlit Dashboard (port 8501)** ← NEW!
4. Face Detection App (background)

## 💡 Tips

- Use the 🔄 Refresh button in Logs tab for live updates
- Adjust "Number of lines" slider to view more/less logs
- Use level filters (INFO/WARNING/ERROR) to focus on issues
- Search functionality works across all log content
- Attendance CSV shows real-time recognition events

## 🎯 Next Steps

After starting the container:

1. Open http://localhost:8501
2. Navigate to **📝 Logs** tab
3. Select "Face Recognition App Logs"
4. Watch live face detection events!

Enjoy real-time monitoring! 🎉
