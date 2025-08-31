# 🎥 Camera IP Configuration Guide

This guide explains how to easily update camera IP addresses for the Madrasati face detection system.

## 📍 Single Source of Truth

All camera IP addresses are configured in **ONE PLACE**: the `.env` file

## 🚀 Quick Update Methods

### Method 1: Direct Edit (Simplest)
1. Open `.env` file in any text editor
2. Find the camera lines:
   ```
   ENTRY_CAMERA_1=http://192.168.1.222:8080/video
   EXIT_CAMERA_1=http://192.168.1.223:8080/video
   ```
3. Update the IP addresses
4. Save the file
5. Restart the container: `docker-compose restart face-detection`

### Method 2: Windows Batch Script (User-Friendly)
1. Double-click `quick_update_cameras.bat`
2. Follow the prompts to enter new IP addresses
3. The script will update the configuration and restart the container automatically

### Method 3: Python Script (Advanced)
1. Run: `python update_cameras.py`
2. Follow the interactive wizard
3. View current config, update IPs, and restart container all in one place

## 📝 Camera IP Format

### IP Cameras (Most Common)
```
http://IP_ADDRESS:PORT/video
```
Examples:
- `http://192.168.1.100:8080/video`
- `http://10.0.0.50:8080/video`

### USB Cameras
```
0, 1, 2, 3, etc.
```
Examples:
- `0` (first USB camera)
- `1` (second USB camera)

## 🔧 Configuration Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `ENTRY_CAMERA_1` | Main entrance camera | `http://192.168.1.222:8080/video` |
| `ENTRY_CAMERA_2` | Secondary entrance camera | `1` |
| `EXIT_CAMERA_1` | Main exit camera | `http://192.168.1.223:8080/video` |
| `EXIT_CAMERA_2` | Secondary exit camera | `0` |

## 🔄 Applying Changes

After updating camera IPs, you MUST restart the face-detection container:

```bash
docker-compose restart face-detection
```

## 📋 Troubleshooting

### Check if changes applied:
```bash
docker-compose logs face-detection
```

### Check current container status:
```bash
docker-compose ps
```

### Test camera connectivity:
```bash
docker exec madrasati_face_detection python -c "import cv2; cap = cv2.VideoCapture('YOUR_CAMERA_URL'); print('Camera accessible:', cap.isOpened())"
```

## 📞 Common Issues

### Issue: Camera IP changed but system still uses old IP
**Solution**: Make sure you restarted the face-detection container after updating .env

### Issue: Camera not connecting
**Solutions**: 
1. Check if camera IP is correct and accessible
2. Verify camera is powered on and connected to network
3. Test camera URL in browser: `http://CAMERA_IP:PORT/video`

### Issue: .env changes not taking effect
**Solution**: 
1. Check .env file syntax (no spaces around =)
2. Restart container: `docker-compose restart face-detection`
3. Check logs: `docker-compose logs face-detection`

## 🎯 Quick Test

To quickly test your camera configuration:

1. Update camera IPs in `.env`
2. Run: `docker-compose restart face-detection`
3. Check logs: `docker-compose logs --tail=20 face-detection`
4. Look for messages like:
   - ✅ "Connexion établie" (Connection established)
   - ❌ "Aucune caméra trouvée" (No camera found)

## 💡 Pro Tips

1. **Keep backup**: Save working camera IPs in a text file
2. **Test cameras**: Verify camera URLs work in browser before updating
3. **One change at a time**: Update one camera at a time to isolate issues
4. **Monitor logs**: Always check logs after changes to verify success
