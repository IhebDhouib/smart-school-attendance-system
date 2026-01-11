const { google } = require("googleapis");
const fs = require("fs");
const path = require("path");
const winston = require("winston");

// Configure logger for Google Drive operations
const logger = winston.createLogger({
  level: "info",
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: "logs/google-drive-backup.log" }),
    new winston.transports.Console(),
  ],
});

class GoogleDriveBackup {
  constructor() {
    this.drive = null;
    this.parentFolderId = null;
    this.isInitialized = false;
  }

  /**
   * Initialize Google Drive API with service account
   */
  async initialize() {
    try {
      // Load service account credentials from environment or file
      const serviceAccount = this.loadServiceAccountCredentials();

      if (!serviceAccount) {
        throw new Error("Google Drive service account credentials not found");
      }

      // Create JWT auth client
      const auth = new google.auth.JWT(
        serviceAccount.client_email,
        null,
        serviceAccount.private_key.replace(/\\n/g, "\n"),
        ["https://www.googleapis.com/auth/drive.file"]
      );

      // Initialize Google Drive API
      this.drive = google.drive({ version: "v3", auth });

      // Check if we should use shared drives
      const useSharedDrive =
        process.env.GOOGLE_DRIVE_USE_SHARED_DRIVE === "true";
      const sharedDriveId = process.env.GOOGLE_DRIVE_SHARED_DRIVE_ID;

      if (useSharedDrive && sharedDriveId) {
        // Use shared drive - files will be stored there
        this.sharedDriveId = sharedDriveId;
        this.parentFolderId = await this.createOrFindFolder(
          "Madrasati_Student_Photos",
          null,
          sharedDriveId
        );
        logger.info(
          "Google Drive backup service initialized with shared drive",
          {
            sharedDriveId: this.sharedDriveId,
            parentFolderId: this.parentFolderId,
          }
        );
      } else {
        // Create or find the main backup folder in regular drive (will fail for service accounts)
        this.parentFolderId = await this.createOrFindFolder(
          "Madrasati_Student_Photos"
        );
        logger.info("Google Drive backup service initialized successfully", {
          parentFolderId: this.parentFolderId,
        });
      }

      this.isInitialized = true;

      return true;
    } catch (error) {
      logger.error("Failed to initialize Google Drive backup", {
        error: error.message,
        stack: error.stack,
      });
      return false;
    }
  }

  /**
   * Load service account credentials
   */
  loadServiceAccountCredentials() {
    try {
      // Try to load from environment variable first
      if (process.env.GOOGLE_SERVICE_ACCOUNT_KEY) {
        return JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_KEY);
      }

      // Try to load from file
      const credentialsPath =
        process.env.GOOGLE_SERVICE_ACCOUNT_PATH ||
        "./config/google-service-account.json";
      if (fs.existsSync(credentialsPath)) {
        return JSON.parse(fs.readFileSync(credentialsPath, "utf8"));
      }

      return null;
    } catch (error) {
      logger.error("Error loading Google service account credentials", {
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Create or find a folder in Google Drive
   */
  async createOrFindFolder(folderName, parentId = null, sharedDriveId = null) {
    if (!this.drive) {
      throw new Error("Google Drive not initialized");
    }

    try {
      // Search for existing folder
      const query = `name='${folderName}' and mimeType='application/vnd.google-apps.folder' and trashed=false`;
      const searchParams = {
        q: parentId ? `${query} and '${parentId}' in parents` : query,
        fields: "files(id, name)",
      };

      // Add shared drive support
      if (sharedDriveId) {
        searchParams.driveId = sharedDriveId;
        searchParams.corpora = "drive"; // Required when using driveId
        searchParams.includeItemsFromAllDrives = true;
        searchParams.supportsAllDrives = true;
      }

      const searchResponse = await this.drive.files.list(searchParams);
      const existingFolders = searchResponse.data.files;

      if (existingFolders && existingFolders.length > 0) {
        logger.info(`Found existing folder: ${folderName}`, {
          folderId: existingFolders[0].id,
        });
        return existingFolders[0].id;
      }

      // Create new folder if not found
      const folderMetadata = {
        name: folderName,
        mimeType: "application/vnd.google-apps.folder",
        parents: parentId ? [parentId] : undefined,
      };

      const createParams = {
        resource: folderMetadata,
        fields: "id",
      };

      // Add shared drive support for creation
      if (sharedDriveId) {
        createParams.supportsAllDrives = true;
        // If no parent specified and we're using shared drive, set the shared drive as parent
        if (!parentId) {
          folderMetadata.parents = [sharedDriveId];
        }
      }

      const createResponse = await this.drive.files.create(createParams);

      const folderId = createResponse.data.id;
      logger.info(`Created new folder: ${folderName}`, { folderId });
      return folderId;
    } catch (error) {
      logger.error(`Error creating/finding folder: ${folderName}`, {
        error: error.message,
        parentId,
      });
      throw error;
    }
  }

  /**
   * Upload a student's photos to Google Drive
   */
  async backupStudentPhotos(studentData, photoFiles) {
    if (!this.isInitialized) {
      logger.warn("Google Drive not initialized, skipping backup");
      return false;
    }

    try {
      const studentId = studentData.matricule || studentData._id;
      const studentName = studentData.fullName || `Student_${studentId}`;

      // Create student-specific folder
      const sanitizedFolderName = this.sanitizeFolderName(
        `${studentId}_${studentName}`
      );
      const studentFolderId = await this.createOrFindFolder(
        sanitizedFolderName,
        this.parentFolderId,
        this.sharedDriveId
      );

      const uploadPromises = photoFiles.map(async (photoFile, index) => {
        try {
          const fileName = `photo_${index + 1}_${Date.now()}.jpg`;
          const fileMetadata = {
            name: fileName,
            parents: [studentFolderId],
          };

          const media = {
            mimeType: "image/jpeg",
            body: fs.createReadStream(photoFile.path),
          };

          const uploadParams = {
            resource: fileMetadata,
            media: media,
            fields: "id, name, webViewLink",
          };

          // Add shared drive support for file uploads
          if (this.sharedDriveId) {
            uploadParams.supportsAllDrives = true;
          }

          const uploadResponse = await this.drive.files.create(uploadParams);

          logger.info("Photo uploaded to Google Drive", {
            studentId,
            fileName,
            fileId: uploadResponse.data.id,
            webViewLink: uploadResponse.data.webViewLink,
          });

          return {
            success: true,
            fileId: uploadResponse.data.id,
            fileName: uploadResponse.data.name,
            webViewLink: uploadResponse.data.webViewLink,
          };
        } catch (error) {
          logger.error("Failed to upload photo to Google Drive", {
            studentId,
            photoFile: photoFile.path,
            error: error.message,
          });
          return {
            success: false,
            error: error.message,
          };
        }
      });

      const uploadResults = await Promise.all(uploadPromises);
      const successfulUploads = uploadResults.filter(
        (result) => result.success
      );

      logger.info("Student photos backup completed", {
        studentId,
        totalFiles: photoFiles.length,
        successfulUploads: successfulUploads.length,
        failedUploads: uploadResults.length - successfulUploads.length,
      });

      return {
        success: true,
        studentFolderId,
        uploadResults,
        successfulUploads: successfulUploads.length,
        totalFiles: photoFiles.length,
      };
    } catch (error) {
      logger.error("Error during student photos backup", {
        studentId: studentData.matricule || studentData._id,
        error: error.message,
        stack: error.stack,
      });
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Upload face encodings backup
   */
  async backupFaceEncodings(encodingsFilePath) {
    if (!this.isInitialized) {
      logger.warn("Google Drive not initialized, skipping encodings backup");
      return false;
    }

    try {
      if (!fs.existsSync(encodingsFilePath)) {
        logger.warn("Encodings file not found", { path: encodingsFilePath });
        return false;
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const fileName = `face_encodings_backup_${timestamp}.pkl`;

      const fileMetadata = {
        name: fileName,
        parents: [this.parentFolderId],
      };

      const media = {
        mimeType: "application/octet-stream",
        body: fs.createReadStream(encodingsFilePath),
      };

      const uploadResponse = await this.drive.files.create({
        resource: fileMetadata,
        media: media,
        fields: "id, name, webViewLink",
      });

      logger.info("Face encodings backed up to Google Drive", {
        fileName,
        fileId: uploadResponse.data.id,
        webViewLink: uploadResponse.data.webViewLink,
      });

      return {
        success: true,
        fileId: uploadResponse.data.id,
        fileName: uploadResponse.data.name,
        webViewLink: uploadResponse.data.webViewLink,
      };
    } catch (error) {
      logger.error("Failed to backup face encodings", {
        error: error.message,
        stack: error.stack,
      });
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Sanitize folder name for Google Drive
   */
  sanitizeFolderName(name) {
    // Remove or replace characters that are problematic in folder names
    return name
      .replace(/[<>:"/\\|?*]/g, "_")
      .replace(/\s+/g, "_")
      .substring(0, 100); // Limit length
  }

  /**
   * List all backup folders
   */
  async listBackupFolders() {
    if (!this.isInitialized) {
      return [];
    }

    try {
      const response = await this.drive.files.list({
        q: `'${this.parentFolderId}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false`,
        fields: "files(id, name, createdTime, modifiedTime)",
        orderBy: "modifiedTime desc",
      });

      return response.data.files || [];
    } catch (error) {
      logger.error("Error listing backup folders", { error: error.message });
      return [];
    }
  }

  /**
   * Delete old backup files (cleanup)
   */
  async cleanupOldBackups(daysOld = 30) {
    if (!this.isInitialized) {
      return false;
    }

    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysOld);

      const response = await this.drive.files.list({
        q: `'${
          this.parentFolderId
        }' in parents and modifiedTime < '${cutoffDate.toISOString()}' and trashed=false`,
        fields: "files(id, name, modifiedTime)",
      });

      const filesToDelete = response.data.files || [];

      if (filesToDelete.length === 0) {
        logger.info("No old backup files to delete");
        return true;
      }

      const deletePromises = filesToDelete.map(async (file) => {
        try {
          await this.drive.files.delete({ fileId: file.id });
          logger.info("Deleted old backup file", {
            fileName: file.name,
            fileId: file.id,
            modifiedTime: file.modifiedTime,
          });
          return { success: true, fileId: file.id };
        } catch (error) {
          logger.error("Failed to delete old backup file", {
            fileName: file.name,
            fileId: file.id,
            error: error.message,
          });
          return { success: false, fileId: file.id, error: error.message };
        }
      });

      const deleteResults = await Promise.all(deletePromises);
      const successfulDeletes = deleteResults.filter(
        (result) => result.success
      ).length;

      logger.info("Cleanup completed", {
        totalFiles: filesToDelete.length,
        successfulDeletes,
        failedDeletes: filesToDelete.length - successfulDeletes,
      });

      return true;
    } catch (error) {
      logger.error("Error during cleanup", { error: error.message });
      return false;
    }
  }
}

// Export singleton instance
const googleDriveBackup = new GoogleDriveBackup();

module.exports = googleDriveBackup;
