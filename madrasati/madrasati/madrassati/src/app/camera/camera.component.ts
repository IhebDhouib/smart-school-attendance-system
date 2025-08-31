import { Component, OnInit } from '@angular/core';
import { CameraService, Camera } from 'src/services/camera.service';

@Component({
  selector: 'app-camera',
  templateUrl: './camera.component.html',
  styleUrls: ['./camera.component.css']
})
export class CameraComponent implements OnInit {
  cameras: Camera[] = [];
  newCamera: Camera = {
    name: '',
    ip: '',
    port: 8080,
    username: '',
    password: '',
    classroom: '',
    type: 'entry',
    status: 'inactive'
  };
  
  isEditing = false;
  editingCameraId: string | null = null;
  showTestResult = false;
  testResult = '';
  isTestingConnection = false;

  constructor(private cameraService: CameraService) {}

  ngOnInit() {
    this.getCameras();
  }

  getCameras() {
    this.cameraService.getAllCameras().subscribe({
      next: (data) => {
        this.cameras = data;
      },
      error: (err) => {
        console.error('Error loading cameras:', err);
      }
    });
  }

  addCamera() {
    if (this.validateCamera(this.newCamera)) {
      this.cameraService.addCamera(this.newCamera).subscribe({
        next: (response) => {
          console.log('Camera added successfully:', response);
          this.resetForm();
          this.getCameras();
        },
        error: (err) => {
          console.error('Error adding camera:', err);
          alert('خطأ في إضافة الكاميرا');
        }
      });
    }
  }

  editCamera(camera: Camera) {
    this.isEditing = true;
    this.editingCameraId = camera._id!;
    this.newCamera = { ...camera };
  }

  updateCamera() {
    if (this.validateCamera(this.newCamera) && this.editingCameraId) {
      this.cameraService.updateCamera(this.editingCameraId, this.newCamera).subscribe({
        next: (response) => {
          console.log('Camera updated successfully:', response);
          this.resetForm();
          this.getCameras();
        },
        error: (err) => {
          console.error('Error updating camera:', err);
          alert('خطأ في تحديث الكاميرا');
        }
      });
    }
  }

  deleteCamera(id: string) {
    if (confirm('هل أنت متأكد من حذف هذه الكاميرا؟')) {
      this.cameraService.deleteCamera(id).subscribe({
        next: () => {
          console.log('Camera deleted successfully');
          this.getCameras();
        },
        error: (err) => {
          console.error('Error deleting camera:', err);
          alert('خطأ في حذف الكاميرا');
        }
      });
    }
  }

  testConnection(camera: Camera) {
    this.isTestingConnection = true;
    this.showTestResult = false;
    
    this.cameraService.testConnection(camera).subscribe({
      next: (response) => {
        this.testResult = response.success ? 'تم الاتصال بنجاح' : 'فشل في الاتصال';
        this.showTestResult = true;
        this.isTestingConnection = false;
      },
      error: (err) => {
        this.testResult = 'خطأ في اختبار الاتصال';
        this.showTestResult = true;
        this.isTestingConnection = false;
        console.error('Connection test error:', err);
      }
    });
  }

  validateCamera(camera: Camera): boolean {
    if (!camera.name || !camera.ip) {
      alert('يجب ملء الحقول المطلوبة');
      return false;
    }
    
    // Basic IP validation
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipRegex.test(camera.ip)) {
      alert('عنوان IP غير صحيح');
      return false;
    }
    
    return true;
  }

  resetForm() {
    this.newCamera = {
      name: '',
      ip: '',
      port: 8080,
      username: '',
      password: '',
      classroom: '',
      type: 'entry',
      status: 'inactive'
    };
    this.isEditing = false;
    this.editingCameraId = null;
    this.showTestResult = false;
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'active': return 'status-active';
      case 'inactive': return 'status-inactive';
      case 'error': return 'status-error';
      default: return 'status-unknown';
    }
  }
}
