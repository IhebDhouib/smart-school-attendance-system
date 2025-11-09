#!/bin/bash
# Script to check MongoDB status and create user

echo "=== Checking MongoDB Container Status ==="
docker ps | grep madrasati_mongodb

echo ""
echo "=== Checking MongoDB logs for initialization ==="
docker logs madrasati_mongodb 2>&1 | tail -20

echo ""
echo "=== Attempting to connect without authentication (if auth is disabled) ==="
docker exec -it madrasati_mongodb mongosh --eval "db.adminCommand('ping')" 2>&1 | head -5

echo ""
echo "=== Checking if MONGO_PASSWORD env variable is set ==="
grep MONGO_PASSWORD .env 2>/dev/null || echo "No .env file found or MONGO_PASSWORD not set"

echo ""
echo "=== Trying to create user directly (without auth) ==="
docker exec -i madrasati_mongodb mongosh << 'EOF'
use admin
db.createUser({
  user: "admin",
  pwd: "madrasati123",
  roles: [{role: "root", db: "admin"}]
})

use madrasati
db.createUser({
  user: "madrasati_user",
  pwd: "madrasati123",
  roles: [{role: "readWrite", db: "madrasati"}]
})

db.getUsers()
EOF

echo ""
echo "=== Done! Now try to restart MongoDB and Backend ==="
echo "docker compose restart mongodb backend"
