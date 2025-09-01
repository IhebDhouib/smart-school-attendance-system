# Madrasati Production Deployment

## Quick Setup on Server:

### 1. Create deployment directory
```bash
mkdir -p ~/madrasati-deploy && cd ~/madrasati-deploy
```

### 2. Create docker-compose.production.yml
```bash
cat > docker-compose.production.yml << 'EOF'
services:
  # MongoDB Database
  mongodb:
    image: mongo:6.0
    container_name: madrasati_mongodb
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-madrasati123}
      MONGO_INITDB_DATABASE: madrasati
    volumes:
      - mongodb_data:/data/db
      - ./init-mongo.js:/docker-entrypoint-initdb.d/init-mongo.js:ro
    ports:
      - "27017:27017"
    networks:
      - madrasati_network

  # MongoDB Web Interface
  mongo-express:
    image: mongo-express:1.0.0
    container_name: madrasati_mongo_express
    restart: unless-stopped
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: ${MONGO_PASSWORD:-madrasati123}
      ME_CONFIG_MONGODB_URL: mongodb://admin:${MONGO_PASSWORD:-madrasati123}@mongodb:27017/
      ME_CONFIG_BASICAUTH_USERNAME: ""
      ME_CONFIG_BASICAUTH_PASSWORD: ""
      ME_CONFIG_MONGODB_ENABLE_ADMIN: true
    ports:
      - "8081:8081"
    depends_on:
      - mongodb
    networks:
      - madrasati_network

  # Node.js Backend
  backend:
    image: ihebdhouib/madrasati-backend:latest
    container_name: madrasati_backend
    restart: unless-stopped
    environment:
      NODE_ENV: production
      PORT: 3000
      WEBSOCKET_PORT: 3001
      MONGODB_URI: mongodb://admin:${MONGO_PASSWORD:-madrasati123}@mongodb:27017/madrasati?authSource=admin
      JWT_SECRET: ${JWT_SECRET:-your-super-secret-jwt-key-change-this-in-production}
    volumes:
      - backend_uploads:/app/uploads
      - backend_logs:/app/logs
    ports:
      - "3000:3000"
      - "3001:3001"
    depends_on:
      - mongodb
    networks:
      - madrasati_network

  # Face Detection Service
  face-fused:
    image: ihebdhouib/madrasati-face-fused:latest
    container_name: madrasati_face_fused
    restart: unless-stopped
    environment:
      PYTHONUNBUFFERED: 1
      BACKEND_URL: http://backend:3000
      WEBSOCKET_URL: ws://backend:3001
    volumes:
      - face_encodings:/app/encodings
      - face_unknown:/app/unknown_faces
    ports:
      - "8000:8000"
      - "5001:5001"
    depends_on:
      - backend
    networks:
      - madrasati_network
    privileged: true
    devices:
      - /dev/video0:/dev/video0

  # Angular Frontend
  frontend:
    image: ihebdhouib/madrasati-frontend:latest
    container_name: madrasati_frontend
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - madrasati_network

volumes:
  mongodb_data:
    driver: local
  face_encodings:
    driver: local
  face_unknown:
    driver: local
  backend_uploads:
    driver: local
  backend_logs:
    driver: local

networks:
  madrasati_network:
    driver: bridge
EOF
```

### 3. Create init-mongo.js
```bash
cat > init-mongo.js << 'EOF'
// MongoDB initialization script for Madrasati
db = db.getSiblingDB('madrasati');

// Create collections
db.createCollection('students');
db.createCollection('classrooms');
db.createCollection('attendance');
db.createCollection('cameras');
db.createCollection('users');

// Create indexes for better performance
db.students.createIndex({ "matricule": 1 }, { unique: true });
db.students.createIndex({ "classId": 1 });
db.attendance.createIndex({ "studentId": 1, "date": 1 });
db.attendance.createIndex({ "classId": 1, "date": 1 });
db.cameras.createIndex({ "ip": 1 }, { unique: true });
db.cameras.createIndex({ "classroom": 1 });

print('Madrasati database initialized successfully');
EOF
```

### 4. Create environment file
```bash
cat > .env << EOF
MONGO_PASSWORD=madrasati123
JWT_SECRET=your-super-secret-jwt-key-$(date +%s)
COMPOSE_PROJECT_NAME=madrasati
EOF
```

### 5. Login to DockerHub and fix Docker permissions
```bash
# Login to DockerHub first
sudo docker login
# Enter username: ihebdhouib
# Enter password: [your DockerHub password]

# Check if Docker is installed via snap
which docker

# If output is /snap/bin/docker, you need to use sudo or install docker-compose
# Option 1: Use sudo for all docker commands
# Option 2: Install docker-compose separately
sudo snap install docker-compose

# Or create docker group manually (if it doesn't exist)
sudo groupadd docker
sudo usermod -aG docker $USER
# Then logout and login again, or use: newgrp docker
```

### 6. Deploy
```bash
# Pull latest images (use sudo if needed)
docker-compose -f docker-compose.production.yml pull

# Start services (use sudo if needed)
docker-compose -f docker-compose.production.yml up -d

# Check status (use sudo if needed)
docker-compose -f docker-compose.production.yml ps
```

## Access Points:
- Frontend: http://YOUR_SERVER_IP
- Database Admin: http://YOUR_SERVER_IP:8081
- Backend API: http://YOUR_SERVER_IP:3000

## Management Commands:
```bash
# View logs
docker-compose -f docker-compose.production.yml logs -f

# Stop all services
docker-compose -f docker-compose.production.yml down

# Restart services
docker-compose -f docker-compose.production.yml restart
```
