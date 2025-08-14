const mongoose = require("mongoose");

const teacherSchema = new mongoose.Schema({
  userId: {
    type: String,
    required: [true, "Matricule est requis"],
    unique: true,
  },
  firstName: {
    type: String,
    required: [true, "Prénom est requis"],
  },
  lastName: {
    type: String,
    required: [true, "Nom est requis"],
  },
  subject: {
    type: String,
    required: [true, "Sujet est requis"],
  },
  photo: {
    type: String,
    required: false,
  },
});

module.exports = mongoose.model("Teacher", teacherSchema);
// 