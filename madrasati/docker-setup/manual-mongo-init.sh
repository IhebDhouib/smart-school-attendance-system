#!/bin/bash
# Manual MongoDB initialization since automatic init isn't working

echo "=== Manual MongoDB Setup ==="

echo "Step 1: Connecting to MongoDB without authentication and creating admin user..."
docker exec -i madrasati_mongodb mongosh << 'EOF'
// Create admin user first
use admin
db.createUser({
  user: "admin",
  pwd: "madrasati123",
  roles: [{role: "root", db: "admin"}]
})

// Create madrasati database user
use madrasati
db.createUser({
  user: "madrasati_user", 
  pwd: "madrasati123",
  roles: [{role: "readWrite", db: "madrasati"}]
})

// Create collections
db.createCollection("users");
db.createCollection("students");
db.createCollection("teachers");
db.createCollection("classrooms");
db.createCollection("attendance");
db.createCollection("schedules");

// Create indexes for better performance
db.users.createIndex({ email: 1 }, { unique: true });
db.students.createIndex({ matricule: 1 }, { unique: true });
db.teachers.createIndex({ teacherId: 1 }, { unique: true });
db.attendance.createIndex({ studentId: 1, timestamp: -1 });
db.schedules.createIndex({ classroomId: 1, date: 1 });

// Insert default admin user
db.users.insertOne({
  email: "admin@madrasati.com",
  passwordHash: "$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi",
  role: "admin",
  createdAt: new Date(),
  updatedAt: new Date(),
});

print("✅ Database initialized successfully!");
EOF

echo ""
echo "Step 2: Testing admin connection..."
docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin --eval "db.adminCommand('ping')"

echo ""
echo "Step 3: Verifying madrasati_user..."
docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin --eval "use madrasati; db.getUsers()"

echo ""
echo "Step 4: Restarting MongoDB to enable authentication properly..."
docker compose restart mongodb

echo ""
echo "Step 5: Waiting for MongoDB to restart..."
sleep 10

echo ""
echo "Step 6: Testing connection after restart..."
docker exec -it madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin --eval "db.adminCommand('ping')"

echo ""
echo "Step 7: Starting backend..."
docker compose up -d backend

echo ""
echo "Step 8: Checking backend logs..."
sleep 5
docker logs madrasati_backend --tail 10

echo ""
echo "=== DONE! ==="