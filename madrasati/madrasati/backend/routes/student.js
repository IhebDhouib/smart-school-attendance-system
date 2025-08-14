const express = require("express");
const router = express.Router();
const Student = require("../models/Student");
const multer = require("multer");
const path = require("path");
const xlsx = require("xlsx");
const Classroom = require("../models/Classroom");
const { spawn } = require('child_process');
const fs = require('fs');
// 📁 Configuration Multer
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, "uploads/"); // Dossier de destination
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + "-" + Math.round(Math.random() * 1e9);
    cb(null, uniqueSuffix + path.extname(file.originalname)); // nom du fichier
  },
});

const upload = multer({ storage });

// Function to trigger face encoding for a student
async function triggerFaceEncoding(student) {
  try {
    if (!student.photos || student.photos.length === 0) {
      console.log(`No photos for student ${student.matricule}, skipping encoding`);
      return;
    }

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
          console.log(`Copied photo to ${destPath}`);
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

    pythonProcess.stdout.on('data', (data) => {
      console.log(`Face encoding output: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`Face encoding error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        console.log(`Face encoding completed for student ${student.fullName} (${student.matricule})`);
      } else {
        console.error(`Face encoding failed for student ${student.fullName} with code ${code}`);
      }
    });

    // Send input to Python script to update existing encodings
    pythonProcess.stdin.write('u\n');
    pythonProcess.stdin.end();

  } catch (error) {
    console.error('Face encoding error:', error);
  }
}

router.post("/", upload.array("photos", 5), async (req, res) => {
  try {
    const { matricule, fullName, nomPere, dateNaissance, classId } = req.body;
    const photoPaths = req.files.map((file) => file.path);

    const student = new Student({
      matricule,
      fullName,
      nomPere,
      dateNaissance,
      classId,
      photos: photoPaths,
    });

    await student.save();
    
    // Trigger face encoding if photos exist
    if (photoPaths.length > 0) {
      triggerFaceEncoding(student);
    }
    
    res.status(201).json(student);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});



// Lister tous les étudiants (avec classe peuplée)
router.get("/", async (req, res) => {
  try {
    const students = await Student.find().populate("classId");
    res.json(students);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Récupérer un étudiant par ID
router.get("/:id", async (req, res) => {
  try {
    const student = await Student.findById(req.params.id).populate("classId");
    if (!student) return res.status(404).json({ error: "Étudiant non trouvé" });
    res.json(student);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Supprimer un étudiant
router.delete("/:id", async (req, res) => {
  try {
    const student = await Student.findById(req.params.id);
    if (!student) return res.status(404).json({ error: "Étudiant non trouvé" });
    
    // Remove student's face data from dataset
    const faceDir = path.join(__dirname, '../../face');
    const datasetDir = path.join(faceDir, 'dataset');
    const studentDir = path.join(datasetDir, student.matricule);
    
    if (fs.existsSync(studentDir)) {
      fs.rmSync(studentDir, { recursive: true, force: true });
      console.log(`Removed face data for student ${student.matricule}`);
      
      // Trigger re-encoding to update encodings.pkl
      const encodingScript = path.join(faceDir, 'encode_faces_copy.py');
      const pythonProcess = spawn('python3', [encodingScript], {
        cwd: faceDir,
        stdio: ['pipe', 'pipe', 'pipe']
      });
      
      pythonProcess.stdin.write('u\n');
      pythonProcess.stdin.end();
    }
    
    await Student.findByIdAndDelete(req.params.id);
    res.status(204).end();
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Mettre à jour un étudiant
router.put("/:id", upload.array("photos", 5), async (req, res) => {
  try {
    const updateData = { ...req.body };
    
    // If new photos are uploaded, add them to the update data
    if (req.files && req.files.length > 0) {
      const photoPaths = req.files.map((file) => file.path);
      updateData.photos = photoPaths;
    }
    
    const student = await Student.findByIdAndUpdate(req.params.id, updateData, {
      new: true,
      runValidators: true,
    });
    
    if (!student) return res.status(404).json({ error: "Étudiant non trouvé" });
    
    // Trigger face encoding if photos exist
    if (student.photos && student.photos.length > 0) {
      triggerFaceEncoding(student);
    }
    
    res.json(student);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});












// Route POST pour l’importation depuis Excel
router.post("/import-excel", upload.single("file"), async (req, res) => {
  try {
    console.log("Excel import started.");
    const workbook = xlsx.readFile(req.file.path);
    console.log("Workbook read.");
    const sheet = workbook.Sheets[workbook.SheetNames[0]];

    // Extract data as array of arrays, starting from the first row (including headers)
    const data = xlsx.utils.sheet_to_json(sheet, { header: 1 });
    console.log("Raw data from sheet (header: 1):", data);

    // Assuming the first row contains the headers, and subsequent rows are data
    const rows = data.slice(1);

    const createdStudents = [];

    for (const rawRow of rows) {
      console.log("Processing raw row:", rawRow);

      // Accessing data by index as per user's request
      const matricule = rawRow[1]; // المعرف الوحيد
      const fullName = rawRow[2]; // الإسم
      const dateNaissance = rawRow[3]; // تاريخ الولادة
      const classe = rawRow[6]; // القسم
      const nomPere = rawRow[7]; // الولي

      console.log("Extracted fields by index: ", { matricule, fullName, nomPere, dateNaissance, classe });

      // Validate required fields before proceeding
      if (!matricule || !fullName || !nomPere || !dateNaissance || !classe) {
        console.error("Missing required field in row:", { matricule, fullName, nomPere, dateNaissance, classe });
        continue; // Skip this row or handle error as appropriate
      }

      // classe = "Class A - 1ère année primaire"
      const name = classe;
      const grade = "أ";
      console.log("Classroom name and grade:", { name, grade });

      // Chercher ou créer la classe
      let classroom = await Classroom.findOne({ name, grade });
      console.log("Classroom found or not:", classroom);

      if (!classroom) {
        classroom = new Classroom({ name, grade });
        await classroom.save();
        console.log("New classroom created:", classroom);
      }

      const student = new Student({
        matricule,
        fullName,
        nomPere,
        dateNaissance,
        classId: classroom._id,
        photos: [] // pas de photo dans import Excel
      });

      await student.save();
      createdStudents.push(student);
      console.log("Student saved:", student);
    }

    console.log("Excel import completed successfully.");
    res.status(201).json({ message: "Importation réussie", students: createdStudents });
  } catch (error) {
    console.error("Error during Excel import:", error);
    res.status(500).json({ error: error.message });
  }
});




module.exports = router;
