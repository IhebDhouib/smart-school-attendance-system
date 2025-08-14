const express = require("express");
const router = express.Router();
const multer = require("multer");
const xlsx = require("xlsx");
const winston = require("winston");
const ClassSchedule = require("../models/ClassSchedule");
const Classroom = require("../models/Classroom");

// Configure Winston logger
const logger = winston.createLogger({
  level: "debug",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: "logs/schedule-upload.log" }),
    new winston.transports.Console(),
  ],
});

// Configure Multer for file uploads
const upload = multer({ storage: multer.memoryStorage() });

// Upload class schedule
router.post("/upload", upload.single("file"), async (req, res) => {
  logger.info("Received POST request to /api/schedules/upload", {
    method: req.method,
    url: req.url,
    body: req.body,
    file: req.file
      ? { originalname: req.file.originalname, size: req.file.size }
      : "No file",
  });

  try {
    // Validate inputs
    logger.debug("Validating request inputs");
    if (!req.file || !req.body.className || !req.body.grade) {
      logger.error("Missing required inputs", {
        className: req.body.className,
        grade: req.body.grade,
        file: !!req.file,
      });
      return res
        .status(400)
        .json({ error: "Class name, grade, and Excel file are required" });
    }

    // Fetch classId by className and grade
    logger.debug("Fetching classroom", {
      className: req.body.className,
      grade: req.body.grade,
    });
    const classroom = await Classroom.findOne({
      name: req.body.className,
      grade: req.body.grade,
    });
    if (!classroom) {
      logger.error("Classroom not found", {
        className: req.body.className,
        grade: req.body.grade,
      });
      return res.status(404).json({
        error: `Classroom with name ${req.body.className} and grade ${req.body.grade} not found`,
      });
    }
    const classId = classroom._id;
    logger.debug("Classroom found", { classId: classId.toString() });

    // Parse Excel file
    logger.debug("Parsing Excel file");
    let workbook;
    try {
      workbook = xlsx.read(req.file.buffer, { type: "buffer" });
    } catch (parseErr) {
      logger.error("Failed to parse Excel file", { error: parseErr.message });
      return res.status(400).json({ error: "Invalid Excel file format" });
    }
    const sheetName = workbook.SheetNames[0];
    if (!sheetName) {
      logger.error("Excel file has no sheets");
      return res.status(400).json({ error: "Excel file is empty or invalid" });
    }
    const sheet = workbook.Sheets[sheetName];
    const data = xlsx.utils.sheet_to_json(sheet);
    logger.debug("Excel file parsed", { rowCount: data.length });

    // Validate and transform data
    logger.debug("Validating Excel data");
    const schedules = data.map((row, index) => {
      if (
        !row.subject ||
        !row.dayOfWeek ||
        !row.startTime ||
        !row.endTime ||
        !row.teacherId
      ) {
        logger.error("Missing required fields in Excel row", {
          row: index + 2,
          data: row,
        });
        throw new Error(`Missing required fields in row ${index + 2}`);
      }
      if (
        ![
          "Monday",
          "Tuesday",
          "Wednesday",
          "Thursday",
          "Friday",
          "Saturday",
        ].includes(row.dayOfWeek)
      ) {
        logger.error("Invalid dayOfWeek in Excel row", {
          row: index + 2,
          dayOfWeek: row.dayOfWeek,
        });
        throw new Error(
          `Invalid dayOfWeek in row ${index + 2}: ${row.dayOfWeek}`
        );
      }
      if (
        !/^([0-1][0-9]|2[0-3]):[0-5][0-9]$/.test(row.startTime) ||
        !/^([0-1][0-9]|2[0-3]):[0-5][0-9]$/.test(row.endTime)
      ) {
        logger.error("Invalid time format in Excel row", {
          row: index + 2,
          startTime: row.startTime,
          endTime: row.endTime,
        });
        throw new Error(`Invalid time format in row ${index + 2}. Use HH:mm`);
      }
      return {
        classId,
        teacherId: row.teacherId,
        subject: row.subject,
        dayOfWeek: row.dayOfWeek,
        startTime: row.startTime,
        endTime: row.endTime,
      };
    });
    logger.debug("Excel data validated", { scheduleCount: schedules.length });

    // Clear existing schedules for the class
    logger.debug("Clearing existing schedules", {
      classId: classId.toString(),
    });
    const deleteResult = await ClassSchedule.deleteMany({ classId });
    logger.debug("Existing schedules cleared", {
      deletedCount: deleteResult.deletedCount,
    });

    // Insert new schedules
    logger.debug("Inserting new schedules");
    const createdSchedules = await ClassSchedule.insertMany(schedules);
    logger.info("Schedules uploaded successfully", {
      scheduleCount: createdSchedules.length,
      classId: classId.toString(),
    });

    res.status(201).json({
      message: "Schedules uploaded successfully",
      data: createdSchedules,
    });
  } catch (err) {
    logger.error("Unexpected error in schedule upload", {
      error: err.message,
      stack: err.stack,
    });
    res.status(400).json({ error: err.message });
  }
});

module.exports = router;


// Get schedules by class ID
router.get("/class/:classId", async (req, res) => {
  try {
    const { classId } = req.params;
    const schedules = await ClassSchedule.find({ classId });
    res.status(200).json(schedules);
  } catch (error) {
    console.error("Error fetching schedules by class ID:", error);
    res.status(500).json({ message: "Server error" });
  }
});


