const express = require("express");
const router = express.Router();
const Teacher = require("../models/Teacher");
const multer = require("multer");
const path = require("path");

// Multer config
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, "uploads/"),
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + "-" + Math.round(Math.random() * 1e9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  },
});
const upload = multer({
  storage,
  fileFilter: (req, file, cb) => {
    if (!file.mimetype.startsWith("image/")) {
      return cb(new Error("Seuls les fichiers image sont autorisés"), false);
    }
    cb(null, true);
  },
  limits: { fileSize: 5 * 1024 * 1024 },
});

// Create Teacher
router.post("/", upload.single("photo"), async (req, res) => {
  try {
    const { userId, firstName, lastName, subject } = req.body;

    if (!userId || !firstName || !lastName || !subject) {
      return res
        .status(400)
        .json({
          message:
            "Les champs userId, firstName, lastName et subject sont requis.",
        });
    }

    const teacher = new Teacher({
      userId,
      firstName,
      lastName,
      subject,
      photo: req.file ? `/uploads/${req.file.filename}` : undefined,
    });

    await teacher.save();
    res.status(201).json(teacher);
  } catch (error) {
    if (error.code === 11000) {
      res
        .status(400)
        .json({ message: "Le userId existe déjà.", details: error.message });
    } else {
      res.status(400).json({ message: error.message, details: error.errors });
    }
  }
});

// Get all
router.get("/", async (req, res) => {
  try {
    const teachers = await Teacher.find();
    res.json(teachers);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// Get one by userId
router.get("/:userId", async (req, res) => {
  try {
    const teacher = await Teacher.findOne({ userId: req.params.userId });
    if (!teacher)
      return res.status(404).json({ message: "Teacher non trouvé" });
    res.json(teacher);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// Update
router.put("/:userId", upload.single("photo"), async (req, res) => {
  try {
    const { userId, firstName, lastName, subject } = req.body;

    if (!userId || !firstName || !lastName || !subject) {
      return res
        .status(400)
        .json({
          message:
            "Les champs userId, firstName, lastName et subject sont requis.",
        });
    }

    const updatedData = {
      userId,
      firstName,
      lastName,
      subject,
      photo: req.file ? `/uploads/${req.file.filename}` : undefined,
    };

    const teacher = await Teacher.findOneAndUpdate(
      { userId: req.params.userId },
      updatedData,
      { new: true, runValidators: true }
    );

    if (!teacher)
      return res.status(404).json({ message: "Teacher non trouvé" });

    res.json(teacher);
  } catch (error) {
    if (error.code === 11000) {
      res
        .status(400)
        .json({ message: "Le userId existe déjà.", details: error.message });
    } else {
      res.status(400).json({ message: error.message, details: error.errors });
    }
  }
});

// Delete
router.delete("/:userId", async (req, res) => {
  try {
    const teacher = await Teacher.findOneAndDelete({
      userId: req.params.userId,
    });
    if (!teacher)
      return res.status(404).json({ message: "Teacher non trouvé" });
    res.json({ message: "Teacher supprimé" });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

module.exports = router;
