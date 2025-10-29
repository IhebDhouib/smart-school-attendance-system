const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const { WebSocketServer } = require("ws");
const winston = require("winston");
const authRoutes = require("./routes/authRoutes");
const classRoutes = require("./routes/classroom");
const studentRoutes = require("./routes/student");
const attendanceRoutes = require("./routes/attendance");
const faceEncodingRoutes = require("./routes/face-encoding");
const cameraRoutes = require("./routes/camera");
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
app.use(
  cors({
    origin: true, // Allow all origins
    credentials: true,
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
  })
);
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static files from uploads directory with CORS headers
app.use("/uploads", cors(), express.static("uploads"));

// Test endpoint to check photo display
app.get("/test-photo", (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head><title>Photo Test</title></head>
    <body>
      <h1>Photo Display Test</h1>
      <h2>Absolute URL:</h2>
      <img src="http://localhost:3000/uploads/1756078201070-122937191.jpg" style="max-width: 200px;" />
      <h2>Relative URL:</h2>
      <img src="/uploads/1756078201070-122937191.jpg" style="max-width: 200px;" />
      <h2>API Response Test:</h2>
      <div id="api-test"></div>
      <script>
        fetch('/api/students')
          .then(r => r.json())
          .then(students => {
            const withPhotos = students.filter(s => s.photos && s.photos.length > 0);
            const html = withPhotos.map(s => 
              '<p>' + s.fullName + ': <img src="' + s.photos[0] + '" style="max-width: 100px;" /></p>'
            ).join('');
            document.getElementById('api-test').innerHTML = html;
          });
      </script>
    </body>
    </html>
  `);
});

// Routes
app.use("/api/classrooms", classRoutes);
app.use("/api/students", studentRoutes);
app.use("/api/attendance", attendanceRoutes);
app.use("/api/face-encoding", faceEncodingRoutes);
app.use("/api/cameras", cameraRoutes);
app.use("/api/auth", authRoutes);

// MongoDB Connection
mongoose
  .connect(
    process.env.MONGODB_URI ||
      "mongodb://madrasati_user:madrasati123@mongodb:27017/madrasati",
    {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    }
  )
  .then(() => logger.info("Connected to MongoDB"))
  .catch((err) =>
    logger.error("MongoDB connection error", {
      error: err.message,
      stack: err.stack,
    })
  );

// WebSocket Server with ping/pong heartbeat
const wss = new WebSocketServer({ port: 3001 });

// Store all connected WebSocket clients
const connectedClients = new Set();

// Heartbeat interval to keep connections alive
const HEARTBEAT_INTERVAL = 30000; // 30 seconds

wss.on("connection", (ws, req) => {
  const clientIp = req.headers["x-forwarded-for"] || req.socket.remoteAddress;
  logger.info("WebSocket client connected", {
    clientIp,
    totalClients: connectedClients.size + 1,
  });

  // Add client to the set
  connectedClients.add(ws);

  // Set up heartbeat for this connection
  ws.isAlive = true;
  ws.on("pong", () => {
    ws.isAlive = true;
  });

  ws.on("message", async (message) => {
    try {
      const data = JSON.parse(message.toString());
      const { studentId, timestamp, camera_type } = data;
      logger.debug("Received attendance data", {
        studentId,
        timestamp,
        clientIp,
        camera_type,
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

      // Check for duplicate attendance (within last 30 seconds)
      const thirtySecondsAgo = new Date(date.getTime() - 30000);
      const existingAttendance = await Attendance.findOne({
        studentId: studentId,
        timestamp: { $gte: thirtySecondsAgo, $lte: date },
      });

      if (existingAttendance) {
        logger.debug("Duplicate attendance detected, skipping", {
          studentId,
          existingTimestamp: existingAttendance.timestamp,
          newTimestamp: date,
          clientIp,
        });
        ws.send(
          JSON.stringify({
            message: "Duplicate attendance detected, skipped",
            studentId,
          })
        );
        return;
      }

      // Save attendance
      const attendance = new Attendance({
        studentId, // Store matricule as string
        classId,
        timestamp: date,
        camera: camera_type,
      });
      await attendance.save();
      logger.info("Attendance recorded", {
        studentId,
        classId: classId.toString(),
        timestamp,
        clientIp,
        camera_type,
      });

      // Send confirmation to the sender
      ws.send(
        JSON.stringify({
          success: true,
          message: `Attendance recorded for student ${studentId}`,
          studentName: student.fullName,
          className: classroom.name,
          timestamp,
        })
      );

      // Broadcast to all connected clients for real-time updates
      const broadcastData = {
        type: "attendance_update",
        studentId,
        studentName: student.fullName,
        classId: classId.toString(),
        className: classroom.name,
        timestamp,
        camera_type,
      };

      connectedClients.forEach((client) => {
        if (client !== ws && client.readyState === client.OPEN) {
          try {
            client.send(JSON.stringify(broadcastData));
            logger.debug("Broadcasted attendance update to client", {
              studentId,
              classId: classId.toString(),
            });
          } catch (err) {
            logger.error("Error broadcasting to client", {
              error: err.message,
            });
            connectedClients.delete(client);
          }
        }
      });
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
    logger.info("WebSocket client disconnected", {
      clientIp,
      totalClients: connectedClients.size - 1,
    });
    // Remove client from the set
    connectedClients.delete(ws);
  });

  ws.on("error", (error) => {
    logger.error("WebSocket client error", {
      error: error.message,
      stack: error.stack,
      clientIp,
    });
    // Remove client from the set on error
    connectedClients.delete(ws);
  });
});

// Heartbeat: Send ping to all clients every 30 seconds
const heartbeatInterval = setInterval(() => {
  connectedClients.forEach((ws) => {
    if (ws.isAlive === false) {
      logger.warn("Client didn't respond to ping, terminating connection");
      connectedClients.delete(ws);
      return ws.terminate();
    }

    ws.isAlive = false;
    ws.ping();
  });
}, HEARTBEAT_INTERVAL);

// Clean up on server shutdown
wss.on("close", () => {
  clearInterval(heartbeatInterval);
});

// Start Express Server
app.listen(3000, () => logger.info("Express server running on port 3000"));
