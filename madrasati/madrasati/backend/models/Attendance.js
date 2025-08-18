const mongoose = require("mongoose");

const attendanceSchema = new mongoose.Schema({
  studentId: {
    type: String, // identifiant/ matricule venant du FastAPI / Student
    required: true,
  },
  classId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "Classroom",
    required: true,
  },
  // scheduleId supprimé selon ta nouvelle logique
  timestamp: {
    type: Date,
    default: Date.now,
  },
  camera: { type: String, required: true },
});

module.exports = mongoose.model("Attendance", attendanceSchema);
