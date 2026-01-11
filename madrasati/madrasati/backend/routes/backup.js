const express = require("express");
const router = express.Router();
const Student = require("../models/Student");
const googleDriveBackup = require("../services/googleDriveBackup");
const path = require("path");

// =============================
// GOOGLE DRIVE BACKUP MANAGEMENT ROUTES
// =============================

/**
 * Get Google Drive backup status and configuration
 */
router.get("/status", async (req, res) => {
  try {
    const isInitialized = googleDriveBackup.isInitialized;
    const folders = isInitialized
      ? await googleDriveBackup.listBackupFolders()
      : [];

    res.json({
      isEnabled: !!process.env.ENABLE_GOOGLE_DRIVE_BACKUP,
      isInitialized,
      totalBackupFolders: folders.length,
      folders: folders.slice(0, 10), // Return first 10 folders
      lastUpdated: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      error: "Failed to get backup status",
      details: error.message,
    });
  }
});

/**
 * List all backup folders in Google Drive
 */
router.get("/folders", async (req, res) => {
  try {
    if (!googleDriveBackup.isInitialized) {
      return res.status(503).json({
        error: "Google Drive backup service not initialized",
      });
    }

    const folders = await googleDriveBackup.listBackupFolders();
    res.json({
      success: true,
      totalFolders: folders.length,
      folders,
    });
  } catch (error) {
    res.status(500).json({
      error: "Failed to list backup folders",
      details: error.message,
    });
  }
});

/**
 * Initialize Google Drive backup service
 */
router.post("/initialize", async (req, res) => {
  try {
    const result = await googleDriveBackup.initialize();

    if (result) {
      res.json({
        success: true,
        message: "Google Drive backup service initialized successfully",
      });
    } else {
      res.status(500).json({
        success: false,
        message: "Failed to initialize Google Drive backup service",
      });
    }
  } catch (error) {
    res.status(500).json({
      error: "Error initializing Google Drive backup",
      details: error.message,
    });
  }
});

/**
 * Manual backup trigger for specific student
 */
router.post("/student/:id", async (req, res) => {
  try {
    if (!googleDriveBackup.isInitialized) {
      const initResult = await googleDriveBackup.initialize();
      if (!initResult) {
        return res.status(503).json({
          error: "Google Drive backup service not available",
        });
      }
    }

    const student = await Student.findById(req.params.id);
    if (!student) {
      return res.status(404).json({ error: "Student not found" });
    }

    if (!student.photos || student.photos.length === 0) {
      return res.status(400).json({
        error: "Student has no photos to backup",
      });
    }

    // Prepare photo files for backup
    const photoFiles = student.photos
      .filter((photoPath) => {
        const fullPath = path.resolve(photoPath);
        const exists = require("fs").existsSync(fullPath);
        if (!exists) {
          console.warn(`Photo file not found: ${fullPath}`);
        }
        return exists;
      })
      .map((photoPath) => ({
        path: path.resolve(photoPath),
        originalname: path.basename(photoPath),
      }));

    if (photoFiles.length === 0) {
      return res.status(400).json({
        error: "No valid photo files found for backup",
      });
    }

    const result = await googleDriveBackup.backupStudentPhotos(
      student,
      photoFiles
    );

    res.json({
      success: result.success,
      studentId: student.matricule,
      studentName: student.fullName,
      totalFiles: result.totalFiles,
      successfulUploads: result.successfulUploads,
      failedUploads: result.totalFiles - result.successfulUploads,
      googleDriveFolderId: result.studentFolderId,
      uploadResults: result.uploadResults,
      error: result.error,
    });
  } catch (error) {
    res.status(500).json({
      error: "Manual backup failed",
      details: error.message,
    });
  }
});

/**
 * Backup all students (bulk operation)
 */
router.post("/all-students", async (req, res) => {
  try {
    if (!googleDriveBackup.isInitialized) {
      const initResult = await googleDriveBackup.initialize();
      if (!initResult) {
        return res.status(503).json({
          error: "Google Drive backup service not available",
        });
      }
    }

    const students = await Student.find({
      photos: { $exists: true, $not: { $size: 0 } },
    });

    if (students.length === 0) {
      return res.status(404).json({
        message: "No students with photos found",
      });
    }

    const results = [];
    let successCount = 0;
    let errorCount = 0;

    // Process students in batches of 5 to avoid overwhelming the API
    const batchSize = 5;
    for (let i = 0; i < students.length; i += batchSize) {
      const batch = students.slice(i, i + batchSize);

      const batchPromises = batch.map(async (student) => {
        try {
          const photoFiles = student.photos
            .filter((photoPath) => {
              const fullPath = path.resolve(photoPath);
              return require("fs").existsSync(fullPath);
            })
            .map((photoPath) => ({
              path: path.resolve(photoPath),
              originalname: path.basename(photoPath),
            }));

          if (photoFiles.length === 0) {
            return {
              studentId: student.matricule,
              success: false,
              error: "No valid photo files found",
            };
          }

          const result = await googleDriveBackup.backupStudentPhotos(
            student,
            photoFiles
          );

          if (result.success) {
            successCount++;
          } else {
            errorCount++;
          }

          return {
            studentId: student.matricule,
            studentName: student.fullName,
            success: result.success,
            totalFiles: result.totalFiles,
            successfulUploads: result.successfulUploads,
            error: result.error,
          };
        } catch (error) {
          errorCount++;
          return {
            studentId: student.matricule,
            success: false,
            error: error.message,
          };
        }
      });

      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);

      // Add delay between batches to respect API limits
      if (i + batchSize < students.length) {
        await new Promise((resolve) => setTimeout(resolve, 2000)); // 2 second delay
      }
    }

    res.json({
      success: true,
      totalStudents: students.length,
      successfulBackups: successCount,
      failedBackups: errorCount,
      results,
    });
  } catch (error) {
    res.status(500).json({
      error: "Bulk backup failed",
      details: error.message,
    });
  }
});

/**
 * Cleanup old backup files
 */
router.delete("/cleanup/:days", async (req, res) => {
  try {
    if (!googleDriveBackup.isInitialized) {
      return res.status(503).json({
        error: "Google Drive backup service not initialized",
      });
    }

    const days = parseInt(req.params.days) || 30;

    if (days < 7) {
      return res.status(400).json({
        error: "Minimum cleanup period is 7 days for safety",
      });
    }

    const result = await googleDriveBackup.cleanupOldBackups(days);

    res.json({
      success: result,
      message: `Cleanup completed for files older than ${days} days`,
      daysOld: days,
    });
  } catch (error) {
    res.status(500).json({
      error: "Cleanup failed",
      details: error.message,
    });
  }
});

/**
 * Cleanup old backup files with default 30 days
 */
router.delete("/cleanup", async (req, res) => {
  try {
    if (!googleDriveBackup.isInitialized) {
      return res.status(503).json({
        error: "Google Drive backup service not initialized",
      });
    }

    const days = 30; // Default to 30 days

    if (days < 7) {
      return res.status(400).json({
        error: "Minimum cleanup period is 7 days for safety",
      });
    }

    const result = await googleDriveBackup.cleanupOldBackups(days);

    res.json({
      success: result,
      message: `Cleanup completed for files older than ${days} days (default)`,
      daysOld: days,
    });
  } catch (error) {
    res.status(500).json({
      error: "Cleanup failed",
      details: error.message,
    });
  }
});

/**
 * Backup face encodings file
 */
router.post("/encodings", async (req, res) => {
  try {
    if (!googleDriveBackup.isInitialized) {
      const initResult = await googleDriveBackup.initialize();
      if (!initResult) {
        return res.status(503).json({
          error: "Google Drive backup service not available",
        });
      }
    }

    // Default encodings file path - adjust based on your configuration
    const encodingsFilePath =
      process.env.ENCODINGS_FILE_ARCFACE ||
      path.join(process.cwd(), "../face/encodings_arcface.pkl");

    const result = await googleDriveBackup.backupFaceEncodings(
      encodingsFilePath
    );

    if (result.success) {
      res.json({
        success: true,
        message: "Face encodings backed up successfully",
        fileName: result.fileName,
        fileId: result.fileId,
        webViewLink: result.webViewLink,
      });
    } else {
      res.status(500).json({
        success: false,
        error: result.error,
      });
    }
  } catch (error) {
    res.status(500).json({
      error: "Encodings backup failed",
      details: error.message,
    });
  }
});

module.exports = router;
