#!/bin/bash
# Diagnostic and fix script for MongoDB issues

echo "=== MongoDB Diagnostics and Fix ==="

echo "Step 1: Checking if MongoDB container is running..."
docker ps | grep madrasati_mongodb

echo ""
echo "Step 2: Checking MongoDB logs for errors..."
echo "--- Recent MongoDB logs ---"
docker logs madrasati_mongodb --tail 20

echo ""
echo "Step 3: Trying to connect without authentication..."
docker exec -it madrasati_mongodb mongosh --eval "db.adminCommand('ping')" 2>&1

echo ""
echo "Step 4: Checking if any users exist in admin database..."
docker exec -it madrasati_mongodb mongosh --eval "use admin; db.getUsers()" 2>&1

echo ""
echo "Step 5: Checking if madrasati database exists..."
docker exec -it madrasati_mongodb mongosh --eval "show dbs" 2>&1

echo ""
echo "Step 6: If no users exist, creating them now..."
docker exec -i madrasati_mongodb mongosh << 'EOF'
try {
  // Switch to admin database
  use admin
  
  // Try to create admin user (will fail if exists)
  try {
    db.createUser({
      user: "admin",
      pwd: "madrasati123", 
      roles: [{role: "root", db: "admin"}]
    })
    print("✅ Admin user created successfully")
  } catch(e) {
    print("⚠️  Admin user might already exist: " + e.message)
  }
  
  // Switch to madrasati database
  use madrasati
  
  // Try to create madrasati_user
  try {
    db.createUser({
      user: "madrasati_user",
      pwd: "madrasati123",
      roles: [{role: "readWrite", db: "madrasati"}]
    })
    print("✅ Madrasati user created successfully")
  } catch(e) {
    print("⚠️  Madrasati user might already exist: " + e.message)
  }
  
  // Create collections if they don't exist
  db.createCollection("users");
  db.createCollection("students");
  db.createCollection("teachers");
  db.createCollection("classrooms");
  db.createCollection("attendance");
  db.createCollection("schedules");
  
  print("✅ Collections created/verified")
  
} catch(error) {
  print("❌ Error during setup: " + error.message)
}
EOF

echo ""
echo "Step 7: Testing admin authentication..."
docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin --eval "db.adminCommand('ping')" 2>&1

echo ""
echo "Step 8: Testing madrasati_user authentication..."
docker exec -it madrasati_mongodb mongosh -u madrasati_user -p madrasati123 --authenticationDatabase madrasati --eval "db.adminCommand('ping')" 2>&1

echo ""
echo "Step 9: Verifying users exist..."
docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin --eval "use madrasati; db.getUsers()" 2>&1

echo ""
echo "Step 10: Restarting backend to test connection..."
docker compose restart backend

echo ""
echo "Step 11: Waiting and checking backend logs..."
sleep 8
docker logs madrasati_backend --tail 15

echo ""
echo "=== Diagnostic Complete ==="
echo "If you still see authentication errors, the issue might be:"
echo "1. Environment variable MONGO_PASSWORD is set differently"
echo "2. Backend is using a different connection string"
echo "3. MongoDB needs to be completely rebuilt"