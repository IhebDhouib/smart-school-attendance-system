# Google Drive Backup Integration Setup Guide

This guide will help you set up Google Drive backup for student photos in your Madrasati attendance system.

## Prerequisites

1. Google Cloud Console account
2. Node.js project with Google APIs enabled

## Step 1: Create Google Cloud Project and Enable Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click on it and press "Enable"

## Step 2: Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Fill in service account details:
   - Name: `madrasati-drive-backup`
   - Description: `Service account for backing up student photos to Google Drive`
4. Click "Create and Continue"
5. Skip "Grant this service account access to project" (optional)
6. Click "Done"

## Step 3: Generate Service Account Key

1. Click on the created service account
2. Go to "Keys" tab
3. Click "Add Key" → "Create New Key"
4. Select "JSON" format
5. Download the JSON file
6. Rename it to `google-service-account.json`

## Step 4: Share Google Drive Folder (Optional)

If you want to use a specific Google Drive account:

1. Create a folder in your Google Drive called "Madrasati_Student_Photos"
2. Right-click the folder → "Share"
3. Add the service account email (from the JSON file) with "Editor" permissions
4. The email looks like: `madrasati-drive-backup@your-project-id.iam.gserviceaccount.com`

## Step 5: Install Required Dependencies

```bash
cd madrasati/madrasati/backend
npm install googleapis
```

## Step 6: Configuration

### Method 1: Environment Variable (Recommended for Production)

Add to your `.env` file or docker-compose environment:

```bash
# Google Drive Backup Configuration
ENABLE_GOOGLE_DRIVE_BACKUP=true
GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"your-project-id",...}'
```

### Method 2: JSON File (For Development)

1. Place `google-service-account.json` in `madrasati/backend/config/`
2. Add to `.env`:

```bash
ENABLE_GOOGLE_DRIVE_BACKUP=true
GOOGLE_SERVICE_ACCOUNT_PATH=./config/google-service-account.json
```

## Step 7: Update Docker Configuration (if using Docker)

Add to your `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      # ... existing environment variables
      ENABLE_GOOGLE_DRIVE_BACKUP: "true"
      GOOGLE_SERVICE_ACCOUNT_KEY: ${GOOGLE_SERVICE_ACCOUNT_KEY}
    volumes:
      # ... existing volumes
      - ./config/google-service-account.json:/app/config/google-service-account.json:ro  # if using file method
```

## Step 8: Test the Integration

1. Start your backend server
2. Add a new student with photos through the web interface
3. Check the console logs for Google Drive backup messages
4. Verify that a folder was created in Google Drive with the student photos

## Features

### ✅ What Gets Backed Up

- **Student Photos**: All photos uploaded for each student
- **Organized Folders**: Each student gets their own folder named `{matricule}_{fullName}`
- **Face Encodings**: Backup of the face encodings database file
- **Timestamps**: All files include timestamps for version control

### ✅ Automatic Operations

- **On Student Creation**: Photos are automatically backed up
- **On Student Update**: New photos are backed up
- **Folder Organization**: Hierarchical folder structure maintained
- **Non-blocking**: Backup runs asynchronously without affecting API performance

### ✅ Management Features

- **List Backups**: View all backup folders
- **Cleanup**: Remove old backup files automatically
- **Error Handling**: Robust error handling with detailed logging
- **Duplicate Detection**: Avoid duplicate uploads

## API Endpoints (Optional Management)

You can add these optional management endpoints to your student routes:

```javascript
// List all backup folders
router.get("/backup/folders", async (req, res) => {
  try {
    const folders = await googleDriveBackup.listBackupFolders();
    res.json(folders);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Manual backup trigger for specific student
router.post("/:id/backup", async (req, res) => {
  try {
    const student = await Student.findById(req.params.id);
    if (!student) {
      return res.status(404).json({ error: "Student not found" });
    }
    
    const photoFiles = student.photos.map(photoPath => ({
      path: path.resolve(photoPath),
      originalname: path.basename(photoPath)
    }));
    
    const result = await googleDriveBackup.backupStudentPhotos(student, photoFiles);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Cleanup old backups
router.delete("/backup/cleanup/:days", async (req, res) => {
  try {
    const days = parseInt(req.params.days) || 30;
    const result = await googleDriveBackup.cleanupOldBackups(days);
    res.json({ success: result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## Logging and Monitoring

The Google Drive backup service includes comprehensive logging:

- **Success Logs**: Successful uploads with file IDs and links
- **Error Logs**: Detailed error messages for troubleshooting
- **Performance Logs**: Upload timing and file sizes
- **Cleanup Logs**: Automatic cleanup operations

Check the log file: `logs/google-drive-backup.log`

## Security Considerations

1. **Keep Service Account Key Secret**: Never commit the JSON key to version control
2. **Limit Permissions**: The service account only needs Drive file creation permissions
3. **Environment Variables**: Use environment variables for sensitive data
4. **Regular Rotation**: Consider rotating service account keys periodically

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify service account JSON is correctly formatted
   - Check that Google Drive API is enabled
   - Ensure service account has proper permissions

2. **Upload Failures**:
   - Check file paths and permissions
   - Verify internet connectivity
   - Monitor Google Drive API quotas

3. **Folder Creation Issues**:
   - Ensure service account can create folders
   - Check for special characters in student names
   - Verify folder naming conventions

### Debug Mode

Enable detailed logging by setting:

```bash
NODE_ENV=development
GOOGLE_DRIVE_DEBUG=true
```

This will provide more detailed console output for troubleshooting.

## Cost Considerations

- **Google Drive API**: Free tier includes generous quotas
- **Storage**: 15GB free storage per Google account
- **Bandwidth**: Upload bandwidth limits apply
- **Requests**: API request quotas (usually sufficient for normal use)

For high-volume usage, consider:
- Google Workspace with increased storage
- Monitoring API quotas
- Implementing backup batching for large uploads

## Benefits

✅ **Data Protection**: Automatic offsite backup of all student photos  
✅ **Disaster Recovery**: Quick recovery from local data loss  
✅ **Accessibility**: Access photos from anywhere via Google Drive  
✅ **Version Control**: Timestamped backups for historical reference  
✅ **Organized Storage**: Automatic folder organization by student  
✅ **No Performance Impact**: Asynchronous backup process  
✅ **Scalable**: Handles growing numbers of students and photos  
✅ **Cost Effective**: Uses free Google Drive storage initially  

Your student photos are now automatically backed up to Google Drive every time a student is added or updated! 🎉