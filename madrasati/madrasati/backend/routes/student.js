const express = require("express");
const router = express.Router();
const Student = require("../models/Student");
const multer = require("multer");
const path = require("path");
const xlsx = require("xlsx");
const Classroom = require("../models/Classroom");
const { spawn } = require("child_process");
const fs = require("fs");
const axios = require("axios");
const FormData = require("form-data");

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

// Helper function to convert local file paths to HTTP URLs
const convertPhotosToUrls = (student, req) => {
  if (student.photos && student.photos.length > 0) {
    student.photos = student.photos.map((photoPath) => {
      // Convert 'uploads/filename.jpg' to proper URL
      if (photoPath && !photoPath.startsWith("http")) {
        const baseUrl = `${req.protocol}://${req.get("host")}`;
        const absoluteUrl = `${baseUrl}/${photoPath}`;

        console.log(`[PHOTO_URL] Converting ${photoPath} to ${absoluteUrl}`);
        return absoluteUrl;
      }
      return photoPath;
    });

    // Also provide relative URLs as a backup
    student.photosRelative = student.photos.map((photoPath) => {
      if (photoPath && photoPath.includes("uploads/")) {
        return photoPath.replace(/.*\/(uploads\/.*)/, "/$1");
      }
      return photoPath;
    });

    // Add debug info for frontend troubleshooting
    student.photoDebug = {
      hasPhotos: true,
      photoCount: student.photos.length,
      firstPhotoUrl: student.photos[0],
      relativeUrl: student.photosRelative[0],
      testPageUrl: `${req.protocol}://${req.get("host")}/test-photo`,
    };
  } else {
    student.photoDebug = {
      hasPhotos: false,
      photoCount: 0,
      message: "No photos found for this student",
    };
  }
  return student;
};

// =============================
// ADD STUDENT
// =============================
router.post("/", upload.array("photos", 5), async (req, res) => {
  try {
    const { matricule, fullName, nomPere, dateNaissance, classId } = req.body;

    console.log("[ADD_STUDENT] Request received:", {
      body: req.body,
      filesCount: req.files ? req.files.length : 0,
      contentType: req.headers["content-type"],
    });

    // Validate required fields
    if (!matricule || !fullName || !nomPere || !dateNaissance || !classId) {
      const missing = [];
      if (!matricule) missing.push("matricule");
      if (!fullName) missing.push("fullName");
      if (!nomPere) missing.push("nomPere");
      if (!dateNaissance) missing.push("dateNaissance");
      if (!classId) missing.push("classId");

      return res.status(400).json({
        error: "Champs obligatoires manquants",
        missing: missing,
      });
    }

    // Safe file handling - only process files if they exist
    const photoPaths =
      req.files && Array.isArray(req.files)
        ? req.files.map((file) => file.path)
        : [];

    const student = new Student({
      matricule,
      fullName,
      nomPere,
      dateNaissance: new Date(dateNaissance),
      classId,
      photos: photoPaths,
    });

    await student.save();

    // 🔥 Call Python API for encoding only if photos exist
    if (photoPaths.length > 0) {
      try {
        for (let i = 0; i < student.photos.length; i++) {
          const photoPath = student.photos[i];
          const form = new FormData();
          form.append("matricule", student.matricule);
          form.append("photo", fs.createReadStream(photoPath));

          const response = await axios.post(
            "http://face-api:8000/students/add",
            form,
            { headers: form.getHeaders() }
          );

          console.log("Face API Add result:", response.data);
        }
      } catch (err) {
        console.error("Face API error (add student):", err.message);
      }
    }

    // Convert photo paths to URLs before returning
    const studentObj = student.toObject();
    const studentWithUrls = convertPhotosToUrls(studentObj, req);

    res.status(201).json(studentWithUrls);
  } catch (err) {
    console.error("[ADD_STUDENT] Error:", err);

    if (err.code === 11000) {
      return res.status(409).json({ error: "Matricule déjà utilisé" });
    }

    if (err.name === "ValidationError") {
      return res.status(400).json({
        error: "Erreur de validation",
        details: err.message,
      });
    }

    res.status(500).json({ error: "Erreur interne du serveur" });
  }
});

// =============================
// DELETE STUDENT
// =============================
router.delete("/:id", async (req, res) => {
  try {
    const student = await Student.findById(req.params.id);
    if (!student) return res.status(404).json({ error: "Étudiant non trouvé" });

    // 🔥 Call Python API to delete dataset + re-encode
    try {
      const response = await axios.delete(
        `http://face-api:8000/students/${student.matricule}`
      );
      console.log("Face API Delete result:", response.data);
    } catch (err) {
      console.error("Face API error (delete student):", err.message);
    }

    await Student.findByIdAndDelete(req.params.id);
    res.status(204).end();
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// =============================
// UPDATE STUDENT
// =============================
router.put("/:id", upload.array("photos", 5), async (req, res) => {
  try {
    console.log("[UPDATE_STUDENT] Request received:", {
      id: req.params.id,
      body: req.body,
      filesCount: req.files ? req.files.length : 0,
      contentType: req.headers["content-type"],
    });

    const updateData = { ...req.body };

    // Safe file handling - only process files if they exist and are an array
    if (req.files && Array.isArray(req.files) && req.files.length > 0) {
      const photoPaths = req.files.map((file) => file.path);
      updateData.photos = photoPaths;
    }

    const student = await Student.findByIdAndUpdate(req.params.id, updateData, {
      new: true,
      runValidators: true,
    });

    if (!student) return res.status(404).json({ error: "Étudiant non trouvé" });

    // 🔥 If new photos uploaded, re-trigger encoding via API
    if (student.photos && student.photos.length > 0) {
      try {
        for (let i = 0; i < student.photos.length; i++) {
          const photoPath = student.photos[i];
          const form = new FormData();
          form.append("matricule", student.matricule);
          form.append("photo", fs.createReadStream(photoPath));

          const response = await axios.post(
            "http://face-api:8000/students/add",
            form,
            { headers: form.getHeaders() }
          );

          console.log("Face API Update result:", response.data);
        }
      } catch (err) {
        console.error("Face API error (update student):", err.message);
      }
    }

    // Convert photo paths to URLs before returning
    const studentObj = student.toObject();
    const studentWithUrls = convertPhotosToUrls(studentObj, req);

    res.json(studentWithUrls);
  } catch (err) {
    console.error("[UPDATE_STUDENT] Error:", err);

    if (err.code === 11000) {
      return res.status(409).json({ error: "Matricule déjà utilisé" });
    }

    if (err.name === "ValidationError") {
      return res.status(400).json({
        error: "Erreur de validation",
        details: err.message,
      });
    }

    if (err.name === "CastError") {
      return res.status(400).json({
        error: "ID étudiant invalide",
        details: err.message,
      });
    }

    res.status(500).json({ error: "Erreur interne du serveur" });
  }
});

module.exports = router;

// Lister tous les étudiants (avec classe peuplée)
router.get("/", async (req, res) => {
  try {
    const students = await Student.find().populate("classId");

    // Convert photo paths to URLs for each student
    const studentsWithUrls = students.map((student) => {
      const studentObj = student.toObject();
      return convertPhotosToUrls(studentObj, req);
    });

    res.json(studentsWithUrls);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Récupérer un étudiant par ID
router.get("/:id", async (req, res) => {
  try {
    const student = await Student.findById(req.params.id).populate("classId");
    if (!student) return res.status(404).json({ error: "Étudiant non trouvé" });

    // Convert photo paths to URLs
    const studentObj = student.toObject();
    const studentWithUrls = convertPhotosToUrls(studentObj, req);

    res.json(studentWithUrls);
  } catch (err) {
    res.status(500).json({ error: err.message });
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
