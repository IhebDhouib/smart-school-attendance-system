const express = require("express");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const User = require("../models/User");

const router = express.Router();

const JWT_SECRET = process.env.JWT_SECRET || "supersecretjwtkey";

// =======================
// @route POST /api/auth/register
// =======================
router.post("/register", async (req, res) => {
  console.log("Register request body:", req.body); // <-- log input
  const { name, email, password, role } = req.body;

  try {
    const existing = await User.findOne({ email });
    if (existing) return res.status(400).json({ error: "User already exists" });

    const passwordHash = await bcrypt.hash(password, 10);

    const newUser = new User({ name, email, passwordHash, role });
    await newUser.save();

    res.status(201).json({ message: "User registered successfully" });
  } catch (err) {
    console.error("Register error:", err); // <-- log full error
    res.status(500).json({ error: "Server error", details: err.message });
  }
});

// =======================
// @route POST /api/auth/login
// =======================
router.post("/login", async (req, res) => {
  const { email, password } = req.body;

  try {
    const user = await User.findOne({ email });
    if (!user) return res.status(401).json({ error: "User not found" });

    const isMatch = await bcrypt.compare(password, user.passwordHash);
    if (!isMatch) return res.status(401).json({ error: "Invalid password" });

    const token = jwt.sign({ userId: user._id, role: user.role }, JWT_SECRET, {
      expiresIn: "1d",
    });

    res.json({
      token,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        role: user.role,
      },
    });
  } catch (err) {
    res.status(500).json({ error: "Server error" });
  }
});

// =======================
// @route GET /api/auth/logout (client-side only clears token)
// =======================
router.get("/logout", (req, res) => {
  // Token should be removed on client side
  res.json({
    message: "Logout successful on client side. Just remove the token.",
  });
});

module.exports = router;
