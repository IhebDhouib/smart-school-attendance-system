const teacherAttendanceSchema = new mongoose.Schema({
  teacherId: { type: mongoose.Schema.Types.ObjectId, ref: "Teacher" },
  date: Date,
  timeSlot: String, // e.g. "08:00-09:30"
  isPresent: Boolean,
  markedBy: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
});
module.exports = mongoose.model("TeacherAttendance", teacherAttendanceSchema);
