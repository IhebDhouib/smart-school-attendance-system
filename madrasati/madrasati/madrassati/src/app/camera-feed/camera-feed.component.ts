import { Component, ElementRef, OnDestroy, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { CameraService, Camera } from 'src/services/camera.service';

interface CaptureItem {
  url: string;
  name: string;
  timestamp: Date;
  blob?: Blob;
  type?: string; // Ajouter une propriété type pour éviter les erreurs
}

interface LogEntry {
  timestamp: Date;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

interface CameraDevice {
  deviceId: string;
  label: string;
}

@Component({
  selector: 'app-camera-feed',
  templateUrl: './camera-feed.component.html',
  styleUrls: ['./camera-feed.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class CameraFeedComponent implements OnInit, OnDestroy {
  @ViewChild('videoElement', { static: false }) videoElement!: ElementRef<HTMLVideoElement>;
  @ViewChild('imageElement', { static: false }) imageElement!: ElementRef<HTMLImageElement>;

  // Camera settings
  selectedCamera: string = 'ip'; // Par défaut sur IP pour votre usage
  customCameraUrl: string = 'http://192.168.1.153:8080/video';
  streamQuality: string = 'medium';

  // Available cameras
  availableCameras: CameraDevice[] = [];
  selectedDeviceId: string = '';

  // Saved cameras from database
  savedCameras: Camera[] = [];
  selectedSavedCameraId: string = '';

  // Stream state
  isStreaming: boolean = false;
  isConnecting: boolean = false;
  isRecording: boolean = false;
  isMuted: boolean = true;
  volume: number = 50;

  // Stream info
  connectionStatus: string = 'disconnected';
  streamDuration: string = '00:00:00';

  // Media stream
  private mediaStream: MediaStream | null = null;
  private streamStartTime: Date | null = null;
  private durationInterval: any;
  private mediaRecorder: MediaRecorder | null = null;
  private recordedChunks: Blob[] = [];
  
  // Pour les flux IP
  private refreshInterval: any;
  isIPStream: boolean = false;

  // Data
  captures: CaptureItem[] = [];
  logs: LogEntry[] = [];

  constructor(private cameraService: CameraService) { }

  async ngOnInit(): Promise<void> {
    this.addLog('تم تحميل صفحة بث الكاميرا', 'info');
    await this.getCameraDevices();
    this.loadSavedCameras(); // Remove await since it's now using subscription
  }

  ngOnDestroy(): void {
    this.stopStream();
    if (this.durationInterval) {
      clearInterval(this.durationInterval);
    }
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  // Get available camera devices
  async getCameraDevices(): Promise<void> {
    try {
      const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
      tempStream.getTracks().forEach(track => track.stop());

      const devices = await navigator.mediaDevices.enumerateDevices();
      this.availableCameras = devices
        .filter(device => device.kind === 'videoinput')
        .map(device => ({
          deviceId: device.deviceId,
          label: device.label || `كاميرا ${device.deviceId.substring(0, 10)}`
        }));

      if (this.availableCameras.length > 0) {
        this.selectedDeviceId = this.availableCameras[0].deviceId;
        this.addLog(`تم العثور على ${this.availableCameras.length} كاميرا متاحة`, 'success');
      } else {
        this.addLog('لم يتم العثور على كاميرات', 'warning');
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error getting camera devices:', error);
      this.addLog(`خطأ في الوصول للكاميرات - تأكد من الصلاحيات: ${errorMessage}`, 'error');
    }
  }

  // Load saved cameras from database
  async loadSavedCameras(): Promise<void> {
    try {
      this.cameraService.getAllCameras().subscribe({
        next: (cameras) => {
          this.savedCameras = cameras || [];
          
          if (this.savedCameras.length > 0) {
            this.selectedSavedCameraId = this.savedCameras[0]._id || '';
            this.addLog(`تم تحميل ${this.savedCameras.length} كاميرا محفوظة`, 'success');
          } else {
            this.addLog('لا توجد كاميرات محفوظة', 'info');
          }
        },
        error: (error) => {
          const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
          console.error('Error loading saved cameras:', error);
          this.addLog(`خطأ في تحميل الكاميرات المحفوظة: ${errorMessage}`, 'error');
        }
      });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error loading saved cameras:', error);
      this.addLog(`خطأ في تحميل الكاميرات المحفوظة: ${errorMessage}`, 'error');
    }
  }

  // Camera control methods
  async startStream(): Promise<void> {
    try {
      this.isConnecting = true;
      this.addLog('جاري الاتصال بالكاميرا...', 'info');

      const cameraUrl = this.getCameraUrl();

      if (this.selectedCamera === 'custom' && !this.isValidUrl(cameraUrl)) {
        throw new Error('رابط الكاميرا المخصص غير صالح');
      }

      if (this.selectedCamera === 'saved' && !cameraUrl) {
        throw new Error('لم يتم اختيار كاميرا محفوظة صالحة');
      }

      if (this.selectedCamera === 'ip' || this.selectedCamera === 'custom' || this.selectedCamera === 'saved') {
        await this.startIPCameraStream(cameraUrl);
      } else {
        await this.startLocalCameraStream();
      }

      this.isStreaming = true;
      this.connectionStatus = 'connected';
      this.streamStartTime = new Date();
      this.startDurationTimer();

      this.addLog('تم الاتصال بالكاميرا بنجاح', 'success');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error starting stream:', error);
      this.addLog(`فشل في الاتصال بالكاميرا: ${errorMessage}`, 'error');
      this.connectionStatus = 'error';
    } finally {
      this.isConnecting = false;
    }
  }

  stopStream(): void {
    try {
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }

      if (this.videoElement?.nativeElement) {
        this.videoElement.nativeElement.srcObject = null;
        this.videoElement.nativeElement.src = '';
      }

      if (this.imageElement?.nativeElement) {
        this.imageElement.nativeElement.src = '';
      }

      if (this.durationInterval) {
        clearInterval(this.durationInterval);
      }

      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
      }

      if (this.isRecording) {
        this.stopRecording();
      }

      this.isStreaming = false;
      this.isIPStream = false;
      this.connectionStatus = 'disconnected';
      this.streamDuration = '00:00:00';

      this.addLog('تم إيقاف البث', 'info');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error stopping stream:', error);
      this.addLog(`خطأ في إيقاف البث: ${errorMessage}`, 'error');
    }
  }

  switchCamera(): void {
    if (this.isStreaming) {
      this.stopStream();
      setTimeout(() => {
        this.startStream();
      }, 1000);
    }
    this.addLog(`تم تغيير مصدر الكاميرا إلى: ${this.getCameraDisplayName()}`, 'info');
  }

  switchLocalCamera(): void {
    if (this.selectedCamera === 'local' && this.isStreaming) {
      this.stopStream();
      setTimeout(() => {
        this.startStream();
      }, 1000);
    }
    this.addLog(`تم تغيير الكاميرا المحلية`, 'info');
  }

  switchSavedCamera(): void {
    if (this.selectedCamera === 'saved' && this.isStreaming) {
      this.stopStream();
      setTimeout(() => {
        this.startStream();
      }, 1000);
    }
    const selectedCamera = this.savedCameras.find(camera => camera._id === this.selectedSavedCameraId);
    const cameraName = selectedCamera ? selectedCamera.name : 'غير محدد';
    this.addLog(`تم تغيير الكاميرا المحفوظة إلى: ${cameraName}`, 'info');
  }

  refreshSavedCameras(): void {
    this.addLog('جاري تحديث قائمة الكاميرات المحفوظة...', 'info');
    this.loadSavedCameras();
  }

  changeQuality(): void {
    if (this.isStreaming) {
      this.addLog(`تم تغيير جودة البث إلى: ${this.getQualityDisplayName()}`, 'info');
      this.switchCamera();
    }
  }

  validateCustomUrl(): void {
    if (this.selectedCamera === 'custom' && this.customCameraUrl && !this.isValidUrl(this.customCameraUrl)) {
      this.addLog('رابط الكاميرا المخصص غير صالح', 'warning');
    }
  }

  // Recording methods (seulement pour flux locaux)
  toggleRecording(): void {
    if (this.isIPStream) {
      this.addLog('التسجيل غير متاح لكاميرات IP - استخدم التقاط الصور بدلاً من ذلك', 'warning');
      return;
    }
    
    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording();
    }
  }

  private startRecording(): void {
    try {
      if (!this.mediaStream || this.isIPStream) {
        throw new Error('لا يوجد بث متاح للتسجيل أو البث من كاميرا IP');
      }

      this.recordedChunks = [];
      const mimeTypes = [
        'video/webm;codecs=vp9',
        'video/webm;codecs=vp8',
        'video/webm',
        'video/mp4'
      ];

      let selectedMimeType = '';
      for (const mimeType of mimeTypes) {
        if (MediaRecorder.isTypeSupported(mimeType)) {
          selectedMimeType = mimeType;
          break;
        }
      }

      this.mediaRecorder = new MediaRecorder(this.mediaStream, {
        mimeType: selectedMimeType
      });

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.recordedChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.recordedChunks, { type: selectedMimeType });
        const url = URL.createObjectURL(blob);
        const timestamp = new Date();

        this.captures.push({
          url,
          name: `recording_${timestamp.getTime()}`,
          timestamp,
          blob,
          type: 'video'
        });

        this.addLog('تم حفظ التسجيل', 'success');
      };

      this.mediaRecorder.start(1000);
      this.isRecording = true;
      this.addLog('بدء التسجيل', 'info');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error starting recording:', error);
      this.addLog(`فشل في بدء التسجيل: ${errorMessage}`, 'error');
    }
  }

  private stopRecording(): void {
    try {
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
      }
      this.isRecording = false;
      this.addLog('تم إيقاف التسجيل', 'info');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error stopping recording:', error);
      this.addLog(`خطأ في إيقاف التسجيل: ${errorMessage}`, 'error');
    }
  }

  // Capture methods
  captureFrame(): void {
    try {
      if (this.isIPStream) {
        this.captureFromIPCamera();
      } else {
        this.captureFromVideoElement();
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error capturing frame:', error);
      this.addLog(`فشل في التقاط الصورة: ${errorMessage}`, 'error');
    }
  }

  private captureFromIPCamera(): void {
    try {
      const img = this.imageElement?.nativeElement;
      if (!img) {
        throw new Error('عنصر الصورة غير متاح');
      }

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        throw new Error('فشل في إنشاء canvas');
      }

      canvas.width = img.naturalWidth || img.width;
      canvas.height = img.naturalHeight || img.height;
      ctx.drawImage(img, 0, 0);

      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const timestamp = new Date();

          this.captures.push({
            url,
            name: `capture_${timestamp.getTime()}`,
            timestamp,
            blob,
            type: 'image'
          });

          this.addLog('تم التقاط الصورة من كاميرا IP', 'success');
        }
      }, 'image/jpeg', 0.9);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      this.addLog(`فشل في التقاط الصورة من كاميرا IP: ${errorMessage}`, 'error');
    }
  }

  private captureFromVideoElement(): void {
    try {
      if (!this.videoElement?.nativeElement) {
        throw new Error('عنصر الفيديو غير متاح');
      }

      const video = this.videoElement.nativeElement;
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        throw new Error('فشل في إنشاء canvas');
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);

      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const timestamp = new Date();

          this.captures.push({
            url,
            name: `capture_${timestamp.getTime()}`,
            timestamp,
            blob,
            type: 'image'
          });

          this.addLog('تم التقاط الصورة', 'success');
        }
      }, 'image/jpeg', 0.9);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      this.addLog(`فشل في التقاط الصورة: ${errorMessage}`, 'error');
    }
  }

  // Media control methods
  toggleFullscreen(): void {
    try {
      const element = this.isIPStream ? 
        this.imageElement?.nativeElement : 
        this.videoElement?.nativeElement;
      
      if (!element) return;

      if (!document.fullscreenElement) {
        element.requestFullscreen();
        this.addLog('تم تفعيل وضع ملء الشاشة', 'info');
      } else {
        document.exitFullscreen();
        this.addLog('تم إلغاء وضع ملء الشاشة', 'info');
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error toggling fullscreen:', error);
      this.addLog(`خطأ في تغيير وضع الشاشة: ${errorMessage}`, 'error');
    }
  }

  toggleMute(): void {
    if (this.isIPStream) {
      this.addLog('كاميرات IP لا تحتوي على صوت عادة', 'info');
      return;
    }

    const video = this.videoElement?.nativeElement;
    if (video) {
      this.isMuted = !this.isMuted;
      video.muted = this.isMuted;
      this.addLog(`تم ${this.isMuted ? 'كتم' : 'إلغاء كتم'} الصوت`, 'info');
    }
  }

  adjustVolume(): void {
    if (this.isIPStream) return;
    
    const video = this.videoElement?.nativeElement;
    if (video) {
      video.volume = this.volume / 100;
    }
  }

  // Capture management methods
  viewCapture(capture: CaptureItem): void {
    window.open(capture.url, '_blank');
  }

  downloadCapture(capture: CaptureItem): void {
    try {
      const link = document.createElement('a');
      link.href = capture.url;
      const extension = capture.type === 'video' ? 'webm' : 'jpg';
      link.download = `${capture.name}.${extension}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      this.addLog(`تم تحميل ${capture.name}`, 'success');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error downloading capture:', error);
      this.addLog(`فشل في تحميل الملف: ${errorMessage}`, 'error');
    }
  }

  deleteCapture(index: number): void {
    try {
      const capture = this.captures[index];
      URL.revokeObjectURL(capture.url);
      this.captures.splice(index, 1);
      this.addLog(`تم حذف ${capture.name}`, 'info');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error deleting capture:', error);
      this.addLog(`فشل في حذف الملف: ${errorMessage}`, 'error');
    }
  }

  clearCaptures(): void {
    try {
      this.captures.forEach(capture => {
        URL.revokeObjectURL(capture.url);
      });
      this.captures = [];
      this.addLog('تم مسح جميع الصور المحفوظة', 'info');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
      console.error('Error clearing captures:', error);
      this.addLog(`فشل في مسح الصور: ${errorMessage}`, 'error');
    }
  }

  // Log management methods
  clearLogs(): void {
    this.logs = [];
  }

  private addLog(message: string, type: LogEntry['type']): void {
    this.logs.unshift({
      timestamp: new Date(),
      message,
      type
    });

    if (this.logs.length > 100) {
      this.logs = this.logs.slice(0, 100);
    }
  }

  // Helper methods
  private getCameraUrl(): string {
    switch (this.selectedCamera) {
      case 'ip':
        return 'http://192.168.1.153:8080/video';
      case 'custom':
        return this.customCameraUrl;
      case 'saved':
        return this.getSavedCameraUrl();
      case 'local':
      default:
        return 'local';
    }
  }

  private getSavedCameraUrl(): string {
    const selectedCamera = this.savedCameras.find(camera => camera._id === this.selectedSavedCameraId);
    if (selectedCamera) {
      // Build URL from saved camera data
      const protocol = 'http'; // You might want to make this configurable
      let baseUrl: string;
      
      // Add authentication if available
      if (selectedCamera.username && selectedCamera.password) {
        baseUrl = `${protocol}://${selectedCamera.username}:${selectedCamera.password}@${selectedCamera.ip}:${selectedCamera.port}`;
      } else {
        baseUrl = `${protocol}://${selectedCamera.ip}:${selectedCamera.port}`;
      }
      
      // Add the video endpoint for IP Webcam
      return `${baseUrl}/video`;
    }
    return '';
  }

  private getCameraDisplayName(): string {
    switch (this.selectedCamera) {
      case 'ip':
        return 'كاميرا IP';
      case 'custom':
        return 'كاميرا مخصصة';
      case 'saved':
        return 'كاميرا محفوظة';
      case 'local':
      default:
        return 'الكاميرا المحلية';
    }
  }

  getQualityDisplayName(): string {
    switch (this.streamQuality) {
      case 'high':
        return 'عالية (1080p)';
      case 'medium':
        return 'متوسطة (720p)';
      case 'low':
        return 'منخفضة (480p)';
      default:
        return 'متوسطة';
    }
  }

  private async startIPCameraStream(url: string): Promise<void> {
    const img = this.imageElement?.nativeElement;
    if (!img) throw new Error('عنصر الصورة غير متاح');

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('انتهت مهلة الاتصال بالكاميرا (15 ثانية)'));
      }, 15000);

      this.isIPStream = true;
      
      // Add detailed logging
      console.log('Attempting to connect to camera URL:', url);
      this.addLog(`محاولة الاتصال بـ: ${url}`, 'info');
      
      img.onload = () => {
        clearTimeout(timeout);
        console.log('Camera stream loaded successfully');
        this.addLog(`تم تحميل بث الكاميرا من ${url}`, 'success');
        
        // Actualiser l'image toutes les 100ms pour simuler le streaming
        this.refreshInterval = setInterval(() => {
          if (this.isStreaming && this.isIPStream) {
            img.src = `${url}?timestamp=${Date.now()}`;
          }
        }, 100);
        
        resolve();
      };

      img.onerror = (event) => {
        clearTimeout(timeout);
        console.error('Image error for IP camera:', url, event);
        
        const errorMessage = `فشل في تحميل بث الكاميرا من ${url}. تحقق من:
        1. تشغيل تطبيق IP Webcam على الهاتف
        2. الاتصال بنفس شبكة WiFi
        3. عنوان IP صحيح (${url})
        4. عدم حجب المتصفح للمحتوى المختلط (HTTP)
        
        جرب الحلول التالية:
        - افتح ${url.replace('/video', '')} في متصفح جديد للتحقق من الاتصال
        - تأكد من تفعيل "Start server" في تطبيق IP Webcam
        - جرب منافذ أخرى (8080, 8081, 9000)
        - جرب ${url.replace('/video', '/shot.jpg')} للحصول على صورة واحدة`;
        
        reject(new Error(errorMessage));
      };

      try {
        // Add timestamp to avoid cache and set image source directly
        img.src = `${url}?timestamp=${Date.now()}`;
      } catch (error: unknown) {
        clearTimeout(timeout);
        const errorMessage = error instanceof Error ? error.message : 'خطأ غير معروف';
        console.error('Error setting image source:', error, 'URL:', url);
        reject(new Error(`خطأ في تعيين مصدر الصورة: ${errorMessage}`));
      }
    });
  }

  private async startLocalCameraStream(): Promise<void> {
    try {
      const constraints = this.getStreamConstraints();

      if (this.selectedDeviceId && constraints.video && typeof constraints.video === 'object') {
        const videoConstraints = constraints.video as MediaTrackConstraints;
        constraints.video = {
          ...videoConstraints,
          deviceId: { exact: this.selectedDeviceId }
        };
      }

      this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      this.isIPStream = false;

      const video = this.videoElement?.nativeElement;
      if (video) {
        video.srcObject = this.mediaStream;
        await video.play();

        const videoTrack = this.mediaStream.getVideoTracks()[0];
        if (videoTrack) {
          const settings = videoTrack.getSettings();
          this.addLog(`الكاميرا: ${videoTrack.label} (${settings.width}x${settings.height})`, 'info');
        }
      }
    } catch (error: unknown) {
      console.error('Error starting local camera:', error);
      if (error instanceof Error) {
        if (error.name === 'NotFoundError') {
          throw new Error('لم يتم العثور على كاميرا');
        } else if (error.name === 'NotAllowedError') {
          throw new Error('تم رفض الوصول للكاميرا - تحقق من الصلاحيات');
        } else if (error.name === 'NotReadableError') {
          throw new Error('الكاميرا قيد الاستخدام من تطبيق آخر');
        } else {
          throw new Error(`خطأ في الكاميرا: ${error.message}`);
        }
      }
      throw new Error('خطأ في الكاميرا: خطأ غير معروف');
    }
  }

  private getStreamConstraints(): MediaStreamConstraints {
    const videoConstraints: MediaTrackConstraints = {
      facingMode: 'user'
    };

    switch (this.streamQuality) {
      case 'high':
        videoConstraints.width = { ideal: 1920 };
        videoConstraints.height = { ideal: 1080 };
        break;
      case 'medium':
        videoConstraints.width = { ideal: 1280 };
        videoConstraints.height = { ideal: 720 };
        break;
      case 'low':
        videoConstraints.width = { ideal: 854 };
        videoConstraints.height = { ideal: 480 };
        break;
    }

    return {
      video: videoConstraints,
      audio: true
    };
  }

  isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return url.startsWith('http://') || url.startsWith('https://');
    } catch {
      return false;
    }
  }

  private startDurationTimer(): void {
    this.durationInterval = setInterval(() => {
      if (this.streamStartTime) {
        const now = new Date();
        const diff = now.getTime() - this.streamStartTime.getTime();
        this.streamDuration = this.formatDuration(diff);
      }
    }, 1000);
  }

  private async testCameraConnection(url: string): Promise<void> {
    try {
      // Test with a simple GET request to check if camera is responding
      const testUrl = url.replace('/video', '/status'); // Try status endpoint first
      const response = await fetch(testUrl, { 
        method: 'GET',
        mode: 'no-cors', // Allow cross-origin
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });
      
      this.addLog('اختبار الاتصال نجح', 'success');
    } catch (error) {
      // If status endpoint fails, try the video endpoint directly
      try {
        const response = await fetch(url, { 
          method: 'HEAD', // Just check if endpoint exists
          mode: 'no-cors',
          signal: AbortSignal.timeout(3000)
        });
        this.addLog('اختبار الاتصال المباشر نجح', 'success');
      } catch (secondError) {
        throw new Error('فشل في الوصول للكاميرا');
      }
    }
  }

  private async tryAlternativeEndpoints(baseUrl: string): Promise<void> {
    const baseUrlWithoutEndpoint = baseUrl.replace('/video', '');
    const alternatives = [
      '/shot.jpg',      // Single frame capture
      '/stream',        // Alternative stream endpoint
      '/mjpeg',         // MJPEG stream
      '/video.mjpeg',   // Another common endpoint
      '/cam.jpg'        // Another single frame option
    ];

    this.addLog('جاري تجربة نقاط نهاية بديلة...', 'info');

    for (const endpoint of alternatives) {
      try {
        const altUrl = baseUrlWithoutEndpoint + endpoint;
        console.log('Trying alternative endpoint:', altUrl);
        this.addLog(`تجربة: ${endpoint}`, 'info');
        
        await this.testAlternativeEndpoint(altUrl);
        
        // If successful, use this endpoint
        const img = this.imageElement?.nativeElement;
        if (img) {
          img.src = `${altUrl}?timestamp=${Date.now()}`;
          this.addLog(`نجح الاتصال عبر: ${endpoint}`, 'success');
          return;
        }
      } catch (error) {
        console.log(`Alternative endpoint ${endpoint} failed:`, error);
      }
    }
    
    throw new Error('فشل في جميع نقاط النهاية البديلة');
  }

  private async testAlternativeEndpoint(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const testImg = new Image();
      const timeout = setTimeout(() => {
        reject(new Error('Timeout'));
      }, 3000);

      testImg.onload = () => {
        clearTimeout(timeout);
        resolve();
      };

      testImg.onerror = () => {
        clearTimeout(timeout);
        reject(new Error('Load failed'));
      };

      testImg.src = `${url}?timestamp=${Date.now()}`;
    });
  }

  private formatDuration(milliseconds: number): string {
    const seconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }

  getConnectionStatusText(): string {
    switch (this.connectionStatus) {
      case 'connected':
        return 'متصل';
      case 'connecting':
        return 'جاري الاتصال';
      case 'error':
        return 'خطأ في الاتصال';
      case 'disconnected':
      default:
        return 'غير متصل';
    }
  }
}