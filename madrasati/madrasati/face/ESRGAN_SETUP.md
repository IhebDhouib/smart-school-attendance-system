# Real-ESRGAN Setup Guide

## What is Real-ESRGAN?
Real-ESRGAN is an AI-based image enhancement model that improves image quality through super-resolution. It can significantly improve face detection by:
- **Upscaling low-resolution images** (2x or 4x)
- **Enhancing facial details** that may be blurry or far away
- **Improving detection accuracy** for distant or small faces

## Installation

### 1. Install Python Dependencies
```bash
pip install realesrgan==0.3.0 basicsr==1.4.2 facexlib==0.3.0 gfpgan==1.3.8
```

Or install all dependencies including ESRGAN:
```bash
pip install -r requirements-fused.txt
```

### 2. Download Pre-trained Model
Download the ESRGAN model file and place it in the `face/` directory:

**Recommended Model: RealESRGAN_x2plus.pth** (for 2x upscaling)
```bash
# Windows PowerShell
Invoke-WebRequest -Uri "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth" -OutFile "RealESRGAN_x2plus.pth"

# Linux/Mac
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth
```

**Alternative Models:**
- `RealESRGAN_x4plus.pth` - 4x upscaling (slower, higher quality)
- `RealESRNet_x4plus.pth` - Faster but less enhancement

## Configuration

### Environment Variables
You can configure ESRGAN through environment variables:

```bash
# Enable/disable ESRGAN (default: True)
ENABLE_ESRGAN=True

# Model file path (default: RealESRGAN_x2plus.pth)
ESRGAN_MODEL_PATH=RealESRGAN_x2plus.pth

# Upscaling factor: 2 or 4 (default: 2)
ESRGAN_SCALE=2
```

### In Docker
Add to your `docker-compose.yml`:
```yaml
face-fused:
  environment:
    - ENABLE_ESRGAN=True
    - ESRGAN_MODEL_PATH=/app/face/RealESRGAN_x2plus.pth
    - ESRGAN_SCALE=2
  volumes:
    - ./madrasati/face/RealESRGAN_x2plus.pth:/app/face/RealESRGAN_x2plus.pth
```

## Usage

### Running the Single Camera Script
```bash
cd madrasati/face

# With ESRGAN enabled (default)
python app_with_env_single_camera.py

# Disable ESRGAN (use OpenCV only)
ENABLE_ESRGAN=False python app_with_env_single_camera.py
```

### Expected Output
When ESRGAN is enabled and working:
```
✅ Real-ESRGAN libraries loaded successfully
🔧 Initializing Real-ESRGAN...
✅ Real-ESRGAN initialized successfully!
   Model: RealESRGAN_x2plus.pth
   Scale: 2x upscaling
   Tile size: 400x400 (memory efficient)
```

During frame processing:
```
   🎨 ESRGAN enhancement applied (2x upscaling)
```

### Fallback Behavior
If ESRGAN fails or is not available, the system automatically falls back to OpenCV enhancement:
```
   🎨 OpenCV enhancement applied
```

## Performance Considerations

### Processing Time
- **OpenCV Enhancement**: ~10-20ms per frame
- **ESRGAN Enhancement**: ~200-500ms per frame (10-20x slower)

### Recommendations
1. **For Real-time Processing**: Consider processing every Nth frame with ESRGAN
2. **For High Accuracy**: Enable ESRGAN on all frames (slower but better detection)
3. **GPU Acceleration**: If you have CUDA GPU, set `half=True` in the ESRGAN initializer for faster processing

### Memory Usage
- Model loads ~100MB into RAM
- Tile processing (400x400) keeps memory usage reasonable
- Larger tiles = faster but more memory

## Troubleshooting

### Issue: "Real-ESRGAN not available"
**Solution**: Install required libraries:
```bash
pip install realesrgan basicsr facexlib gfpgan
```

### Issue: "ESRGAN model file not found"
**Solution**: Download the model file:
```bash
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth
```

### Issue: "ESRGAN failed: CUDA out of memory"
**Solution**: Reduce tile size or disable GPU:
```python
# In initialize_esrgan() function
esrgan_upsampler = RealESRGANer(
    scale=ESRGAN_SCALE,
    model_path=ESRGAN_MODEL_PATH,
    model=model,
    tile=200,  # Reduce from 400
    tile_pad=10,
    pre_pad=0,
    half=False  # Disable GPU FP16
)
```

### Issue: Too slow for real-time processing
**Solution**: Process fewer frames or disable ESRGAN:
```python
# In main() loop, process every 5th frame with ESRGAN
if frame_skip_counter % 5 == 0:
    process_frame(frame, camera_type, camera_name)
```

## Comparison: OpenCV vs ESRGAN

| Feature | OpenCV Enhancement | ESRGAN Enhancement |
|---------|-------------------|-------------------|
| Speed | ✅ Fast (10-20ms) | ⚠️ Slow (200-500ms) |
| Quality | ✅ Good | ✅✅ Excellent |
| Memory | ✅ Low | ⚠️ Medium |
| Dependencies | ✅ Minimal | ⚠️ Many |
| GPU Required | ❌ No | ❌ No (but recommended) |
| Best For | Real-time detection | High-accuracy offline processing |

## Next Steps

1. **Install dependencies**: `pip install -r requirements-fused.txt`
2. **Download model**: Get `RealESRGAN_x2plus.pth`
3. **Test it**: Run `python app_with_env_single_camera.py`
4. **Monitor performance**: Check timing logs to see enhancement impact
5. **Adjust if needed**: Disable ESRGAN if too slow, or process fewer frames

---
**Note**: ESRGAN is now **enabled by default** in `app_with_env_single_camera.py`. Set `ENABLE_ESRGAN=False` to disable.
