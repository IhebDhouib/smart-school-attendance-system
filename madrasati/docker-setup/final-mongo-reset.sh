#!/bin/bash
# Complete MongoDB reset - this is the final solution

echo "=== FINAL MongoDB Reset ==="

echo "Step 1: Stopping all containers..."
docker compose down

echo ""
echo "Step 2: Removing MongoDB data completely..."
sudo rm -rf ./data/mongodb
sudo mkdir -p ./data/mongodb
sudo chmod 755 ./data/mongodb

echo ""
echo "Step 3: Removing MongoDB image to force fresh pull..."
docker rmi mongo:6.0 2>/dev/null || echo "MongoDB image not found, continuing..."

echo ""
echo "Step 4: Starting ONLY MongoDB first..."
docker compose up -d mongodb

echo ""
echo "Step 5: Waiting 20 seconds for full initialization..."
sleep 20

echo ""
echo "Step 6: Checking MongoDB logs for 'Database initialized successfully!'..."
docker logs madrasati_mongodb | grep -i "initialized\|error\|user"

echo ""
echo "Step 7: Testing admin user connection..."
if docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin --eval "db.adminCommand('ping')" 2>/dev/null; then
    echo "✅ Admin user works!"
else
    echo "❌ Admin user failed, manual creation needed..."
    
    echo "Creating admin user manually..."
    docker exec -i madrasati_mongodb mongosh << 'EOF'
use admin
db.createUser({
  user: "admin",
  pwd: "madrasati123",
  roles: [{role: "root", db: "admin"}]
})
EOF
fi

echo ""
echo "Step 8: Testing madrasati_user connection..."
if docker exec -it madrasati_mongodb mongosh -u madrasati_user -p madrasati123 --authenticationDatabase madrasati --eval "db.adminCommand('ping')" 2>/dev/null; then
    echo "✅ Madrasati user works!"
else
    echo "❌ Madrasati user failed, creating manually..."
    
    docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin << 'EOF'
use madrasati
db.createUser({
  user: "madrasati_user",
  pwd: "madrasati123",
  roles: [{role: "readWrite", db: "madrasati"}]
})

// Create collections
db.createCollection("users")
db.createCollection("students")
db.createCollection("teachers")
db.createCollection("classrooms")
db.createCollection("attendance")
db.createCollection("schedules")

// Create indexes
db.users.createIndex({ email: 1 }, { unique: true })
db.students.createIndex({ matricule: 1 }, { unique: true })
db.teachers.createIndex({ teacherId: 1 }, { unique: true })
db.attendance.createIndex({ studentId: 1, timestamp: -1 })
db.schedules.createIndex({ classroomId: 1, date: 1 })

print("✅ Madrasati database setup complete!")
EOF
fi

echo ""
echo "Step 9: Final verification..."
docker exec -it madrasati_mongodb mongosh -u madrasati_user -p madrasati123 --authenticationDatabase madrasati --eval "db.adminCommand('ping')"

echo ""
echo "Step 10: Starting backend..."
docker compose up -d backend

echo ""
echo "Step 11: Checking backend connection..."
sleep 8
docker logs madrasati_backend --tail 10

echo ""
echo "=== FINAL RESULT ==="
if docker logs madrasati_backend --tail 5 | grep -q "Connected to MongoDB"; then
    echo "🎉 SUCCESS! Backend connected to MongoDB!"
else
    echo "❌ Still failing. Check logs above."
fi