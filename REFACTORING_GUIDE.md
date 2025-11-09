# 🔧 Madrasati Project - CI/CD Refactoring Guide

## 🚨 **Critical Issues Found**

Your project currently has these deployment-breaking issues:

1. ❌ **Database loss on pull**: MongoDB data in tracked `./data/mongodb` directory
2. ❌ **Merge conflicts**: Config files (`nginx.conf`, Python scripts) causing conflicts
3. ❌ **Exposed secrets**: `.env` file tracked in Git with passwords
4. ❌ **Dev/Prod mixing**: Development bind mounts in production setup
5. ❌ **No .gitignore**: Missing proper Git ignore rules

---

## ✅ **Solution Overview**

We'll implement a **4-tier configuration system**:

```
├── docker-compose.yml          # Base configuration (tracked in Git)
├── docker-compose.dev.yml      # Development overrides (tracked in Git)
├── docker-compose.prod.yml     # Production overrides (tracked in Git)
├── docker-compose.local.yml    # Personal overrides (NOT tracked - .gitignore)
├── .env.example                # Template (tracked in Git)
└── .env                        # Actual secrets (NOT tracked - .gitignore)
```

---

## 📋 **Step-by-Step Refactoring Instructions**

### **STEP 1: Backup Your Current Data** ⚠️

**DO THIS FIRST - BEFORE ANY CHANGES!**

```powershell
# Navigate to project root
cd C:\Users\ihedh\Downloads\madrasatiarabe

# Create backup directory
New-Item -ItemType Directory -Force -Path "backups\pre-refactor-$(Get-Date -Format 'yyyy-MM-dd')"

# Backup MongoDB data
Copy-Item -Recurse "madrasati\docker-setup\data" "backups\pre-refactor-$(Get-Date -Format 'yyyy-MM-dd')\data"

# Backup current .env file
Copy-Item "madrasati\docker-setup\.env" "backups\pre-refactor-$(Get-Date -Format 'yyyy-MM-dd')\.env.backup"

# Export MongoDB database (if running)
docker exec madrasati_mongodb mongodump --out=/data/db/backup --authenticationDatabase=admin -u admin -p madrasati123
```

---

### **STEP 2: Stop All Containers**

```powershell
cd madrasati\docker-setup
docker-compose down
```

---

### **STEP 3: Untrack Sensitive Files from Git**

These files should NEVER be in Git:

```powershell
# Remove .env from Git tracking (but keep local file)
git rm --cached madrasati/docker-setup/.env

# Remove data directory from Git
git rm -r --cached madrasati/docker-setup/data

# Remove any generated files
git rm -r --cached madrasati/docker-setup/__pycache__
git rm --cached madrasati/docker-setup/*.pyc
git rm -r --cached madrasati/docker-setup/unknown_faces

# Commit these changes
git commit -m "chore: untrack sensitive files and generated data"
```

---

### **STEP 4: Create Proper .gitignore Files**

I've already created these for you:
- ✅ `/.gitignore` (root level)
- ✅ `/madrasati/docker-setup/.gitignore`

**Verify they exist:**
```powershell
ls .gitignore
ls madrasati\docker-setup\.gitignore
```

---

### **STEP 5: Restructure Docker Compose Files**

#### **5.1: Create Base Configuration** (`docker-compose.yml`)

This file contains **only** what's common across ALL environments:

```powershell
# I'll create the new file in next step
```

#### **5.2: Create Development Configuration** (`docker-compose.dev.yml`)

For local development with hot-reload:

```powershell
# I'll create the new file in next step
```

#### **5.3: Create Production Configuration** (`docker-compose.prod.yml`)

Already exists - we'll update it.

---

### **STEP 6: Separate Configuration Files**

Create a `config/` directory for environment-specific configs:

```powershell
cd madrasati\docker-setup
New-Item -ItemType Directory -Force -Path "config"
New-Item -ItemType Directory -Force -Path "config\nginx"
New-Item -ItemType Directory -Force -Path "config\python"
```

Then:
1. Move `nginx.conf` → `config/nginx/nginx.conf.example` (template)
2. Copy it to `config/nginx/nginx.conf` (local override, not tracked)
3. Same for Python scripts that you modify frequently

---

### **STEP 7: Database Volume Strategy**

**Change from bind mount to named volume:**

**BEFORE (current - loses data):**
```yaml
volumes:
  - ./data/mongodb:/data/db  # ❌ Tracked in Git, gets overwritten
```

**AFTER (new - persists data):**
```yaml
volumes:
  - mongodb_data:/data/db    # ✅ Docker managed volume, persists across pulls

volumes:
  mongodb_data:
    external: true  # Created once, never deleted
    name: madrasati_mongodb_data
```

---

### **STEP 8: Environment Variables Management**

**Update `.env.example`** with all required variables (I'll do this).

**Then create your local `.env`:**
```powershell
cd madrasati\docker-setup
Copy-Item .env.example .env
# Edit .env with your actual values (this file is NOT tracked)
```

---

### **STEP 9: Handle Configuration Files That Change**

For files like `nginx.conf`, `unknown_faces_api_fastapi.py`, `faceapi.py`:

**Option A: Use templates + volume mounts (Recommended)**
```yaml
volumes:
  - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro  # Local override
```

**Option B: Use environment variables**
```python
# In Python files, replace hardcoded values:
CAMERA_URL = os.getenv('CAMERA_URL', 'default_value')
```

---

### **STEP 10: Create Docker Volume for Database**

**One-time setup** - do this before first deployment:

```powershell
# Create named volume for MongoDB
docker volume create madrasati_mongodb_data

# Create other named volumes
docker volume create madrasati_face_encodings
docker volume create madrasati_backend_uploads
docker volume create madrasati_face_unknown
docker volume create madrasati_backend_logs
docker volume create madrasati_face_logs
```

---

### **STEP 11: Restore MongoDB Data to Named Volume**

```powershell
# Start only MongoDB with new volume
docker-compose up -d mongodb

# Copy backup data to new volume
docker cp "backups\pre-refactor-$(Get-Date -Format 'yyyy-MM-dd')\data\." madrasati_mongodb:/data/db/

# Or restore from mongodump
docker exec -i madrasati_mongodb mongorestore --authenticationDatabase=admin -u admin -p madrasati123 /data/db/backup

# Restart MongoDB
docker-compose restart mongodb
```

---

### **STEP 12: Update Your Workflow**

**Development:**
```powershell
cd madrasati\docker-setup

# Start with dev overrides (hot-reload enabled)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f backend
```

**Production:**
```powershell
cd madrasati\docker-setup

# Start with prod optimizations
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use the simpler command if you set COMPOSE_FILE in .env:
docker-compose up -d
```

**Pulling Updates (NEW - No Data Loss!):**
```powershell
# 1. Pull latest code
git pull origin main

# 2. Rebuild containers (data persists in volumes!)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 3. No data loss! MongoDB volume is preserved
```

---

### **STEP 13: Commit Structure Changes**

```powershell
# Add new files
git add .gitignore
git add madrasati/docker-setup/.gitignore
git add madrasati/docker-setup/.env.example
git add madrasati/docker-setup/docker-compose.yml
git add madrasati/docker-setup/docker-compose.dev.yml
git add madrasati/docker-setup/docker-compose.prod.yml
git add madrasati/docker-setup/config/

# Commit
git commit -m "refactor: implement CI/CD-friendly structure with persistent volumes"

# Push
git push origin new-version
```

---

## 🔐 **Security Best Practices**

### **Never Commit These Files:**
- `.env` (contains passwords!)
- `data/` (database files)
- `docker-compose.local.yml` (personal overrides)
- `config/nginx/nginx.conf` (if it has IPs/secrets)
- Generated files (`*.pkl`, `__pycache__/`, `node_modules/`)

### **Always Commit These Files:**
- `.env.example` (template without secrets)
- `docker-compose.yml` (base config)
- `docker-compose.dev.yml` (dev overrides)
- `docker-compose.prod.yml` (prod overrides)
- `config/**/*.example` (config templates)

---

## 🚀 **CI/CD Pipeline Setup**

### **GitHub Actions Example** (`.github/workflows/deploy.yml`)

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Copy files to server
        uses: appleboy/scp-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          source: "."
          target: "/opt/madrasati"
      
      - name: Deploy on server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/madrasati/madrasati/docker-setup
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
            docker system prune -f
```

---

## 📊 **Volume Management Commands**

### **Backup Database:**
```powershell
# Export MongoDB to file
docker exec madrasati_mongodb mongodump --out=/backup --authenticationDatabase=admin -u admin -p $env:MONGO_PASSWORD
docker cp madrasati_mongodb:/backup "./backups/mongodb-$(Get-Date -Format 'yyyy-MM-dd').dump"
```

### **Restore Database:**
```powershell
# Restore from backup
docker cp "./backups/mongodb-2024-01-15.dump" madrasati_mongodb:/restore
docker exec madrasati_mongodb mongorestore --authenticationDatabase=admin -u admin -p $env:MONGO_PASSWORD /restore
```

### **List Volumes:**
```powershell
docker volume ls | Select-String "madrasati"
```

### **Inspect Volume:**
```powershell
docker volume inspect madrasati_mongodb_data
```

---

## 🔍 **Troubleshooting**

### **Problem: Still getting merge conflicts**
```powershell
# Check what files are tracked:
git ls-files | Select-String "nginx.conf|data|\.env"

# If they appear, untrack them:
git rm --cached <file>
git commit -m "chore: untrack config file"
```

### **Problem: Database is empty after pull**
```powershell
# Check if volume exists:
docker volume ls | Select-String "madrasati_mongodb"

# If missing, you're using bind mount - see Step 10-11
```

### **Problem: Container can't access volume**
```powershell
# Check volume permissions:
docker run --rm -v madrasati_mongodb_data:/data alpine ls -la /data
```

---

## ✅ **Verification Checklist**

After refactoring, verify:

- [ ] `.env` is in `.gitignore` and not tracked: `git ls-files | Select-String "\.env$"`
- [ ] `data/` is not tracked: `git ls-files | Select-String "data/"`
- [ ] Named volumes are created: `docker volume ls`
- [ ] Can pull without conflicts: `git pull origin main`
- [ ] Database persists after `git pull && docker-compose up -d --build`
- [ ] Environment variables load from `.env`
- [ ] Development mode works: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`
- [ ] Production mode works: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up`

---

## 📞 **Next Steps**

1. **Read this entire guide carefully**
2. **Backup your data** (Step 1)
3. **Follow steps 2-13 in order**
4. **Test thoroughly** before deploying
5. **Set up CI/CD pipeline** (optional but recommended)

---

## 📝 **Additional Files I'll Create**

I'll now create the updated Docker Compose files with proper structure. Do you want me to proceed with creating:

1. ✅ Updated `docker-compose.yml` (base)
2. ✅ Updated `docker-compose.dev.yml` (development)
3. ✅ Updated `docker-compose.prod.yml` (production)
4. ✅ Configuration templates in `config/`
5. ✅ CI/CD pipeline example

**Shall I proceed with creating these files?**
