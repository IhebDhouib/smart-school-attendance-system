const express = require("express");
const router = express.Router();
const Camera = require("../models/Camera");
const axios = require("axios");

// Get all cameras
router.get("/", async (req, res) => {
  try {
    const cameras = await Camera.find().sort({ createdAt: -1 });
    res.json(cameras);
  } catch (error) {
    console.error("Error fetching cameras:", error);
    res.status(500).json({ error: "Failed to fetch cameras" });
  }
});

// Get camera by ID
router.get("/:id", async (req, res) => {
  try {
    const camera = await Camera.findById(req.params.id);
    if (!camera) {
      return res.status(404).json({ error: "Camera not found" });
    }
    res.json(camera);
  } catch (error) {
    console.error("Error fetching camera:", error);
    res.status(500).json({ error: "Failed to fetch camera" });
  }
});

// Create new camera
router.post("/", async (req, res) => {
  try {
    const { name, ip, port, username, password, classroom, type } = req.body;

    // Basic validation
    if (!name || !ip) {
      return res.status(400).json({ error: "Name and IP are required" });
    }

    // Check if camera with this IP already exists
    const existingCamera = await Camera.findOne({ ip });
    if (existingCamera) {
      return res
        .status(409)
        .json({ error: "Camera with this IP already exists" });
    }

    const camera = new Camera({
      name,
      ip,
      port: port || 8080,
      username: username || "",
      password: password || "",
      classroom: classroom || "",
      type: type || "entry",
      status: "inactive",
    });

    const savedCamera = await camera.save();

    // Test connection after creating
    try {
      await testCameraConnection(camera);
      savedCamera.status = "active";
      await savedCamera.save();
    } catch (testError) {
      console.log(
        "Camera created but connection test failed:",
        testError.message
      );
      savedCamera.status = "error";
      await savedCamera.save();
    }

    res.status(201).json(savedCamera);
  } catch (error) {
    console.error("Error creating camera:", error);
    if (error.code === 11000) {
      res.status(409).json({ error: "Camera with this IP already exists" });
    } else if (error.name === "ValidationError") {
      res.status(400).json({ error: error.message });
    } else {
      res.status(500).json({ error: "Failed to create camera" });
    }
  }
});

// Update camera
router.put("/:id", async (req, res) => {
  try {
    const { name, ip, port, username, password, classroom, type } = req.body;

    // Basic validation
    if (!name || !ip) {
      return res.status(400).json({ error: "Name and IP are required" });
    }

    // Check if another camera with this IP exists (excluding current camera)
    const existingCamera = await Camera.findOne({
      ip,
      _id: { $ne: req.params.id },
    });
    if (existingCamera) {
      return res
        .status(409)
        .json({ error: "Another camera with this IP already exists" });
    }

    const updatedCamera = await Camera.findByIdAndUpdate(
      req.params.id,
      {
        name,
        ip,
        port: port || 8080,
        username: username || "",
        password: password || "",
        classroom: classroom || "",
        type: type || "entry",
      },
      { new: true, runValidators: true }
    );

    if (!updatedCamera) {
      return res.status(404).json({ error: "Camera not found" });
    }

    // Test connection after updating
    try {
      await testCameraConnection(updatedCamera);
      updatedCamera.status = "active";
      await updatedCamera.save();
    } catch (testError) {
      console.log(
        "Camera updated but connection test failed:",
        testError.message
      );
      updatedCamera.status = "error";
      await updatedCamera.save();
    }

    res.json(updatedCamera);
  } catch (error) {
    console.error("Error updating camera:", error);
    if (error.code === 11000) {
      res.status(409).json({ error: "Camera with this IP already exists" });
    } else if (error.name === "ValidationError") {
      res.status(400).json({ error: error.message });
    } else {
      res.status(500).json({ error: "Failed to update camera" });
    }
  }
});

// Delete camera
router.delete("/:id", async (req, res) => {
  try {
    const deletedCamera = await Camera.findByIdAndDelete(req.params.id);
    if (!deletedCamera) {
      return res.status(404).json({ error: "Camera not found" });
    }
    res.json({ message: "Camera deleted successfully" });
  } catch (error) {
    console.error("Error deleting camera:", error);
    res.status(500).json({ error: "Failed to delete camera" });
  }
});

// Test camera connection
router.post("/test-connection", async (req, res) => {
  try {
    const { ip, port, username, password } = req.body;

    if (!ip) {
      return res.status(400).json({ error: "IP address is required" });
    }

    const camera = { ip, port: port || 8080, username, password };

    try {
      await testCameraConnection(camera);
      res.json({ success: true, message: "Connection successful" });
    } catch (testError) {
      res.json({ success: false, message: testError.message });
    }
  } catch (error) {
    console.error("Error testing connection:", error);
    res.status(500).json({ error: "Failed to test connection" });
  }
});

// Helper function to test camera connection
async function testCameraConnection(camera) {
  try {
    // Build URL for camera stream
    const protocol = "http"; // Assuming HTTP, could be HTTPS
    let url = `${protocol}://${camera.ip}:${camera.port}`;

    // Add basic auth if credentials provided
    const config = {
      timeout: 5000, // 5 second timeout
      headers: {
        "User-Agent": "MadrasatiCameraTest/1.0",
      },
    };

    if (camera.username && camera.password) {
      config.auth = {
        username: camera.username,
        password: camera.password,
      };
    }

    // Try to access the camera
    const response = await axios.get(url, config);

    if (response.status === 200) {
      return true;
    } else {
      throw new Error(`Camera responded with status: ${response.status}`);
    }
  } catch (error) {
    if (error.code === "ECONNREFUSED") {
      throw new Error("Connection refused - camera may be offline");
    } else if (error.code === "ETIMEDOUT") {
      throw new Error("Connection timed out");
    } else if (error.response && error.response.status === 401) {
      throw new Error("Authentication failed - check username/password");
    } else if (error.response && error.response.status === 404) {
      throw new Error("Camera stream not found");
    } else {
      throw new Error(`Connection failed: ${error.message}`);
    }
  }
}

// Update camera status (for periodic health checks)
router.patch("/:id/status", async (req, res) => {
  try {
    const { status } = req.body;

    if (!["active", "inactive", "error"].includes(status)) {
      return res.status(400).json({ error: "Invalid status value" });
    }

    const camera = await Camera.findByIdAndUpdate(
      req.params.id,
      { status },
      { new: true }
    );

    if (!camera) {
      return res.status(404).json({ error: "Camera not found" });
    }

    res.json(camera);
  } catch (error) {
    console.error("Error updating camera status:", error);
    res.status(500).json({ error: "Failed to update camera status" });
  }
});

module.exports = router;
