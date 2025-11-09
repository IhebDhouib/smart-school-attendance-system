#!/bin/bash
# Complete MongoDB reset and initialization script

echo "=== Step 1: Stopping containers ==="
docker compose stop mongodb backend

echo ""
echo "=== Step 2: Removing MongoDB container ==="
docker compose rm -f mongodb

echo ""
echo "=== Step 3: Cleaning MongoDB data directory ==="
sudo rm -rf ./data/mongodb/*
sudo rm -rf ./data/mongodb/.*  2>/dev/null || true

echo ""
echo "=== Step 4: Checking init-mongo.js exists ==="
if [ -f "./init-mongo.js" ]; then
    echo "✓ init-mongo.js found"
    ls -la ./init-mongo.js
else
    echo "✗ init-mongo.js NOT FOUND!"
    exit 1
fi

echo ""
echo "=== Step 5: Starting MongoDB container (will run init script) ==="
docker compose up -d mongodb

echo ""
echo "=== Step 6: Waiting 15 seconds for MongoDB to initialize ==="
sleep 15

echo ""
echo "=== Step 7: Checking MongoDB logs for initialization ==="
docker logs madrasati_mongodb 2>&1 | grep -i "database initialized\|waiting for connections\|admin"

echo ""
echo "=== Step 8: Testing admin user connection ==="
docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin --eval "db.adminCommand('ping')"

echo ""
echo "=== Step 9: Verifying madrasati_user exists ==="
docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin --eval "use madrasati; db.getUsers()"

echo ""
echo "=== Step 10: Starting backend ==="
docker compose up -d backend

echo ""
echo "=== Step 11: Checking backend logs ==="
sleep 5
docker logs madrasati_backend --tail 20

echo ""
echo "=== DONE! ==="
echo "If you see 'Connected to MongoDB' in the backend logs, everything is working!"
