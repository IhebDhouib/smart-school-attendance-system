// routes/attendance.js
const express = require("express");
const util = require("util");
const router = express.Router();
const Attendance = require("../models/Attendance");
const Student = require("../models/Student");
const Classroom = require("../models/Classroom");

// helper pour logs détaillés
function dbg(title, obj) {
  try {
    console.log(`\n--- ${new Date().toISOString()} - ${title} ---`);
    if (obj === undefined) {
      console.log("undefined");
    } else if (typeof obj === "string") {
      console.log(obj);
    } else {
      console.log(util.inspect(obj, { depth: null, colors: false }));
    }
    console.log(`--- end ${title} ---\n`);
  } catch (e) {
    console.error("dbg error", e);
  }
}

// GET all attendance
router.get("/", async (req, res) => {
  dbg("REQ GET /api/attendance - query", req.query);
  try {
    const attendanceRecords = await Attendance.find()
      .populate("classId", "name grade")
      .sort({ timestamp: -1 });

    dbg("Found attendanceRecords count", attendanceRecords.length);
    res.json(attendanceRecords);
  } catch (error) {
    dbg("Error fetching attendance records", {
      message: error.message,
      stack: error.stack,
    });
    res.status(500).json({
      message: "Error fetching attendance records",
      error: error.message,
    });
  }
});

// Get attendance summary for a class on a specific date
router.get("/class/:classId", async (req, res) => {
  dbg("REQ GET /api/attendance/class/:classId - params+query", {
    params: req.params,
    query: req.query,
  });
  try {
    const { classId } = req.params;
    const { date } = req.query;

    let query = { classId };

    if (date) {
      const startDate = new Date(date);
      const endDate = new Date(date);
      endDate.setDate(endDate.getDate() + 1);
      query.timestamp = { $gte: startDate, $lt: endDate };
    }

    dbg("Mongo query for attendanceRecords", query);
    const attendanceRecords = await Attendance.find(query).sort({
      timestamp: -1,
    });

    dbg(
      "attendanceRecords found (sample first item)",
      attendanceRecords[0] ?? "no records"
    );

    const allStudents = await Student.find({ classId });
    dbg("allStudents for class", {
      count: allStudents.length,
      sample: allStudents[0] ?? null,
    });

    const attendanceSummary = allStudents.map((student) => {
      const attendanceRecord = attendanceRecords.find(
        (rec) => rec.studentId === student.matricule
      );
      return {
        studentId: student.matricule,
        fullName: student.fullName,
        nomPere: student.nomPere,
        isPresent: !!attendanceRecord,
        timestamp: attendanceRecord ? attendanceRecord.timestamp : null,
        attendanceId: attendanceRecord ? attendanceRecord._id : null,
      };
    });

    const classInfo = await Classroom.findById(classId);
    res.json({
      classInfo,
      attendanceSummary,
      totalStudents: allStudents.length,
      presentStudents: attendanceSummary.filter((s) => s.isPresent).length,
      absentStudents: attendanceSummary.filter((s) => !s.isPresent).length,
    });
  } catch (error) {
    dbg("Error fetching class attendance", {
      message: error.message,
      stack: error.stack,
      params: req.params,
      query: req.query,
    });
    res.status(500).json({
      message: "Error fetching class attendance",
      error: error.message,
    });
  }
});

// Get a student's attendance records during a period
router.get("/student/:matricule", async (req, res) => {
  dbg("REQ GET /api/attendance/student/:matricule", {
    params: req.params,
    query: req.query,
  });
  try {
    const { matricule } = req.params;
    const { startDate, endDate, classId } = req.query;

    let query = { studentId: matricule };

    if (startDate || endDate) {
      const start = startDate ? new Date(startDate) : new Date(0);
      const end = endDate ? new Date(endDate + "T23:59:59.999Z") : new Date();
      query.timestamp = { $gte: start, $lte: end };
    }

    if (classId) query.classId = classId;

    dbg("Mongo query for student records", query);
    const records = await Attendance.find(query).sort({ timestamp: -1 });

    dbg("Found records count", records.length);
    res.json(records);
  } catch (error) {
    dbg("Error fetching student attendance", {
      message: error.message,
      stack: error.stack,
      params: req.params,
      query: req.query,
    });
    res.status(500).json({
      message: "Error fetching student attendance",
      error: error.message,
    });
  }
});

// Get attendance by date range
router.get("/date-range", async (req, res) => {
  dbg("REQ GET /api/attendance/date-range", req.query);
  try {
    const { startDate, endDate, classId } = req.query;
    if (!startDate || !endDate) {
      dbg("Missing startDate or endDate in date-range request", req.query);
      return res
        .status(400)
        .json({ message: "startDate and endDate are required" });
    }

    const query = {
      timestamp: {
        $gte: new Date(startDate),
        $lte: new Date(endDate + "T23:59:59.999Z"),
      },
    };
    if (classId) query.classId = classId;

    dbg("Mongo query date-range", query);
    const attendanceRecords = await Attendance.find(query).sort({
      timestamp: -1,
    });
    dbg("attendanceRecords date-range count", attendanceRecords.length);
    res.json(attendanceRecords);
  } catch (error) {
    dbg("Error fetching attendance by date range", {
      message: error.message,
      stack: error.stack,
      query: req.query,
    });
    res.status(500).json({
      message: "Error fetching attendance by date range",
      error: error.message,
    });
  }
});

// Create attendance
router.post("/", async (req, res) => {
  dbg("REQ POST /api/attendance", { headers: req.headers, body: req.body });
  try {
    const { studentId, classId } = req.body;

    // validation basique
    if (!studentId || !classId) {
      dbg("Validation failed - missing studentId or classId", req.body);
      return res
        .status(400)
        .json({ message: "studentId and classId are required" });
    }

    // vérifier que l'étudiant existe (par matricule) — logguer le résultat
    const student = await Student.findOne({ matricule: studentId });
    dbg("Student lookup result", student ?? "NOT FOUND");

    // vérifier que la classe existe
    const classroom = await Classroom.findById(classId);
    dbg("Classroom lookup result", classroom ?? "NOT FOUND");

    if (!student) {
      dbg("Student not found - abort create", { studentId, classId });
      return res.status(404).json({ message: "Student not found" });
    }
    if (!classroom) {
      dbg("Class not found - abort create", { studentId, classId });
      return res.status(404).json({ message: "Classroom not found" });
    }

    // Prevent duplicate for same student/class same day
    const today = new Date();
    const startOfDay = new Date(
      today.getFullYear(),
      today.getMonth(),
      today.getDate()
    );
    const endOfDay = new Date(
      today.getFullYear(),
      today.getMonth(),
      today.getDate() + 1
    );

    const existingQuery = {
      studentId,
      classId,
      timestamp: { $gte: startOfDay, $lt: endOfDay },
    };
    dbg("Check existing attendance query", existingQuery);

    const existing = await Attendance.findOne(existingQuery);
    dbg("Existing attendance query result", existing ?? "NONE");

    if (existing) {
      dbg("Attendance already exists for today - returning 400", existing._id);
      return res.status(400).json({
        message: "Attendance already recorded for this student today",
      });
    }

    // create attendance (log the to-be-saved doc)
    const attendance = new Attendance({ studentId, classId });
    dbg("Attendance document to save", attendance);

    const saved = await attendance.save();
    dbg("Attendance saved", saved);

    // optional populate saved doc for response
    const populated = await Attendance.findById(saved._id).populate(
      "classId",
      "name grade"
    );
    dbg("Populated saved attendance", populated);

    res.status(201).json(populated || saved);
  } catch (error) {
    // log error detail + request context
    dbg("Error creating attendance record", {
      message: error.message,
      stack: error.stack,
      reqBody: req.body,
      params: req.params,
      query: req.query,
    });
    // return full error message (ou un message générique selon ta politique)
    res.status(500).json({
      message: "Error creating attendance record",
      error: error.message,
    });
  }
});

// Get current status for a class (present/absent based on any detection today)
router.get("/class/:classId/current-status", async (req, res) => {
  dbg("REQ GET /api/attendance/class/:classId/current-status", req.params);
  try {
    const { classId } = req.params;

    // Get all students for the class
    const allStudents = await Student.find({ classId });
    dbg("allStudents for current status", { count: allStudents.length });

    // Get today's date range (start and end of day)
    const today = new Date();
    const startOfDay = new Date(
      today.getFullYear(),
      today.getMonth(),
      today.getDate()
    );
    const endOfDay = new Date(
      today.getFullYear(),
      today.getMonth(),
      today.getDate() + 1
    );

    dbg("Date range for today's attendance check", {
      today: today.toISOString(),
      startOfDay: startOfDay.toISOString(),
      endOfDay: endOfDay.toISOString(),
      classId,
      todayLocalString: today.toLocaleDateString(),
      startOfDayLocalString: startOfDay.toLocaleDateString(),
    });

    const statusSummary = await Promise.all(
      allStudents.map(async (student) => {
        // Check if student has ANY attendance record for today
        const todayRecord = await Attendance.findOne({
          studentId: student.matricule,
          timestamp: {
            $gte: startOfDay,
            $lt: endOfDay,
          },
        }).sort({ timestamp: -1 }); // Get the latest record of today

        // Debug: Check what records exist for this student (any date)
        const allRecordsForStudent = await Attendance.find({
          studentId: student.matricule,
        })
          .sort({ timestamp: -1 })
          .limit(3);

        dbg(
          `Student ${student.matricule} (${student.fullName}) attendance check`,
          {
            matricule: student.matricule,
            todayRecord: todayRecord
              ? {
                  id: todayRecord._id,
                  timestamp: todayRecord.timestamp,
                  timestampISO: todayRecord.timestamp.toISOString(),
                }
              : null,
            recentRecords: allRecordsForStudent.map((r) => ({
              id: r._id,
              timestamp: r.timestamp,
              timestampISO: r.timestamp.toISOString(),
            })),
            dateRange: {
              startOfDay: startOfDay.toISOString(),
              endOfDay: endOfDay.toISOString(),
            },
          }
        );

        // Student is present if they have any detection today (entry OR exit)
        const isPresent = todayRecord !== null;

        return {
          studentId: student.matricule,
          fullName: student.fullName,
          nomPere: student.nomPere,
          isPresent: isPresent,
          timestamp: todayRecord ? todayRecord.timestamp : null,
          attendanceId: todayRecord ? todayRecord._id : null,
          lastCamera: todayRecord ? todayRecord.camera : null,
        };
      })
    );

    const classInfo = await Classroom.findById(classId);
    res.json({
      classInfo: classInfo
        ? { name: classInfo.name, grade: classInfo.grade }
        : null,
      attendanceSummary: statusSummary,
      totalStudents: allStudents.length,
      presentCount: statusSummary.filter((s) => s.isPresent).length,
      absentCount: statusSummary.filter((s) => !s.isPresent).length,
    });

    dbg("Current status response", {
      totalStudents: allStudents.length,
      presentCount: statusSummary.filter((s) => s.isPresent).length,
      absentCount: statusSummary.filter((s) => !s.isPresent).length,
      dateRange: { startOfDay, endOfDay },
    });
  } catch (error) {
    dbg("Error fetching current status", {
      message: error.message,
      stack: error.stack,
    });
    res.status(500).json({
      message: "Error fetching current status",
      error: error.message,
    });
  }
});

// Delete attendance by id
router.delete("/:id", async (req, res) => {
  dbg("REQ DELETE /api/attendance/:id", req.params);
  try {
    const deleted = await Attendance.findByIdAndDelete(req.params.id);
    if (!deleted) {
      dbg("Delete attendance - not found", req.params.id);
      return res.status(404).json({ message: "Not found" });
    }
    dbg("Deleted attendance", deleted._id);
    res.json({ message: "Deleted" });
  } catch (error) {
    dbg("Error deleting attendance record", {
      message: error.message,
      stack: error.stack,
      params: req.params,
    });
    res.status(500).json({
      message: "Error deleting attendance record",
      error: error.message,
    });
  }
});

module.exports = router;
