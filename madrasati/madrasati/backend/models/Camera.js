const mongoose = require("mongoose");

const cameraSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: true,
      trim: true,
    },
    ip: {
      type: String,
      required: true,
      unique: true,
      validate: {
        validator: function (v) {
          // Basic IP validation
          return /^(\d{1,3}\.){3}\d{1,3}$/.test(v);
        },
        message: "Invalid IP address format",
      },
    },
    port: {
      type: Number,
      default: 8080,
      min: 1,
      max: 65535,
    },
    username: {
      type: String,
      default: "",
    },
    password: {
      type: String,
      default: "",
    },
    classroom: {
      type: String,
      default: "",
    },
    type: {
      type: String,
      enum: ["entry", "exit"],
      required: true,
      default: "entry",
    },
    status: {
      type: String,
      enum: ["active", "inactive", "error"],
      default: "inactive",
    },
  },
  {
    timestamps: true,
  }
);

// Index for faster queries (ip already has unique index from schema)
cameraSchema.index({ classroom: 1 });
cameraSchema.index({ status: 1 });
cameraSchema.index({ type: 1 });

module.exports = mongoose.model("Camera", cameraSchema);
