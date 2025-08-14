const WebSocket = require('ws');
const mongoose = require('mongoose');
const Attendance = require('./models/Attendance');
const Student = require('./models/Student');
const ClassSchedule = require('./models/ClassSchedule');

// Connect to MongoDB
mongoose.connect('mongodb://localhost:27017/madrasati', {
  useNewUrlParser: true,
  useUnifiedTopology: true,
});

const wss = new WebSocket.Server({ port: 3002 });

console.log('🚀 WebSocket server started on port 3001');

// Helper function to find current schedule
async function getCurrentSchedule(currentTime) {
  const dayNames = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
  const currentDay = dayNames[currentTime.getDay()];
  const currentTimeStr = currentTime.toTimeString().slice(0, 5); // HH:MM format

  try {
    const schedules = await ClassSchedule.find({ day: currentDay });
    
    for (const schedule of schedules) {
      const startTime = schedule.startTime;
      const endTime = schedule.endTime;
      
      if (currentTimeStr >= startTime && currentTimeStr <= endTime) {
        return schedule;
      }
    }
    
    return null;
  } catch (error) {
    console.error('Error finding current schedule:', error);
    return null;
  }
}

// Helper function to find student by matricule
async function findStudentByMatricule(matricule) {
  try {
    const student = await Student.findOne({ matricule: matricule });
    return student;
  } catch (error) {
    console.error('Error finding student:', error);
    return null;
  }
}

wss.on('connection', (ws) => {
  console.log('📱 Face recognition client connected');

  ws.on('message', async (message) => {
    try {
      const data = JSON.parse(message);
      console.log('📨 Received attendance data:', data);

      const { studentId, timestamp } = data;

      if (!studentId || !timestamp) {
        ws.send(JSON.stringify({ error: 'Missing studentId or timestamp' }));
        return;
      }

      // Find student by matricule
      const student = await findStudentByMatricule(studentId);
      if (!student) {
        ws.send(JSON.stringify({ error: `Student with matricule ${studentId} not found` }));
        return;
      }

      // Parse timestamp
      const attendanceTime = new Date(timestamp);
      if (isNaN(attendanceTime.getTime())) {
        ws.send(JSON.stringify({ error: 'Invalid timestamp format' }));
        return;
      }

      // Find current schedule
      const currentSchedule = await getCurrentSchedule(attendanceTime);
      if (!currentSchedule) {
        ws.send(JSON.stringify({ error: 'No active schedule found for current time' }));
        return;
      }

      // Check if student belongs to the class
      if (student.classId.toString() !== currentSchedule.classId.toString()) {
        ws.send(JSON.stringify({ error: 'Student does not belong to the class with active schedule' }));
        return;
      }

      // Check if attendance already exists for this student, class, and schedule today
      const today = new Date(attendanceTime);
      today.setHours(0, 0, 0, 0);
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);

      const existingAttendance = await Attendance.findOne({
        studentId: student._id,
        classId: currentSchedule.classId,
        scheduleId: currentSchedule._id,
        timestamp: {
          $gte: today,
          $lt: tomorrow
        }
      });

      if (existingAttendance) {
        ws.send(JSON.stringify({ 
          message: `Attendance already recorded for ${student.fullName} today`,
          duplicate: true
        }));
        return;
      }

      // Create new attendance record
      const attendance = new Attendance({
        studentId: student._id,
        classId: currentSchedule.classId,
        scheduleId: currentSchedule._id,
        timestamp: attendanceTime
      });

      await attendance.save();

      console.log(`✅ Attendance recorded: ${student.fullName} (${student.matricule}) at ${attendanceTime}`);

      ws.send(JSON.stringify({ 
        message: `Attendance recorded for ${student.fullName}`,
        studentName: student.fullName,
        studentMatricule: student.matricule,
        schedule: currentSchedule.subject,
        timestamp: attendanceTime
      }));

    } catch (error) {
      console.error('❌ Error processing attendance:', error);
      ws.send(JSON.stringify({ error: 'Internal server error' }));
    }
  });

  ws.on('close', () => {
    console.log('📱 Face recognition client disconnected');
  });

  ws.on('error', (error) => {
    console.error('❌ WebSocket error:', error);
  });
});

wss.on('error', (error) => {
  console.error('❌ WebSocket server error:', error);
});

process.on('SIGINT', () => {
  console.log('🛑 Shutting down WebSocket server...');
  wss.close(() => {
    mongoose.connection.close();
    process.exit(0);
  });
});

