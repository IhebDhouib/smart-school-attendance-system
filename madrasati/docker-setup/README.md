# Madrasati Docker Setup

This Docker setup provides a complete containerized environment for the Madrasati school management system with face recognition capabilities.

## Architecture Overview

The system consists of 5 main services:

1. **Frontend (Angular)** - Web interface running on port 80
2. **Backend (Node.js)** - API server running on port 3000 with WebSocket on 3001
3. **Face API (FastAPI)** - Face encoding service running on port 8000
4. **Face Detection (Python)** - Real-time face recognition running as background service
5. **MongoDB** - Database running on port 27017

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available for containers
- Camera devices (USB/IP cameras) for face detection

## Quick Start

1. **Clone and prepare the project:**
   ```bash
   # Extract your madrasati.rar file to the parent directory
   # The structure should be: madrasati/docker-setup/
   ```

2. **Configure environment:**
   ```bash
   cd docker-setup
   cp .env.example .env
   # Edit .env file with your camera URLs and other settings
   ```

3. **Build and start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Check service status:**
   ```bash
   docker-compose ps
   ```

5. **Access the application:**
   - Frontend: http://localhost
   - Backend API: http://localhost:3000
   - Face API: http://localhost:8000
   - MongoDB: localhost:27017

## Detailed Configuration

### Camera Configuration

The face detection service supports multiple camera sources. Configure them in your `.env` file:

```bash
# Entry cameras (tried in order until one works)
ENTRY_CAMERA_1=http://192.168.1.66:8080/video  # IP camera
ENTRY_CAMERA_2=1                                # USB camera index

# Exit cameras
EXIT_CAMERA_1=0                                 # Default USB camera
EXIT_CAMERA_2=http://192.168.1.68:5001/video   # IP camera
EXIT_CAMERA_3=0                                 # Fallback camera
```

**Camera Source Types:**
- **USB Cameras:** Use integer values (0, 1, 2, etc.)
- **IP Cameras:** Use full URLs (http://ip:port/video)
- **RTSP Streams:** Use rtsp:// URLs

### Database Configuration

MongoDB is automatically initialized with:
- Database: `madrasati`
- Default admin user: `admin@madrasati.com` / `password`
- Required collections and indexes

### Security Configuration

**Important:** Change these values in production:

```bash
# Strong password for MongoDB
MONGO_PASSWORD=your-secure-mongodb-password

# Long random string for JWT tokens
JWT_SECRET=your-very-long-random-jwt-secret-key-at-least-32-characters
```



## Service Management

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d frontend

# View logs
docker-compose logs -f
docker-compose logs -f backend
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: This deletes all data!)
docker-compose down -v
```

### Updating Services

```bash
# Rebuild and restart all services
docker-compose up -d --build

# Rebuild specific service
docker-compose up -d --build backend
```

## Data Management

### Volumes

The system uses several Docker volumes for persistent data:

- `mongodb_data` - Database files
- `backend_uploads` - Uploaded files (student photos, schedules)
- `face_dataset` - Face recognition training data
- `face_encodings` - Processed face encodings
- `face_unknown` - Unknown faces detected by the system
- `face_logs` - Face detection logs

### Backup

```bash
# Backup MongoDB
docker exec madrasati_mongodb mongodump --out /backup
docker cp madrasati_mongodb:/backup ./mongodb_backup

# Backup uploaded files
docker cp madrasati_backend:/app/uploads ./uploads_backup

# Backup face data
docker cp madrasati_face_api:/app/dataset ./dataset_backup
```

### Restore

```bash
# Restore MongoDB
docker cp ./mongodb_backup madrasati_mongodb:/backup
docker exec madrasati_mongodb mongorestore /backup

# Restore uploaded files
docker cp ./uploads_backup/. madrasati_backend:/app/uploads/
```

## Face Recognition Setup

### Initial Setup

1. **Prepare face dataset:**
   ```bash
   # Create dataset directory structure
   mkdir -p face_data/dataset/student_id_1
   mkdir -p face_data/dataset/student_id_2
   
   # Add student photos (multiple photos per student recommended)
   # face_data/dataset/student_id_1/photo1.jpg
   # face_data/dataset/student_id_1/photo2.jpg
   ```

2. **Copy dataset to container:**
   ```bash
   docker cp face_data/dataset/. madrasati_face_api:/app/dataset/
   ```

3. **Generate face encodings:**
   ```bash
   docker exec madrasati_face_api python encode_faces.py
   ```

### Adding New Students

1. Add photos to dataset directory
2. Copy to container
3. Regenerate encodings
4. Restart face detection service

```bash
# Add new student photos
docker cp new_student_photos/. madrasati_face_api:/app/dataset/
docker exec madrasati_face_api python encode_faces.py
docker-compose restart face-detection
```


## Troubleshooting

### Common Issues

**1. Camera Connection Issues**
```bash
# Check camera access
docker exec madrasati_face_detection ls /dev/video*

# Test camera manually
docker exec -it madrasati_face_detection python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"

# Check logs
docker-compose logs face-detection
```

**2. Face Recognition Not Working**
```bash
# Check if encodings file exists
docker exec madrasati_face_api ls -la encodings.pkl

# Regenerate encodings
docker exec madrasati_face_api python encode_faces.py

# Check dataset structure
docker exec madrasati_face_api find dataset -name "*.jpg" | head -10
```

**3. Database Connection Issues**
```bash
# Check MongoDB status
docker-compose logs mongodb

# Test connection
docker exec madrasati_backend node -e "console.log('Testing DB connection...')"
```

**4. Frontend Not Loading**
```bash
# Check nginx logs
docker-compose logs frontend

# Verify backend connectivity
curl http://localhost:3000/api/health
```

### Performance Optimization

**For Production Environments:**

1. **Increase memory limits:**
   ```yaml
   services:
     face-detection:
       deploy:
         resources:
           limits:
             memory: 2G
           reservations:
             memory: 1G
   ```

2. **Use GPU acceleration (if available):**
   ```yaml
   services:
     face-detection:
       runtime: nvidia
       environment:
         - NVIDIA_VISIBLE_DEVICES=all
   ```

3. **Optimize camera resolution:**
   ```bash
   # In face detection service, modify frame processing
   # Reduce resolution for better performance
   ```

## Production Deployment

### Server Requirements

- **Minimum:** 4GB RAM, 2 CPU cores, 50GB storage
- **Recommended:** 8GB RAM, 4 CPU cores, 100GB SSD
- **Network:** Stable internet connection for IP cameras
- **OS:** Ubuntu 20.04+ or CentOS 8+

### Security Hardening

1. **Change default passwords:**
   ```bash
   # Update .env file with strong passwords
   MONGO_PASSWORD=very-secure-mongodb-password-123!
   JWT_SECRET=super-long-random-jwt-secret-key-for-production-use
   ```

2. **Use reverse proxy:**
   ```bash
   # Install nginx on host
   sudo apt install nginx
   
   # Configure SSL with Let's Encrypt
   sudo certbot --nginx -d yourdomain.com
   ```

3. **Firewall configuration:**
   ```bash
   # Allow only necessary ports
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

4. **Regular backups:**
   ```bash
   # Create backup script
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   docker exec madrasati_mongodb mongodump --out /backup/$DATE
   docker cp madrasati_mongodb:/backup/$DATE ./backups/
   ```

### Monitoring

1. **Health checks:**
   ```bash
   # Add to docker-compose.yml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

2. **Log management:**
   ```bash
   # Configure log rotation
   docker-compose logs --tail=1000 > madrasati.log
   ```

### Scaling

For high-traffic environments:

1. **Load balancer setup**
2. **Database clustering**
3. **Multiple face detection instances**
4. **CDN for static assets**

## API Documentation

### Backend API Endpoints

- `GET /api/health` - Health check
- `POST /api/auth/login` - User authentication
- `GET /api/students` - List students
- `POST /api/attendance` - Record attendance
- `GET /api/attendance/:studentId` - Get student attendance

### Face API Endpoints

- `POST /face/encode` - Encode face from image
- `GET /face/validate` - Validate encodings
- `POST /face/upload` - Upload training images

## Support

For issues and questions:

1. Check the logs: `docker-compose logs`
2. Review this documentation
3. Check camera connections and permissions
4. Verify environment configuration
5. Test individual services

## License

This Docker setup is provided as-is for the Madrasati project.

