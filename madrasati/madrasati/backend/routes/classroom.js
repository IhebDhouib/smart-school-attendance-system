const express = require("express");
const router = express.Router();
const Classroom = require("../models/Classroom");

// Create a classroom
router.post("/", async (req, res) => {
  try {
    const classroom = new Classroom(req.body);
    await classroom.save();
    res.status(201).json(classroom);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// List all classrooms
router.get("/", async (req, res) => {
  const classrooms = await Classroom.find();
  res.json(classrooms);
});

// Get classroom by name and grade
router.get('/name/:name', async (req, res) => {
  try {
    const { name } = req.params;
    const { grade } = req.query;
    if (!grade) {
      return res.status(400).json({ error: 'Grade is required' });
    }
    const classroom = await Classroom.findOne({ name, grade });
    if (!classroom) {
      return res.status(404).json({ error: 'Classroom not found' });
    }
    res.json(classroom);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Delete a classroom
router.delete("/:id", async (req, res) => {
  try {
    await Classroom.findByIdAndDelete(req.params.id);
    res.status(204).end();
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

module.exports = router;
