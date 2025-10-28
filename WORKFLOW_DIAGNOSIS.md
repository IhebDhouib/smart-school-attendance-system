# Student Add Workflow Diagnosis

## Current Workflow Analysis

### 1. Frontend → Backend
- **File**: `madrassati/src/app/student/student.component.ts`
- **Action**: Sends FormData with field `'photos'` (array)
- **Status**: ✅ Working (backend receives files)

### 2. Backend Receives
- **File**: `backend/routes/student.js`
- **Action**: Receives via `upload.array("photos", 5)`
- **Status**: ✅ Working (files saved to uploads/)

### 3. Backend → Face API
- **File**: `backend/routes/student.js` (lines 119-131)
- **Code**:
```javascript
if (photoPaths.length > 0) {
  try {
    for (let i = 0; i < student.photos.length; i++) {
      const photoPath = student.photos[i];
      const form = new FormData();
      form.append("matricule", student.matricule);
      form.append("photo", fs.createReadStream(photoPath));

      const response = await axios.post(
        `${FACE_API_URL}/students/add`,
        form,
        { headers: form.getHeaders() }
      );
      console.log("Face API Add result:", response.data);
    }
  } catch (err) {
    console.error("Face API error (add student):", err.message);
  }
}
```
- **Status**: ❌ **NO LOGS APPEARING** - This means either:
  - The loop never executes
  - The axios call fails silently (caught in catch block)
  - The Face API is unreachable

### 4. Face API Receives
- **File**: `face/faceapi.py` (lines 163+)
- **Endpoint**: `POST /students/add`
- **Expected fields**: `matricule`, `photo` (or `file`/`image`)
- **Status**: ❌ **NO REQUESTS RECEIVED** - No logs in face-fused container

## Potential Issues

### Issue #1: Face API URL Configuration
**In Docker environment:**
- Backend env: `FACE_API_URL=http://face-fused:8000`
- This requires backend container to communicate with face-fused container
- **Check**: Are containers on same network?

**Docker Compose Network:**
```yaml
services:
  backend:
    networks:
      - madrasati_network
    environment:
      FACE_API_URL: http://face-fused:8000
  
  face-fused:
    networks:
      - madrasati_network
    ports:
      - "8000:8000"  # Face Encoding API
```
✅ Both are on `madrasati_network`

### Issue #2: Axios Error Not Being Logged
The current error handling only logs `err.message`, which might hide critical information.

**Recommended fix:**
```javascript
catch (err) {
  console.error("Face API error (add student):", err.message);
  console.error("Full error:", err);  // Add full error details
  if (err.response) {
    console.error("Response status:", err.response.status);
    console.error("Response data:", err.response.data);
  }
}
```

### Issue #3: FormData Headers
When using form-data with file streams, headers must be set correctly:
```javascript
form.append("photo", fs.createReadStream(photoPath));
const response = await axios.post(
  `${FACE_API_URL}/students/add`,
  form,
  { 
    headers: form.getHeaders(),  // ✅ This is correct
    timeout: 10000  // Add timeout to prevent hanging
  }
);
```

### Issue #4: File Path Issues
Backend saves files to `uploads/`, but the path might be:
- Relative path: `uploads/filename.jpg`
- Needs to be absolute when streaming

**Potential fix:**
```javascript
const photoPath = student.photos[i];
const absolutePath = path.join(__dirname, '..', photoPath);
form.append("photo", fs.createReadStream(absolutePath));
```

## Diagnostic Steps

### Step 1: Check Backend Logs for Face API Calls
Look for these logs in backend container:
```bash
docker compose logs backend | grep "Face API"
```

Expected output:
```
✅ "Face API Add result: ..."  (success)
❌ "Face API error (add student): ..."  (error caught)
```

### Step 2: Check Face-Fused API Accessibility
From backend container, test if face-fused is reachable:
```bash
docker compose exec backend curl http://face-fused:8000/students/encodings/status
```

Expected: JSON response with encoding status

### Step 3: Check Face-Fused Logs
```bash
docker compose logs face-fused | grep "/students/add"
```

Expected:
```
🔄 /students/add called. Form keys: ['matricule', 'photo']
```

### Step 4: Add Debug Logging
In `backend/routes/student.js`, add before the Face API call:

```javascript
console.log("[FACE_API_DEBUG] Sending to Face API:", {
  url: `${FACE_API_URL}/students/add`,
  matricule: student.matricule,
  photoPath: photoPath,
  photoExists: fs.existsSync(photoPath)
});
```

## Recommended Fixes

### Fix #1: Enhanced Error Logging
```javascript
catch (err) {
  console.error("❌ Face API error (add student):", {
    message: err.message,
    code: err.code,
    status: err.response?.status,
    data: err.response?.data,
    config: {
      url: err.config?.url,
      method: err.config?.method
    }
  });
}
```

### Fix #2: Add Request Logging
```javascript
console.log(`📤 Sending photo ${i+1}/${student.photos.length} to Face API`);
console.log(`   Matricule: ${student.matricule}`);
console.log(`   Photo path: ${photoPath}`);
console.log(`   FACE_API_URL: ${FACE_API_URL}`);

const response = await axios.post(...);
console.log(`✅ Photo ${i+1} encoded successfully:`, response.data);
```

### Fix #3: Use Absolute Paths
```javascript
const path = require("path");
const absolutePath = path.resolve(photoPath);
console.log(`   Absolute path: ${absolutePath}`);
form.append("photo", fs.createReadStream(absolutePath));
```

### Fix #4: Add Timeout
```javascript
const response = await axios.post(
  `${FACE_API_URL}/students/add`,
  form,
  { 
    headers: form.getHeaders(),
    timeout: 30000  // 30 seconds
  }
);
```

## Next Steps

1. **Add debug logging** to backend (Fix #1, #2)
2. **Check backend logs** after adding a student
3. **Check face-fused logs** after adding a student
4. **Test face API** directly from backend container
5. **Apply fixes** based on error messages

## Expected Behavior After Fix

When adding a student with photos:

**Backend logs:**
```
[ADD_STUDENT] Request received: { body: {...}, filesCount: 2 }
📤 Sending photo 1/2 to Face API
   Matricule: 12345
   Photo path: uploads/1234567-filename.jpg
   FACE_API_URL: http://face-fused:8000
✅ Photo 1 encoded successfully: { status: 'ok', model: 'arcface' }
📤 Sending photo 2/2 to Face API
   Matricule: 12345
   Photo path: uploads/1234568-filename.jpg
   FACE_API_URL: http://face-fused:8000
✅ Photo 2 encoded successfully: { status: 'ok', model: 'arcface' }
```

**Face-fused logs:**
```
🔄 /students/add called. Form keys: ['matricule', 'photo']
🔄 Adding student: 12345 with ArcFace (512-dim embeddings)
📁 Created directory: dataset/12345
💾 Saved photo from upload: dataset/12345/12345_1234567.jpg
🧠 Starting face encoding with ArcFace...
📸 Processing student: 12345 with ArcFace (512-dim)
   ✅ 12345_1234567.jpg: 1 face(s) encoded with ArcFace (512-dim)
✅ ArcFace (512-dim) encodings saved to encodings_arcface.pkl
```
