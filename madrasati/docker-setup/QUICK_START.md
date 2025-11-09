# 🚀 Madrasati Quick Reference Card

## 📌 Common Commands

### Start Services

```powershell
# Development (hot-reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use script
.\deploy-production.ps1
```

### Stop Services

```powershell
docker-compose down                    # Stop all
docker-compose stop                    # Stop without removing
docker-compose restart backend         # Restart specific service
```

### View Logs

```powershell
docker-compose logs -f                 # All services
docker-compose logs -f backend         # Specific service
docker-compose logs --tail=100 backend # Last 100 lines
```

### Update Application (NO DATA LOSS!)

```powershell
git pull origin main                   # Pull code
.\deploy-production.ps1                # Deploy
```

---

## 🗄️ Database Operations

### Backup

```powershell
# Quick backup
docker exec madrasati_mongodb mongodump --out=/backup --authenticationDatabase=admin -u admin -p YourPassword

# Copy to host
docker cp madrasati_mongodb:/backup "./backups/backup-$(Get-Date -Format 'yyyy-MM-dd').dump"
```

### Restore

```powershell
# Copy to container
docker cp ./backups/backup-2024-01-15.dump madrasati_mongodb:/restore

# Restore
docker exec madrasati_mongodb mongorestore --authenticationDatabase=admin -u admin -p YourPassword /restore
```

### Access MongoDB Shell

```powershell
docker exec -it madrasati_mongodb mongosh -u admin -p YourPassword
```

---

## 📁 File Locations

### Important Files

```
.env                          # Your secrets (NEVER commit!)
docker-compose.yml            # Base config
docker-compose.dev.yml        # Dev overrides
docker-compose.prod.yml       # Prod overrides
config/nginx/nginx.conf       # Nginx config (NEVER commit!)
```

### Data Locations (Docker Volumes)

```
madrasati_mongodb_data        # Database
madrasati_face_encodings      # Face recognition data
madrasati_backend_uploads     # Uploaded files
```

---

## 🔍 Troubleshooting

### Check Service Status

```powershell
docker-compose ps                      # List all services
docker ps                              # List running containers
docker stats                           # Resource usage
```

### Debug Issues

```powershell
docker-compose logs -f backend         # Backend logs
docker-compose logs -f face-fused      # Face API logs
docker-compose logs -f mongodb         # Database logs
docker exec -it madrasati_backend sh   # Enter container
```

### Reset Everything (CAREFUL!)

```powershell
docker-compose down                    # Stop containers
docker-compose down -v                 # Stop + remove volumes (DATA LOSS!)
docker system prune -a                 # Clean everything
```

---

## 🌐 Access URLs

```
Frontend:       http://localhost
Backend API:    http://localhost:3000
Face API:       http://localhost:8000
Unknown Faces:  http://localhost:5001
Mongo Express:  http://localhost:8081
WebSocket:      ws://localhost:3001
```

---

## ⚙️ Environment Variables

### Required

```bash
MONGO_PASSWORD=...              # MongoDB password
JWT_SECRET=...                  # JWT secret (64+ chars)
CAMERA_URL=...                  # RTSP camera URL
```

### Optional

```bash
FRONTEND_PORT=80
BACKEND_HTTP_PORT=3000
FACE_API_PORT=8000
MONGO_PORT=27017
```

---

## 🔄 Git Operations

### Pull Updates (No Conflicts!)

```powershell
git pull origin main            # Always works now!
```

### Check What's Tracked

```powershell
git ls-files | Select-String ".env"    # Should be empty
git ls-files | Select-String "data"    # Should be empty
git status                             # Check changes
```

### Untrack File (if needed)

```powershell
git rm --cached path/to/file
git commit -m "chore: untrack file"
```

---

## 🚨 Emergency Commands

### Database Not Starting

```powershell
docker logs madrasati_mongodb
docker volume inspect madrasati_mongodb_data
docker exec -it madrasati_mongodb mongosh -u admin -p YourPassword
```

### Port Conflicts

```powershell
# Edit .env and change ports:
FRONTEND_PORT=8080
BACKEND_HTTP_PORT=3001
```

### Rebuild Everything

```powershell
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📊 Monitoring

### Resource Usage

```powershell
docker stats                    # Live stats
docker system df                # Disk usage
docker volume ls                # List volumes
```

### Health Checks

```powershell
# Check backend
curl http://localhost:3000/api/health

# Check MongoDB
docker exec madrasati_mongodb mongosh -u admin -p YourPassword --eval "db.adminCommand('ping')"
```

---

## 🎯 Best Practices

1. ✅ Always backup before major changes
2. ✅ Never commit `.env` file
3. ✅ Use `.\deploy-production.ps1` for updates
4. ✅ Check logs after deployment
5. ✅ Test in dev before deploying to prod

---

## 📚 Documentation

- `REFACTORING_GUIDE.md` - Detailed refactoring steps
- `README-NEW.md` - Complete usage guide
- `ACTION_PLAN.md` - Implementation checklist
- `.env.example` - All configuration options

---

## 🆘 Quick Help

**Lost database?**
→ Check volumes: `docker volume ls`

**Merge conflicts?**
→ Check `.gitignore`: `git ls-files | Select-String "conflicting-file"`

**Port in use?**
→ Edit `.env` and change port

**Can't connect to camera?**
→ Update `CAMERA_URL` in `.env`

**Slow performance?**
→ Check `docker stats` and adjust resources in `docker-compose.prod.yml`

---

**Need more help? See full docs in `README-NEW.md`**
