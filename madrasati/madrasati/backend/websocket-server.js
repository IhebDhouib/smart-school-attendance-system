const WebSocket = require("ws");
const mongoose = require("mongoose");
const winston = require("winston");
const Attendance = require("./models/Attendance");
const Student = require("./models/Student");
const Classroom = require("./models/Classroom"); // Add to validate classId

// Configure Winston logger
const logger = winston.createLogger({
  level: "debug",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: "logs/websocket-attendance.log" }),
    new winston.transports.Console(),
  ],
});

// Connect to MongoDB
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

const wss = new WebSocket.Server({ port: 3002 });

logger.info("🚀 WebSocket server started on port 3002");

// Helper function to find student by matricule
async function findStudentByMatricule(matricule) {
  try {
    const student = await Student.findOne({ matricule });
    return student;
  } catch (error) {
    logger.error("Error finding student", {
      error: error.message,
      stack: error.stack,
    });
    return null;
  }
}

wss.on("connection", (ws, req) => {
  const clientIp = req.headers["x-forwarded-for"] || req.socket.remoteAddress;
  logger.info("📱 Face recognition client connected", { clientIp });

  ws.on("message", async (message) => {
    try {
      const messageStr = message.toString();
      logger.debug("Raw WebSocket message received", {
        message: messageStr,
        clientIp,
      });

      const data = JSON.parse(messageStr);
      const { studentId, timestamp } = data;
      logger.debug("Parsed attendance data", {
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

      // Find student by matricule
      const student = await findStudentByMatricule(studentId);
      if (!student) {
        logger.warn("Student not found", { studentId, clientIp });
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
          JSON.stringify({ error: `Classroom with ID ${classId} not found` })
        );
        return;
      }

      // Parse timestamp
      const attendanceTime = new Date(timestamp);
      if (isNaN(attendanceTime.getTime())) {
        logger.warn("Invalid timestamp format", { timestamp, clientIp });
        ws.send(JSON.stringify({ error: "Invalid timestamp format" }));
        return;
      }

      // Check for duplicate attendance (same day)
      const today = new Date(attendanceTime);
      today.setHours(0, 0, 0, 0);
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);

      const existingAttendance = await Attendance.findOne({
        studentId: studentId, // Use matricule directly
        classId,
        timestamp: {
          $gte: today,
          $lt: tomorrow,
        },
      });

      if (existingAttendance) {
        logger.warn("Duplicate attendance detected", {
          studentId,
          classId,
          timestamp,
          existingAttendanceId: existingAttendance._id,
          clientIp,
        });
        ws.send(
          JSON.stringify({
            message: `Attendance already recorded for ${student.fullName} today`,
            duplicate: true,
          })
        );
        return;
      }

      // Create new attendance record
      const attendance = new Attendance({
        studentId, // Store matricule directly
        classId,
        timestamp: attendanceTime,
      });

      await attendance.save();

      logger.info("✅ Attendance recorded", {
        studentId,
        classId: classId.toString(),
        timestamp: attendanceTime,
        clientIp,
      });

      ws.send(
        JSON.stringify({
          message: `Attendance recorded for ${student.fullName}`,
          studentName: student.fullName,
          studentMatricule: student.matricule,
          className: classroom.name,
          timestamp: attendanceTime,
        })
      );
    } catch (error) {
      logger.error("❌ Error processing attendance", {
        error: error.message,
        stack: error.stack,
        message: message.toString(),
        clientIp,
      });
      ws.send(JSON.stringify({ error: "Internal server error" }));
    }
  });

  ws.on("close", () => {
    logger.info("📱 Face recognition client disconnected", { clientIp });
  });

  ws.on("error", (error) => {
    logger.error("❌ WebSocket client error", {
      error: error.message,
      stack: error.stack,
      clientIp,
    });
  });
});

wss.on("error", (error) => {
  logger.error("❌ WebSocket server error", {
    error: error.message,
    stack: error.stack,
  });
});

process.on("SIGINT", () => {
  logger.info("🛑 Shutting down WebSocket server...");
  wss.close(() => {
    mongoose.connection.close();
    process.exit(0);
  });
});
