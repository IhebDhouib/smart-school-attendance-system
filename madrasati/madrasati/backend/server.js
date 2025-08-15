const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const { WebSocketServer } = require("ws");
const winston = require("winston");
const teacherRoutes = require("./routes/teacherRoutes");
const authRoutes = require("./routes/authRoutes");
const classRoutes = require("./routes/classroom");
const studentRoutes = require("./routes/student");
const scheduleRoutes = require("./routes/schedules");
const attendanceRoutes = require("./routes/attendance");
const faceEncodingRoutes = require("./routes/face-encoding");
const Attendance = require("./models/Attendance");
const Student = require("./models/Student");
const Classroom = require("./models/Classroom"); // Ensure Classroom is imported

// Configure Winston logger
const logger = winston.createLogger({
  level: "debug",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: "logs/attendance.log" }),
    new winston.transports.Console(),
  ],
});

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.use("/api/teachers", teacherRoutes);
app.use("/api/classrooms", classRoutes);
app.use("/api/students", studentRoutes);
app.use("/api/schedules", scheduleRoutes); // Kept for compatibility, but not used in WebSocket
app.use("/api/attendance", attendanceRoutes);
app.use("/api/face-encoding", faceEncodingRoutes);
app.use("/api/auth", authRoutes);

// MongoDB Connection
mongoose
  .connect("mongodb://localhost:27017/madrasati", {
    useNewUrlParser: true,
    useUnifiedTopology: true,
  })
  .then(() => logger.info("Connected to MongoDB"))
  .catch((err) =>
    logger.error("MongoDB connection error", {
      error: err.message,
      stack: err.stack,
    })
  );

// WebSocket Server
const wss = new WebSocketServer({ port: 3001 });

wss.on("connection", (ws, req) => {
  const clientIp = req.headers["x-forwarded-for"] || req.socket.remoteAddress;
  logger.info("WebSocket client connected", { clientIp });

  ws.on("message", async (message) => {
    try {
      const data = JSON.parse(message.toString());
      const { studentId, timestamp } = data;
      logger.debug("Received attendance data", {
        studentId,
        timestamp,
        clientIp,
      });

      // Validate inputs
      if (!studentId || !timestamp) {
        logger.warn("Missing studentId or timestamp", {
          studentId,
          timestamp,
          clientIp,
        });
        ws.send(
          JSON.stringify({ error: "studentId and timestamp are required" })
        );
        return;
      }

      // Validate studentId against matricule in Student collection
      const student = await Student.findOne({ matricule: studentId });
      if (!student) {
        logger.warn("Student not found", { matricule: studentId, clientIp });
        ws.send(
          JSON.stringify({
            error: `Student with matricule ${studentId} not found`,
          })
        );
        return;
      }

      // Get classId from student
      const classId = student.classId;
      logger.debug("Retrieved classId from student", {
        studentId,
        classId: classId.toString(),
        clientIp,
      });

      // Validate classId
      const classroom = await Classroom.findById(classId);
      if (!classroom) {
        logger.warn("Classroom not found", { classId, clientIp });
        ws.send(
          JSON.stringify({
            error: `Classroom with ID ${classId} not found`,
          })
        );
        return;
      }

      // Validate timestamp format (YYYY-MM-DD HH:MM)
      const timestampRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/;
      if (!timestampRegex.test(timestamp)) {
        logger.warn("Invalid timestamp format", { timestamp, clientIp });
        ws.send(
          JSON.stringify({
            error: "Invalid timestamp format. Use YYYY-MM-DD HH:MM",
          })
        );
        return;
      }

      // Parse timestamp
      const date = new Date(timestamp.replace(" ", "T") + ":00");
      if (isNaN(date.getTime())) {
        logger.warn("Invalid timestamp value", { timestamp, clientIp });
        ws.send(JSON.stringify({ error: "Invalid timestamp value" }));
        return;
      }

      // Check for duplicate attendance




      // Save attendance
      const attendance = new Attendance({
        studentId, // Store matricule as string
        classId,
        timestamp: date,
      });
      await attendance.save();
      logger.info("Attendance recorded", {
        studentId,
        classId: classId.toString(),
        timestamp,
        clientIp,
      });

      ws.send(
        JSON.stringify({
          message: `Attendance recorded for student ${studentId}`,
          studentName: student.fullName,
          className: classroom.name,
          timestamp,
        })
      );
    } catch (err) {
      logger.error("Error processing WebSocket message", {
        error: err.message,
        stack: err.stack,
        clientIp,
      });
      ws.send(
        JSON.stringify({ error: "Internal server error", details: err.message })
      );
    }
  });

  ws.on("close", () => {
    logger.info("WebSocket client disconnected", { clientIp });
  });

  ws.on("error", (error) => {
    logger.error("WebSocket client error", {
      error: error.message,
      stack: error.stack,
      clientIp,
    });
  });
});

// Start Express Server
app.listen(3000, () => logger.info("Express server running on port 3000"));
