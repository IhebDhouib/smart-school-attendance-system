const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const Student = require('../models/Student');

// Face encoding endpoint
router.post('/encode-student', async (req, res) => {
  try {
    const { studentId } = req.body;
    
    if (!studentId) {
      return res.status(400).json({ error: 'Student ID is required' });
    }

    // Find student in database
    const student = await Student.findById(studentId);
    if (!student) {
      return res.status(404).json({ error: 'Student not found' });
    }

    // Check if student has photos
    if (!student.photos || student.photos.length === 0) {
      return res.status(400).json({ error: 'Student has no photos to encode' });
    }

    // Create student directory in face/dataset
    const faceDir = path.join(__dirname, '../../face');
    const datasetDir = path.join(faceDir, 'dataset');
    const studentDir = path.join(datasetDir, student.matricule);

    // Create directories if they don't exist
    if (!fs.existsSync(datasetDir)) {
      fs.mkdirSync(datasetDir, { recursive: true });
    }
    if (!fs.existsSync(studentDir)) {
      fs.mkdirSync(studentDir, { recursive: true });
    }

    // Copy student photos to dataset directory
    for (let i = 0; i < student.photos.length; i++) {
      const photoPath = student.photos[i];
      const photoName = `${student.matricule}_${i + 1}${path.extname(photoPath)}`;
      const destPath = path.join(studentDir, photoName);
      
      try {
        if (fs.existsSync(photoPath)) {
          fs.copyFileSync(photoPath, destPath);
        }
      } catch (copyError) {
        console.error(`Error copying photo ${photoPath}:`, copyError);
      }
    }

    // Run face encoding script
    const encodingScript = path.join(faceDir, 'encode_faces_copy.py');
    const pythonProcess = spawn('python3', [encodingScript], {
      cwd: faceDir,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let errorOutput = '';

    pythonProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        res.json({
          success: true,
          message: `Face encoding completed for student ${student.fullName}`,
          matricule: student.matricule,
          output: output
        });
      } else {
        res.status(500).json({
          error: 'Face encoding failed',
          code: code,
          output: output,
          errorOutput: errorOutput
        });
      }
    });

    // Send input to Python script to update existing encodings
    pythonProcess.stdin.write('u\n');
    pythonProcess.stdin.end();

  } catch (error) {
    console.error('Face encoding error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Endpoint to encode all students
router.post('/encode-all', async (req, res) => {
  try {
    // Get all students with photos
    const students = await Student.find({ photos: { $exists: true, $not: { $size: 0 } } });
    
    if (students.length === 0) {
      return res.status(400).json({ error: 'No students with photos found' });
    }

    const faceDir = path.join(__dirname, '../../face');
    const datasetDir = path.join(faceDir, 'dataset');

    // Create dataset directory if it doesn't exist
    if (!fs.existsSync(datasetDir)) {
      fs.mkdirSync(datasetDir, { recursive: true });
    }

    // Process each student
    for (const student of students) {
      const studentDir = path.join(datasetDir, student.matricule);
      
      // Create student directory
      if (!fs.existsSync(studentDir)) {
        fs.mkdirSync(studentDir, { recursive: true });
      }

      // Copy student photos
      for (let i = 0; i < student.photos.length; i++) {
        const photoPath = student.photos[i];
        const photoName = `${student.matricule}_${i + 1}${path.extname(photoPath)}`;
        const destPath = path.join(studentDir, photoName);
        
        try {
          if (fs.existsSync(photoPath)) {
            fs.copyFileSync(photoPath, destPath);
          }
        } catch (copyError) {
          console.error(`Error copying photo ${photoPath}:`, copyError);
        }
      }
    }

    // Run face encoding script
    const encodingScript = path.join(faceDir, 'encode_faces_copy.py');
    const pythonProcess = spawn('python3', [encodingScript], {
      cwd: faceDir,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let errorOutput = '';

    pythonProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        res.json({
          success: true,
          message: `Face encoding completed for ${students.length} students`,
          studentsProcessed: students.length,
          output: output
        });
      } else {
        res.status(500).json({
          error: 'Face encoding failed',
          code: code,
          output: output,
          errorOutput: errorOutput
        });
      }
    });

    // Send input to Python script to overwrite existing encodings
    pythonProcess.stdin.write('o\n');
    pythonProcess.stdin.end();

  } catch (error) {
    console.error('Face encoding error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Endpoint to get encoding status
router.get('/status', async (req, res) => {
  try {
    const faceDir = path.join(__dirname, '../../face');
    const encodingsFile = path.join(faceDir, 'encodings.pkl');
    
    const encodingsExist = fs.existsSync(encodingsFile);
    let encodingsInfo = null;
    
    if (encodingsExist) {
      const stats = fs.statSync(encodingsFile);
      encodingsInfo = {
        exists: true,
        size: stats.size,
        lastModified: stats.mtime,
        path: encodingsFile
      };
    }

    // Count students with photos
    const studentsWithPhotos = await Student.countDocuments({ 
      photos: { $exists: true, $not: { $size: 0 } } 
    });

    res.json({
      encodingsFile: encodingsInfo,
      studentsWithPhotos: studentsWithPhotos,
      ready: encodingsExist && studentsWithPhotos > 0
    });

  } catch (error) {
    console.error('Status check error:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;

