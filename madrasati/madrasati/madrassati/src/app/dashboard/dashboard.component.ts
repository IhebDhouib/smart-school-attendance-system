import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit, ViewEncapsulation } from '@angular/core';
import { Router } from '@angular/router';
import { StudentService } from '../../services/student.service';
import { ClassroomService } from '../../services/classroom.service';
import { AttendanceService } from '../../services/attendance.service';
import { TeacherService } from '../../services/Teacher.service';
import { interval, Subscription } from 'rxjs';

interface Activity {
  id: string;
  type: 'student' | 'teacher' | 'attendance' | 'system';
  title: string;
  description: string;
  timestamp: Date;
}

interface Alert {
  id: string;
  type: 'warning' | 'danger' | 'info';
  title: string;
  message: string;
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
  encapsulation:ViewEncapsulation.None
})
export class DashboardComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('attendanceChart', { static: false }) attendanceChartRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('studentsChart', { static: false }) studentsChartRef!: ElementRef<HTMLCanvasElement>;

  // Statistics
  totalStudents: number = 0;
  totalTeachers: number = 0;
  totalClasses: number = 0;
  attendanceRate: number = 0;

  // Time and Date
  currentDate: Date = new Date();
  currentTime: string = '';
  private timeSubscription?: Subscription;

  // Activities and Alerts
  recentActivities: Activity[] = [];
  alerts: Alert[] = [];

  // Charts
  private attendanceChart: any;
  private studentsChart: any;

  constructor(
    private router: Router,
    private studentService: StudentService,
    private classroomService: ClassroomService,
    private attendanceService: AttendanceService,
    private teacherService: TeacherService
  ) {}

  ngOnInit(): void {
    this.loadDashboardData();
    this.startTimeUpdater();
    this.loadRecentActivities();
    this.loadAlerts();
  }

  ngAfterViewInit(): void {
    // Initialize charts after view is ready
    setTimeout(() => {
      this.initializeCharts();
    }, 100);
  }

  ngOnDestroy(): void {
    if (this.timeSubscription) {
      this.timeSubscription.unsubscribe();
    }
  }

  private startTimeUpdater(): void {
    this.updateTime();
    this.timeSubscription = interval(1000).subscribe(() => {
      this.updateTime();
    });
  }

  private updateTime(): void {
  const now = new Date();
  this.currentTime = now.toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
  
  // Optionnel: Mise à jour de la date actuelle aussi en français
  this.currentDate = now;
}

  private async loadDashboardData(): Promise<void> {
    try {
      // Load students count
      const students = await this.studentService.getAllStudents().toPromise();
      this.totalStudents = students?.length || 0;

      // Load teachers count
      const teachers = await this.teacherService.getTeachers().toPromise();
      this.totalTeachers = teachers?.length || 0;

      // Load classes count
      const classes = await this.classroomService.getClassrooms().toPromise();
      this.totalClasses = classes?.length || 0;

      // Calculate today's attendance rate
      await this.calculateTodayAttendanceRate();

    } catch (error) {
      console.error('Error loading dashboard data:', error);
    }
  }

  private async calculateTodayAttendanceRate(): Promise<void> {
    try {
      const today = new Date().toISOString().split('T')[0];
      const params = {
        startDate: today,
        endDate: today
      };

      // This would need to be implemented in the attendance service
      // For now, we'll use a mock calculation
      this.attendanceRate = Math.floor(Math.random() * 20) + 80; // 80-100%
    } catch (error) {
      console.error('Error calculating attendance rate:', error);
      this.attendanceRate = 85; // Default value
    }
  }

  private loadRecentActivities(): void {
    // Mock data for recent activities
    this.recentActivities = [
      {
        id: '1',
        type: 'student',
        title: 'طالب جديد مسجل',
        description: 'تم تسجيل أحمد محمد في الصف الثالث الابتدائي',
        timestamp: new Date(Date.now() - 1000 * 60 * 30) // 30 minutes ago
      },
      {
        id: '2',
        type: 'attendance',
        title: 'تسجيل حضور',
        description: 'تم تسجيل حضور 25 طالب في الصف الثاني',
        timestamp: new Date(Date.now() - 1000 * 60 * 60) // 1 hour ago
      },
      {
        id: '3',
        type: 'teacher',
        title: 'معلم جديد',
        description: 'انضمت فاطمة أحمد كمعلمة رياضيات',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2) // 2 hours ago
      },
      {
        id: '4',
        type: 'system',
        title: 'تحديث النظام',
        description: 'تم تحديث نظام إدارة الحضور بنجاح',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4) // 4 hours ago
      }
    ];
  }

  private loadAlerts(): void {
    // Mock data for alerts
    this.alerts = [
      {
        id: '1',
        type: 'warning',
        title: 'انخفاض معدل الحضور',
        message: 'معدل الحضور في الصف الأول أقل من 80% هذا الأسبوع'
      },
      {
        id: '2',
        type: 'info',
        title: 'اجتماع المعلمين',
        message: 'اجتماع المعلمين الأسبوعي غداً الساعة 10:00 صباحاً'
      }
    ];
  }

  private initializeCharts(): void {
    // Mock chart initialization
    // In a real implementation, you would use Chart.js or similar library
    console.log('Charts would be initialized here');
  }

  // Navigation methods
  navigateTo(route: string): void {
    this.router.navigate([route]);
  }

  viewAllActivities(): void {
    // Navigate to activities page or show modal
    console.log('View all activities');
  }

  generateReport(): void {
    // Generate and download report
    console.log('Generate report');
  }

  // Activity helpers
  getActivityIcon(type: string): string {
    switch (type) {
      case 'student':
        return 'fa-user-graduate';
      case 'teacher':
        return 'fa-chalkboard-teacher';
      case 'attendance':
        return 'fa-check-circle';
      case 'system':
        return 'fa-cog';
      default:
        return 'fa-info-circle';
    }
  }

  // Alert helpers
  getAlertIcon(type: string): string {
    switch (type) {
      case 'warning':
        return 'fa-exclamation-triangle';
      case 'danger':
        return 'fa-times-circle';
      case 'info':
        return 'fa-info-circle';
      default:
        return 'fa-bell';
    }
  }

  dismissAlert(alertId: string): void {
    this.alerts = this.alerts.filter(alert => alert.id !== alertId);
  }
}

