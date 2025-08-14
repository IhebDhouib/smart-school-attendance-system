  const mongoose = require("mongoose");

  const studentSchema = new mongoose.Schema({
    matricule: {
      type: String,
      required: true,
      unique: true,  // Pour garantir que chaque matricule est unique
    },
    fullName: {
      type: String,
      required: true,
    },
    nomPere: {
      type: String,
      required: true,
    },
    dateNaissance: {
      type: Date,
      required: true,
    },
    photos: {
      type: [String], // Liste de chaînes (URL, base64, chemin, etc.)
      default: [],
    },
    classId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Classroom",
      required: true,
    },
  });

  module.exports = mongoose.model("Student", studentSchema);
