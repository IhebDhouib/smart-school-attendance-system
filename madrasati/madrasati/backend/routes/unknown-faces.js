// routes/unknown-faces.js
const express = require("express");
const router = express.Router();
const fs = require("fs");
const path = require("path");

// Get all unknown faces
router.get("/", async (req, res) => {
  try {
    const unknownFacesDir = "/app/unknown_faces"; // Path inside face-detection container

    // Check if directory exists
    if (!fs.existsSync(unknownFacesDir)) {
      return res.json({
        faces: [],
        total: 0,
        message: "Unknown faces directory not found",
      });
    }

    // Read all files in the unknown faces directory
    const files = fs.readdirSync(unknownFacesDir);
    const imageFiles = files.filter(
      (file) =>
        file.toLowerCase().endsWith(".jpg") ||
        file.toLowerCase().endsWith(".jpeg") ||
        file.toLowerCase().endsWith(".png")
    );

    // Parse file information
    const faces = imageFiles.map((filename) => {
      const filePath = path.join(unknownFacesDir, filename);
      const stats = fs.statSync(filePath);

      // Parse filename to extract info (format: inconnu_XXXXXXXX_YYYYMMDD_HHMMSS.jpg)
      const parts = filename.replace(".jpg", "").split("_");
      let unknownId = "unknown";
      let timestamp = new Date(stats.birthtime);

      if (parts.length >= 3) {
        unknownId = `${parts[0]}_${parts[1]}`;
        const dateStr = parts[2];
        const timeStr = parts[3];

        if (
          dateStr &&
          timeStr &&
          dateStr.length === 8 &&
          timeStr.length === 6
        ) {
          const year = dateStr.substring(0, 4);
          const month = dateStr.substring(4, 6);
          const day = dateStr.substring(6, 8);
          const hour = timeStr.substring(0, 2);
          const minute = timeStr.substring(2, 4);
          const second = timeStr.substring(4, 6);

          timestamp = new Date(
            `${year}-${month}-${day}T${hour}:${minute}:${second}`
          );
        }
      }

      return {
        id: unknownId,
        filename: filename,
        timestamp: timestamp,
        size: stats.size,
        path: `/unknown-faces/image/${filename}`, // API endpoint to serve the image
      };
    });

    // Sort by timestamp (newest first)
    faces.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    res.json({
      faces: faces,
      total: faces.length,
      directory: unknownFacesDir,
    });
  } catch (error) {
    console.error("Error fetching unknown faces:", error);
    res.status(500).json({
      message: "Error fetching unknown faces",
      error: error.message,
    });
  }
});

// Serve unknown face images
router.get("/image/:filename", async (req, res) => {
  try {
    const filename = req.params.filename;
    const filePath = path.join("/app/unknown_faces", filename);

    // Security check - ensure filename doesn't contain path traversal
    if (
      filename.includes("..") ||
      filename.includes("/") ||
      filename.includes("\\")
    ) {
      return res.status(400).json({ message: "Invalid filename" });
    }

    // Check if file exists
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ message: "Image not found" });
    }

    // Set appropriate headers
    res.setHeader("Content-Type", "image/jpeg");
    res.setHeader("Cache-Control", "public, max-age=86400"); // Cache for 1 day

    // Stream the file
    const fileStream = fs.createReadStream(filePath);
    fileStream.pipe(res);
  } catch (error) {
    console.error("Error serving unknown face image:", error);
    res.status(500).json({
      message: "Error serving image",
      error: error.message,
    });
  }
});

// Delete an unknown face
router.delete("/:filename", async (req, res) => {
  try {
    const filename = req.params.filename;
    const filePath = path.join("/app/unknown_faces", filename);

    // Security check
    if (
      filename.includes("..") ||
      filename.includes("/") ||
      filename.includes("\\")
    ) {
      return res.status(400).json({ message: "Invalid filename" });
    }

    // Check if file exists
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ message: "Image not found" });
    }

    // Delete the file
    fs.unlinkSync(filePath);

    res.json({
      message: "Unknown face deleted successfully",
      filename: filename,
    });
  } catch (error) {
    console.error("Error deleting unknown face:", error);
    res.status(500).json({
      message: "Error deleting unknown face",
      error: error.message,
    });
  }
});

module.exports = router;
