# Madrasati Docker Setup - Complete Package

## 📦 What's Included

This Docker setup provides a complete containerized solution for your Madrasati project with the following components:

### 🏗️ Architecture
- **Frontend**: Angular application with Nginx (Port 80)
- **Backend**: Node.js API server with WebSocket support (Ports 3000, 3001)
- **Face API**: FastAPI service for face encoding (Port 8000)
- **Face Detection**: Python service with configurable camera sources
- **Database**: MongoDB with automatic initialization (Port 27017)

### 📁 Files Structure
```
docker-setup/
├── Dockerfile.frontend          # Angular app containerization
├── Dockerfile.backend           # Node.js API containerization
├── Dockerfile.face-api          # FastAPI face encoding service
├── Dockerfile.face-detection    # Python face detection service
├── docker-compose.yml           # Main orchestration file
├── docker-compose.prod.yml      # Production optimizations
├── docker-compose.override.yml  # Development overrides
├── nginx.conf                   # Frontend web server config
├── requirements.txt             # Python dependencies
├── app_with_env.py             # Modified face detection with env vars
├── init-mongo.js               # Database initialization
├── .env.example                # Environment variables template
├── README.md                   # Comprehensive documentation
└── scripts/
    ├── setup.sh                # Automated setup script
    └── backup.sh               # Backup utility
```

## 🚀 Key Features

### ✅ Camera Configuration Made Easy
- **Environment Variables**: Configure camera sources without code changes
- **Multiple Sources**: Support for USB cameras and IP camera streams
- **Fallback Support**: Try multiple camera sources in order
- **Hot Configuration**: Change camera settings via environment variables

### ✅ Production Ready
- **Resource Limits**: Memory and CPU constraints for stability
- **Health Checks**: Automatic service monitoring
- **Log Management**: Structured logging with rotation
- **Security**: Configurable passwords and JWT secrets
- **Backup Scripts**: Automated data backup utilities

### ✅ Development Friendly
- **Hot Reload**: Source code mounting for development
- **Debug Ports**: Exposed debugging interfaces
- **Override Files**: Separate dev/prod configurations
- **Easy Setup**: One-command deployment

## 🎯 Camera Configuration (Your Request)

The face detection service now reads camera sources from environment variables:

```bash
# Entry cameras
ENTRY_CAMERA_1=http://192.168.1.66:8080/video
ENTRY_CAMERA_2=1

# Exit cameras  
EXIT_CAMERA_1=0
EXIT_CAMERA_2=http://192.168.1.68:5001/video
EXIT_CAMERA_3=0
```

**No more hardcoded camera URLs!** Simply update your `.env` file and restart the service.

## 🔧 Quick Start Commands

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit camera URLs and passwords
nano .env

# 3. Run automated setup
./scripts/setup.sh

# 4. Or manual setup
docker-compose up -d

# 5. Check status
docker-compose ps

# 6. View logs
docker-compose logs -f
```

## 📊 Service Health Monitoring

All services include health checks and proper logging:
- **Frontend**: Nginx access logs
- **Backend**: API health endpoint + WebSocket status
- **Face API**: FastAPI automatic health monitoring
- **Face Detection**: Camera connection status + recognition logs
- **Database**: MongoDB connection monitoring

## 🔒 Security Features

- **Environment-based secrets**: No hardcoded passwords
- **JWT token security**: Configurable secret keys
- **Database authentication**: MongoDB user/password protection
- **Network isolation**: Services communicate via internal Docker network
- **File permissions**: Proper container user permissions

## 📈 Production Deployment

The setup includes production-specific configurations:
- **Resource limits**: Prevent memory/CPU overconsumption
- **Restart policies**: Automatic service recovery
- **Log rotation**: Prevent disk space issues
- **Health checks**: Service availability monitoring
- **Backup automation**: Data protection scripts

## 🆘 Support & Troubleshooting

Comprehensive documentation includes:
- **Common issues**: Camera problems, database connections, etc.
- **Performance tuning**: Memory optimization, GPU acceleration
- **Monitoring**: Health checks and log analysis
- **Backup/Restore**: Data protection procedures
- **Scaling**: Multi-instance deployment guidance

## 🎉 Ready to Deploy!

This Docker setup transforms your Madrasati project into a production-ready, scalable system with configurable camera sources exactly as you requested. The face detection service now reads camera configurations from environment variables, making it easy to deploy on different servers without code changes.

**Next Steps:**
1. Extract this docker-setup folder to your project
2. Configure your camera URLs in `.env`
3. Run the setup script
4. Access your application at http://localhost

Your multi-service architecture is now containerized and ready for deployment! 🚀

