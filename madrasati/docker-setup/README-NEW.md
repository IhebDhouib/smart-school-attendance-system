# 🏫 Madrasati Smart School Attendance System - CI/CD Ready

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [CI/CD Pipeline](#cicd-pipeline)

---

## 🎯 Overview

This is a CI/CD-friendly smart school attendance system using facial recognition. The system is now structured to:

- ✅ **Persist data** across deployments (no more database loss!)
- ✅ **Prevent merge conflicts** with proper .gitignore rules
- ✅ **Separate environments** (dev, prod, local)
- ✅ **Secure secrets** with .env files (not tracked in Git)
- ✅ **Easy updates** with `git pull && docker-compose up`

---

## 🚀 Quick Start

### First-Time Setup

1. **Clone the repository**
   ```powershell
   git clone https://github.com/IhebDhouib/smart-school-attendance-system.git
   cd smart-school-attendance-system/madrasati/docker-setup
   ```

2. **Run setup script**
   ```powershell
   .\setup.ps1
   ```

3. **Edit .env file** (IMPORTANT!)
   ```powershell
   code .env
   ```
   
   Update these values:
   - `MONGO_PASSWORD` - Strong password for MongoDB
   - `JWT_SECRET` - Random secret key (use: `openssl rand -base64 64`)
   - `CAMERA_URL` - Your RTSP camera URL

4. **Start the application**
   
   **Development (with hot-reload):**
   ```powershell
   docker-compose -f docker-compose.base.yml -f docker-compose.dev.new.yml up
   ```
   
   **Production:**
   ```powershell
   .\deploy-production.ps1
   ```
   
   Or manually:
   ```powershell
   docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml up -d
   ```

### Updating the Application

```powershell
# 1. Pull latest code
git pull origin main

# 2. Deploy (data persists automatically!)
.\deploy-production.ps1

# Or manually:
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml up -d --build
```

**No data loss!** MongoDB and all application data are stored in Docker volumes.

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Angular)                   │
│                    Port: 80 (Nginx)                     │
└─────────────────┬───────────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
┌────────▼────────┐  ┌────▼──────────────┐
│  Backend API    │  │  Face Recognition │
│  (Node.js)      │  │  (Python)         │
│  Port: 3000/1   │  │  Port: 8000/5001  │
└────────┬────────┘  └────┬──────────────┘
         │                │
         └────────┬───────┘
                  │
         ┌────────▼────────┐
         │   MongoDB       │
         │   Port: 27017   │
         └─────────────────┘
```

### Data Persistence

All data is stored in **Docker named volumes** (not bind mounts):

```
📦 Volumes:
├── madrasati_mongodb_data       # Database (NEVER deleted!)
├── madrasati_face_encodings     # Face recognition data
├── madrasati_face_dataset       # Student photos
├── madrasati_backend_uploads    # Uploaded files
├── madrasati_backend_logs       # Application logs
└── madrasati_face_logs          # Face detection logs
```

These volumes persist even when you:
- `git pull` new code
- Rebuild containers
- Update Docker images
- Delete and recreate containers

---

## ⚙️ Configuration

### File Structure

```
madrasati/docker-setup/
├── .env                           # Your secrets (NOT in Git) ⚠️
├── .env.example                   # Template (tracked in Git) ✅
├── docker-compose.base.yml        # Base config (tracked in Git) ✅
├── docker-compose.dev.new.yml     # Dev overrides (tracked in Git) ✅
├── docker-compose.prod.new.yml    # Prod overrides (tracked in Git) ✅
├── docker-compose.local.yml       # Personal overrides (NOT in Git) ⚠️
├── setup.ps1                      # Initial setup script
├── deploy-production.ps1          # Deployment script
├── config/
│   ├── nginx/
│   │   ├── nginx.conf.template    # Template (tracked in Git) ✅
│   │   └── nginx.conf             # Your config (NOT in Git) ⚠️
│   └── python/
└── backups/                       # Backups (NOT in Git) ⚠️
```

### Environment Variables

Key variables in `.env`:

```bash
# Security (CHANGE IN PRODUCTION!)
MONGO_PASSWORD=your-secure-password
JWT_SECRET=your-random-secret-key

# Camera
CAMERA_URL=rtsp://user:pass@ip:554/path

# Ports (change if conflicts)
FRONTEND_PORT=80
BACKEND_HTTP_PORT=3000
FACE_API_PORT=8000
MONGO_PORT=27017
```

---

## 🚀 Deployment

### Option 1: Automated Script (Recommended)

```powershell
.\deploy-production.ps1

# With options:
.\deploy-production.ps1 -SkipBackup  # Skip database backup
.\deploy-production.ps1 -SkipPull    # Don't git pull
.\deploy-production.ps1 -SkipBuild   # Use existing images
```

### Option 2: Manual Deployment

```powershell
# 1. Backup database (optional)
docker exec madrasati_mongodb mongodump --out=/data/db/backup

# 2. Pull latest code
git pull origin main

# 3. Stop containers
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml down

# 4. Rebuild images
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml build

# 5. Start containers
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml up -d

# 6. Verify
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml ps
```

### Development Workflow

```powershell
# Start with hot-reload
docker-compose -f docker-compose.base.yml -f docker-compose.dev.new.yml up

# Edit code - changes reflect immediately!
# Backend: Edit files in madrasati/madrasati/backend/
# Face API: Edit files in madrasati/madrasati/face/
# Frontend: Edit files in madrasati/madrasati/madrassati/

# View logs
docker-compose logs -f backend
docker-compose logs -f face-fused

# Restart a service
docker-compose restart backend
```

---

## 🔧 Troubleshooting

### Problem: Database is empty after deployment

**Solution:** Check if you're using named volumes:
```powershell
docker volume ls | Select-String "madrasati"
```

If volumes don't exist, run:
```powershell
.\setup.ps1
```

### Problem: Still getting merge conflicts

**Solution:** Untrack conflicting files:
```powershell
# Check what's tracked
git ls-files | Select-String "nginx.conf|data|\.env"

# Untrack them
git rm --cached madrasati/docker-setup/.env
git rm -r --cached madrasati/docker-setup/data
git commit -m "chore: untrack sensitive files"
```

### Problem: Can't connect to MongoDB

**Solution:** Check credentials in `.env`:
```powershell
# View MongoDB logs
docker logs madrasati_mongodb

# Test connection
docker exec -it madrasati_mongodb mongosh -u admin -p your-password
```

### Problem: Camera not working

**Solution:** Check camera access:
```powershell
# View face service logs
docker logs madrasati_face_fused

# Test camera URL
curl $env:CAMERA_URL

# Update camera URL in .env
code .env
```

### Problem: Port conflicts

**Solution:** Change ports in `.env`:
```bash
FRONTEND_PORT=8080
BACKEND_HTTP_PORT=3001
# etc.
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions (Automatic Deployment)

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that:

1. ✅ Runs tests on every push
2. ✅ Builds Docker images
3. ✅ Deploys to production server
4. ✅ Backs up database before deployment
5. ✅ Verifies health checks

### Setup GitHub Actions

1. **Add secrets to GitHub repository:**
   - `SERVER_HOST` - Your server IP/domain
   - `SERVER_USER` - SSH username
   - `SERVER_SSH_KEY` - Private SSH key
   - `SERVER_PORT` - SSH port (default: 22)
   - `MONGO_PASSWORD` - MongoDB password

2. **Push to main branch:**
   ```powershell
   git add .
   git commit -m "feat: add new feature"
   git push origin main
   ```

3. **Watch deployment in Actions tab:**
   - Go to GitHub repository → Actions tab
   - See real-time deployment progress

---

## 📊 Monitoring & Maintenance

### View Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f face-fused

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Backup Database

```powershell
# Create backup
docker exec madrasati_mongodb mongodump \
  --out=/data/db/backup-$(Get-Date -Format 'yyyy-MM-dd') \
  --authenticationDatabase=admin \
  -u admin -p $env:MONGO_PASSWORD

# Copy backup to host
docker cp madrasati_mongodb:/data/db/backup-2024-01-15 ./backups/
```

### Restore Database

```powershell
# Copy backup to container
docker cp ./backups/backup-2024-01-15 madrasati_mongodb:/data/db/

# Restore
docker exec madrasati_mongodb mongorestore \
  --authenticationDatabase=admin \
  -u admin -p $env:MONGO_PASSWORD \
  /data/db/backup-2024-01-15
```

### Clean Up

```powershell
# Remove old images
docker image prune -f

# Remove unused volumes (CAREFUL!)
docker volume prune -f

# Remove everything except volumes
docker system prune -a
```

---

## 📞 Support

- **Documentation:** See `REFACTORING_GUIDE.md` for detailed refactoring steps
- **Issues:** https://github.com/IhebDhouib/smart-school-attendance-system/issues
- **Contact:** [Your contact info]

---

## 📝 License

[Your license]

---

## 🙏 Credits

Built with ❤️ for Madrasati School
