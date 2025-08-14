const express = require('express');
const router = express.Router();
const Attendance = require('../models/Attendance');
const Student = require('../models/Student');
const Classroom = require('../models/Classroom');
const ClassSchedule = require('../models/ClassSchedule');

// Get all attendance records
router.get('/', async (req, res) => {
  try {
    const attendanceRecords = await Attendance.find()
      .populate('classId', 'name grade')
      .populate('scheduleId', 'subject dayOfWeek startTime endTime')
      .sort({ timestamp: -1 });
    
    res.json(attendanceRecords);
  } catch (error) {
    console.error('Error fetching attendance records:', error);
    res.status(500).json({ message: 'Error fetching attendance records', error: error.message });
  }
});

// Get attendance records by class ID
router.get('/class/:classId', async (req, res) => {
  try {
    const { classId } = req.params;
    const { date, scheduleId } = req.query;

    // Build query
    let query = { classId };
    
    if (scheduleId) {
      query.scheduleId = scheduleId;
    }
    
    if (date) {
      const startDate = new Date(date);
      const endDate = new Date(date);
      endDate.setDate(endDate.getDate() + 1);
      query.timestamp = { $gte: startDate, $lt: endDate };
    }

    const attendanceRecords = await Attendance.find(query)
      .populate('classId', 'name grade')
      .populate('scheduleId', 'subject dayOfWeek startTime endTime')
      .sort({ timestamp: -1 });

    // Get all students in the class
    const allStudents = await Student.find({ classId });
    
    // Create attendance summary with all students
    const attendanceSummary = allStudents.map(student => {
      const attendanceRecord = attendanceRecords.find(record => record.studentId === student.matricule);
      return {
        studentId: student.matricule,
        fullName: student.fullName,
        nomPere: student.nomPere,
        isPresent: !!attendanceRecord,
        timestamp: attendanceRecord ? attendanceRecord.timestamp : null,
        attendanceId: attendanceRecord ? attendanceRecord._id : null
      };
    });

    res.json({
      classInfo: attendanceRecords.length > 0 ? attendanceRecords[0].classId : await Classroom.findById(classId),
      scheduleInfo: attendanceRecords.length > 0 && attendanceRecords[0].scheduleId ? attendanceRecords[0].scheduleId : null,
      attendanceSummary,
      totalStudents: allStudents.length,
      presentStudents: attendanceSummary.filter(s => s.isPresent).length,
      absentStudents: attendanceSummary.filter(s => !s.isPresent).length
    });
  } catch (error) {
    console.error('Error fetching class attendance:', error);
    res.status(500).json({ message: 'Error fetching class attendance', error: error.message });
  }
});

// Get attendance records by date range
router.get("/date-range", async (req, res) => {
  try {
    const { startDate, endDate, classId, scheduleId } = req.query;

    // Validate required parameters
    if (!startDate || !endDate) {
      return res.status(400).json({
        message: "startDate and endDate are required parameters",
      });
    }

    let query = {};

    // Add date range filter
    query.timestamp = {
      $gte: new Date(startDate),
      $lte: new Date(endDate + "T23:59:59.999Z"), // Include the entire end date
    };

    // Add class filter if provided
    if (classId) {
      query.classId = classId;
    }

    // Add schedule/subject filter if provided
    if (scheduleId) {
      query.scheduleId = scheduleId;
    }

    console.log("Query parameters:", {
      startDate,
      endDate,
      classId,
      scheduleId,
    });
    console.log("MongoDB query:", query);

    const attendanceRecords = await Attendance.find(query)
      .populate("classId", "name grade")
      .populate("scheduleId", "subject dayOfWeek startTime endTime")
      .populate("studentId", "name email studentNumber") // Add student info
      .sort({ timestamp: -1 });

    console.log(`Found ${attendanceRecords.length} attendance records`);

    res.json(attendanceRecords);
  } catch (error) {
    console.error("Error fetching attendance by date range:", error);
    res.status(500).json({
      message: "Error fetching attendance by date range",
      error: error.message,
    });
  }
});

// Get attendance statistics for a class
router.get('/stats/:classId', async (req, res) => {
  try {
    const { classId } = req.params;
    const { startDate, endDate } = req.query;
    
    let dateQuery = {};
    if (startDate && endDate) {
      dateQuery = {
        timestamp: {
          $gte: new Date(startDate),
          $lte: new Date(endDate)
        }
      };
    }

    // Get total students in class
    const totalStudents = await Student.countDocuments({ classId });
    
    // Get attendance records for the class
    const attendanceRecords = await Attendance.find({ 
      classId, 
      ...dateQuery 
    }).populate('scheduleId', 'subject dayOfWeek startTime endTime');
    
    // Group by date and schedule
    const attendanceByDate = {};
    attendanceRecords.forEach(record => {
      const date = record.timestamp.toISOString().split('T')[0];
      const scheduleKey = record.scheduleId ? record.scheduleId._id.toString() : 'no-schedule';
      
      if (!attendanceByDate[date]) {
        attendanceByDate[date] = {};
      }
      
      if (!attendanceByDate[date][scheduleKey]) {
        attendanceByDate[date][scheduleKey] = {
          present: 0,
          scheduleInfo: record.scheduleId,
          students: []
        };
      }
      
      attendanceByDate[date][scheduleKey].present++;
      attendanceByDate[date][scheduleKey].students.push(record.studentId);
    });

    // Calculate statistics
    const stats = {
      totalStudents,
      attendanceByDate,
      overallStats: {
        totalDays: Object.keys(attendanceByDate).length,
        averageAttendance: 0
      }
    };

    // Calculate average attendance
    let totalPresent = 0;
    let totalPossible = 0;
    Object.values(attendanceByDate).forEach(dateData => {
      Object.values(dateData).forEach(scheduleData => {
        totalPresent += scheduleData.present;
        totalPossible += totalStudents;
      });
    });
    
    if (totalPossible > 0) {
      stats.overallStats.averageAttendance = (totalPresent / totalPossible) * 100;
    }

    res.json(stats);
  } catch (error) {
    console.error('Error fetching attendance statistics:', error);
    res.status(500).json({ message: 'Error fetching attendance statistics', error: error.message });
  }
});

// Create new attendance record
router.post('/', async (req, res) => {
  try {
    const { studentId, classId, scheduleId } = req.body;
    
    // Check if attendance already exists for this student, class, and schedule today
    const today = new Date();
    const startOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const endOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
    
    const existingAttendance = await Attendance.findOne({
      studentId,
      classId,
      scheduleId,
      timestamp: { $gte: startOfDay, $lt: endOfDay }
    });
    
    if (existingAttendance) {
      return res.status(400).json({ message: 'Attendance already recorded for this student today' });
    }
    
    const attendance = new Attendance({
      studentId,
      classId,
      scheduleId
    });
    
    await attendance.save();
    
    const populatedAttendance = await Attendance.findById(attendance._id)
      .populate('classId', 'name grade')
      .populate('scheduleId', 'subject dayOfWeek startTime endTime');
    
    res.status(201).json(populatedAttendance);
  } catch (error) {
    console.error('Error creating attendance record:', error);
    res.status(500).json({ message: 'Error creating attendance record', error: error.message });
  }
});

// Delete attendance record
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const deletedAttendance = await Attendance.findByIdAndDelete(id);
    
    if (!deletedAttendance) {
      return res.status(404).json({ message: 'Attendance record not found' });
    }
    
    res.json({ message: 'Attendance record deleted successfully' });
  } catch (error) {
    console.error('Error deleting attendance record:', error);
    res.status(500).json({ message: 'Error deleting attendance record', error: error.message });
  }
});

module.exports = router;

