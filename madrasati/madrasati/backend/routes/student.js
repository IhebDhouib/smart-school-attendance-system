const express = require("express");
const router = express.Router();
const Student = require("../models/Student");
const multer = require("multer");
const path = require("path");
const xlsx = require("xlsx");
const Classroom = require("../models/Classroom");
const { spawn } = require("child_process");
const fs = require("fs");
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
      console.log(
        `No photos for student ${student.matricule}, skipping encoding`
      );
      return;
    }

    const faceDir = path.join(__dirname, "../../face");
    const datasetDir = path.join(faceDir, "dataset");
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
      const photoName = `${student.matricule}_${i + 1}${path.extname(
        photoPath
      )}`;
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
    const encodingScript = path.join(faceDir, "encode_faces_copy.py");
    const pythonProcess = spawn("python3", [encodingScript], {
      cwd: faceDir,
      stdio: ["pipe", "pipe", "pipe"],
    });

    pythonProcess.stdout.on("data", (data) => {
      console.log(`Face encoding output: ${data}`);
    });

    pythonProcess.stderr.on("data", (data) => {
      console.error(`Face encoding error: ${data}`);
    });

    pythonProcess.on("close", (code) => {
      if (code === 0) {
        console.log(
          `Face encoding completed for student ${student.fullName} (${student.matricule})`
        );
      } else {
        console.error(
          `Face encoding failed for student ${student.fullName} with code ${code}`
        );
      }
    });

    // Send input to Python script to update existing encodings
    pythonProcess.stdin.write("u\n");
    pythonProcess.stdin.end();
  } catch (error) {
    console.error("Face encoding error:", error);
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
    const faceDir = path.join(__dirname, "../../face");
    const datasetDir = path.join(faceDir, "dataset");
    const studentDir = path.join(datasetDir, student.matricule);

    if (fs.existsSync(studentDir)) {
      fs.rmSync(studentDir, { recursive: true, force: true });
      console.log(`Removed face data for student ${student.matricule}`);

      // Trigger re-encoding to update encodings.pkl
      const encodingScript = path.join(faceDir, "encode_faces_copy.py");
      const pythonProcess = spawn("python3", [encodingScript], {
        cwd: faceDir,
        stdio: ["pipe", "pipe", "pipe"],
      });

      pythonProcess.stdin.write("u\n");
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
// Route POST pour l’importation depuis Excel
// POST /import-excel
router.post("/import-excel", upload.single("file"), async (req, res) => {
  try {
    console.log("Excel import started.");
    const workbook = xlsx.readFile(req.file.path);
    console.log("Workbook read.");
    const sheet = workbook.Sheets[workbook.SheetNames[0]];

    // Récupérer toutes les cellules en tableau de lignes
    const data = xlsx.utils.sheet_to_json(sheet, { header: 1 });
    console.log("Raw data from sheet (header: 1):", data);

    if (!data || data.length === 0) {
      return res.status(400).json({ error: "Le fichier est vide." });
    }

    // --- Helpers ---
    const normalize = (text) =>
      (text == null ? "" : text.toString())
        .trim()
        .replace(/\u200E|\u200F/g, "");

    // Gère les deux cas: nombre Excel (série) ou string "dd/MM/yyyy" (ou "d/M/yyyy")
    const parseExcelDate = (value) => {
      if (value == null || value === "") return null;

      // Cas 1: nombre Excel
      if (typeof value === "number") {
        try {
          if (xlsx.SSF && typeof xlsx.SSF.parse_date_code === "function") {
            const o = xlsx.SSF.parse_date_code(value);
            if (o && o.y && o.m && o.d) return new Date(o.y, o.m - 1, o.d);
          }
          // Fallback si SSF indisponible
          const excelEpoch = new Date(Date.UTC(1899, 11, 30)); // Base Excel
          const ms = Math.round(value * 86400 * 1000);
          return new Date(excelEpoch.getTime() + ms);
        } catch {
          return null;
        }
      }

      // Cas 2: string "dd/MM/yyyy" (ou "d/M/yyyy")
      if (typeof value === "string") {
        const s = normalize(value);
        const m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
        if (m) {
          const d = parseInt(m[1], 10);
          const mo = parseInt(m[2], 10) - 1;
          const y = parseInt(m[3], 10);
          const dt = new Date(y, mo, d);
          return isNaN(dt) ? null : dt;
        }
        // Dernier recours: Date.parse()
        const dt2 = new Date(s);
        return isNaN(dt2) ? null : dt2;
      }

      return null;
    };

    // --- Mapping des colonnes ---
    const headers = data[0].map(normalize);
    console.log("Headers lus depuis Excel:", data[0]);
    console.log("Headers normalisés:", headers);

    const columnMapping = {
      "المعرف الوحيد": "matricule",
      الإسم: "fullName",
      "تاريخ الولادة": "dateNaissance",
      القسم: "classe",
      الولي: "nomPere",
    };

    // index -> paramètre (seulement les colonnes utiles)
    const headerIndexMap = {};
    headers.forEach((h, i) => {
      if (columnMapping[h]) headerIndexMap[i] = columnMapping[h];
    });
    console.log("Mapping des colonnes:", headerIndexMap);

    const rows = data.slice(1);
    const createdStudents = [];

    for (const row of rows) {
      const studentData = {};

      // Extraire uniquement les champs mappés
      for (const [idxStr, param] of Object.entries(headerIndexMap)) {
        const idx = Number(idxStr);
        const rawVal = row[idx];

        if (param === "dateNaissance") {
          studentData.dateNaissance = parseExcelDate(rawVal);
        } else if (param === "matricule") {
          // Préserve les zéros éventuels / évite les soucis d'entier
          studentData.matricule =
            rawVal == null ? "" : normalize(String(rawVal));
        } else if (param === "classe") {
          studentData.classe = rawVal == null ? "" : normalize(rawVal);
        } else if (param === "fullName") {
          studentData.fullName = rawVal == null ? "" : normalize(rawVal);
        } else if (param === "nomPere") {
          // Optionnel : peut être vide dans ton fichier
          studentData.nomPere =
            rawVal == null || rawVal === "" ? "" : normalize(rawVal);
        }
      }

      console.log("Étudiant brut extrait:", studentData);

      const { matricule, fullName, dateNaissance, classe } = studentData;

      // Validation: on rend nomPere optionnel
      if (!matricule || !fullName || !dateNaissance || !classe) {
        console.error("Champs manquants obligatoires:", studentData);
        continue;
      }

      // Chercher ou créer la classe
      const name = classe;
      const grade = "أ"; // inchangé, adapte si besoin
      let classroom = await Classroom.findOne({ name, grade });
      if (!classroom) {
        classroom = new Classroom({ name, grade });
        await classroom.save();
        console.log("Nouvelle classe créée:", classroom);
      }

      // Créer l'étudiant
      const student = new Student({
        matricule,
        fullName,
        nomPere:
          studentData.nomPere && studentData.nomPere.trim() !== ""
            ? studentData.nomPere
            : "غير معروف", // vide si absent
        dateNaissance, // de type Date
        classId: classroom._id,
        photos: [],
      });

      await student.save();
      createdStudents.push(student);
      console.log("Étudiant sauvegardé:", student);
    }

    console.log("Excel import completed successfully.");
    res
      .status(201)
      .json({ message: "Importation réussie", students: createdStudents });
  } catch (error) {
    console.error("Error during Excel import:", error);
    res.status(500).json({ error: error.message });
  } finally {
    // Optionnel : nettoyer le fichier uploadé si besoin
    // try { fs.unlinkSync(req.file.path); } catch {}
  }
});

module.exports = router;
