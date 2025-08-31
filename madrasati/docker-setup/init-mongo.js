// MongoDB initialization script for Madrasati
db = db.getSiblingDB("madrasati");

// Create collections
db.createCollection("users");
db.createCollection("students");
db.createCollection("teachers");
db.createCollection("classrooms");
db.createCollection("attendance");
db.createCollection("schedules");

// Create indexes for better performance
db.users.createIndex({ email: 1 }, { unique: true });
db.students.createIndex({ studentId: 1 }, { unique: true });
db.teachers.createIndex({ teacherId: 1 }, { unique: true });
db.attendance.createIndex({ studentId: 1, timestamp: -1 });
db.schedules.createIndex({ classroomId: 1, date: 1 });

// Insert default admin user (optional)
db.users.insertOne({
  email: "admin@madrasati.com",
  passwordHash: "$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi", // password: "password"
  role: "admin",
  createdAt: new Date(),
  updatedAt: new Date(),
});

print("Database initialized successfully!");
