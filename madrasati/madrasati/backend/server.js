const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const { WebSocketServer } = require("ws");
const winston = require("winston");
const teacherRoutes = require("./routes/teacherRoutes");
const authRoutes = require("./routes/authRoutes"); // ✅ Importing auth routes
const classRoutes = require("./routes/classroom");
const studentRoutes = require("./routes/student");
const scheduleRoutes = require("./routes/schedules");
const attendanceRoutes = require("./routes/attendance");
const faceEncodingRoutes = require("./routes/face-encoding");
const Attendance = require("./models/Attendance");
const ClassSchedule = require("./models/ClassSchedule");
const Student = require("./models/Student");

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
// Routes
app.use("/api/teachers", teacherRoutes);
app.use("/api/classrooms", classRoutes);
app.use("/api/students", studentRoutes);
app.use("/api/schedules", scheduleRoutes);
app.use("/api/attendance", attendanceRoutes);
app.use("/api/face-encoding", faceEncodingRoutes);
app.use("/api/auth", authRoutes); // ✅ Correctly mounted auth routes
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
        logger.error("Missing studentId or timestamp", {
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
        logger.error("Student not found", { matricule: studentId, clientIp });
        ws.send(
          JSON.stringify({
            error: `Student with matricule ${studentId} not found`,
          })
        );
        return;
      }

      // Validate timestamp format (YYYY-MM-DD HH:MM)
      const timestampRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/;
      if (!timestampRegex.test(timestamp)) {
        logger.error("Invalid timestamp format", { timestamp, clientIp });
        ws.send(
          JSON.stringify({
            error: "Invalid timestamp format. Use YYYY-MM-DD HH:MM",
          })
        );
        return;
      }

      // Parse timestamp
      const date = new Date(timestamp.replace(" ", "T") + ":00Z");
      if (isNaN(date.getTime())) {
        logger.error("Invalid timestamp value", { timestamp, clientIp });
        ws.send(JSON.stringify({ error: "Invalid timestamp value" }));
        return;
      }

      // Get day of week and time from timestamp
      const dayOfWeek = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
      ][date.getDay()];
      const currentTime = `${date.getHours().toString().padStart(2, "0")}:${date
        .getMinutes()
        .toString()
        .padStart(2, "0")}`;

      // Find active schedule
      const schedule = await ClassSchedule.findOne({
        dayOfWeek,
        startTime: { $lte: currentTime },
        endTime: { $gte: currentTime },
      }).populate("classId");

      if (!schedule) {
        logger.error("No active schedule found", {
          dayOfWeek,
          currentTime,
          timestamp,
          clientIp,
        });
        ws.send(
          JSON.stringify({
            error: "No active class schedule found for the given timestamp",
          })
        );
        return;
      }

      // Check for duplicate attendance
      const existingAttendance = await Attendance.findOne({
        studentId,
        scheduleId: schedule._id,
        timestamp: {
          $gte: new Date(date.setHours(0, 0, 0, 0)),
          $lte: new Date(date.setHours(23, 59, 59, 999)),
        },
      });
      if (existingAttendance) {
        logger.warn("Duplicate attendance detected", {
          studentId,
          scheduleId: schedule._id.toString(),
          timestamp,
          clientIp,
        });
        ws.send(
          JSON.stringify({
            error: `Attendance already recorded for student ${studentId} on this day`,
          })
        );
        return;
      }

      // Save attendance
      const attendance = new Attendance({
        studentId, // Maps to matricule
        classId: schedule.classId._id,
        scheduleId: schedule._id,
        timestamp: date,
      });
      await attendance.save();
      logger.info("Attendance recorded", {
        studentId,
        classId: schedule.classId._id.toString(),
        scheduleId: schedule._id.toString(),
        timestamp,
        clientIp,
      });

      ws.send(
        JSON.stringify({
          message: `Attendance recorded for student ${studentId}`,
        })
      );
    } catch (err) {
      logger.error("Error processing WebSocket message", {
        error: err.message,
        stack: err.stack,
        clientIp,
      });
      ws.send(JSON.stringify({ error: err.message }));
    }
  });

  ws.on("close", () => {
    logger.info("WebSocket client disconnected", { clientIp });
  });
});

// Start Express Server
app.listen(3000, () => logger.info("Express server running on port 3000"));
