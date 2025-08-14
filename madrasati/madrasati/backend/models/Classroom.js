const mongoose = require("mongoose");

const classroomSchema = new mongoose.Schema({
  name: { type: String, required: true }, // ex: "A", "B"
  grade: { type: String, required: true }, // ex: "1ère année primaire"
});

module.exports = mongoose.model("Classroom", classroomSchema);
