#!/bin/bash

# Madrasati Backup Script
# Creates backups of all important data

set -e

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🗄️  Creating backup in: $BACKUP_DIR"

# Backup MongoDB
echo "📊 Backing up MongoDB..."
docker exec madrasati_mongodb mongodump --out /tmp/backup
docker cp madrasati_mongodb:/tmp/backup "$BACKUP_DIR/mongodb"
echo "✅ MongoDB backup complete"

# Backup uploaded files
echo "📁 Backing up uploaded files..."
docker cp madrasati_backend:/app/uploads "$BACKUP_DIR/uploads"
echo "✅ Uploads backup complete"

# Backup face dataset
echo "👤 Backing up face dataset..."
docker cp madrasati_face_api:/app/dataset "$BACKUP_DIR/dataset"
docker cp madrasati_face_api:/app/encodings.pkl "$BACKUP_DIR/encodings.pkl" 2>/dev/null || echo "⚠️  No encodings file found"
echo "✅ Face data backup complete"

# Backup logs
echo "📝 Backing up logs..."
docker cp madrasati_face_detection:/app/logs "$BACKUP_DIR/face_logs" 2>/dev/null || echo "⚠️  No face logs found"
docker cp madrasati_backend:/app/logs "$BACKUP_DIR/backend_logs" 2>/dev/null || echo "⚠️  No backend logs found"
echo "✅ Logs backup complete"

# Create archive
echo "📦 Creating archive..."
tar -czf "$BACKUP_DIR.tar.gz" -C "./backups" "$(basename "$BACKUP_DIR")"
rm -rf "$BACKUP_DIR"

echo "🎉 Backup complete: $BACKUP_DIR.tar.gz"
echo "📊 Backup size: $(du -h "$BACKUP_DIR.tar.gz" | cut -f1)"

