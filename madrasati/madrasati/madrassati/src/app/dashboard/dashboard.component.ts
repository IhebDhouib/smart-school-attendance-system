import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit, ViewEncapsulation } from '@angular/core';
import { Router } from '@angular/router';
import { StudentService } from '../../services/student.service';
import { ClassroomService } from '../../services/classroom.service';
import { AttendanceService } from '../../services/attendance.service';
import { interval, Subscription } from 'rxjs';
import { Chart, ChartConfiguration, ChartData, registerables } from 'chart.js';

// Register Chart.js components
Chart.register(...registerables);

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
  totalClasses: number = 0;
  attendanceRate: number = 0;

  // Time and Date
  currentDate: Date = new Date();
  currentTime: string = '';
  private timeSubscription?: Subscription;

  // Charts
  private attendanceChart: any;
  private studentsChart: any;

  constructor(
    private router: Router,
    private studentService: StudentService,
    private classroomService: ClassroomService,
    private attendanceService: AttendanceService
  ) {}

  ngOnInit(): void {
    this.loadDashboardData();
    this.startTimeUpdater();
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
    
    // Clean up charts
    if (this.attendanceChart) {
      this.attendanceChart.destroy();
    }
    if (this.studentsChart) {
      this.studentsChart.destroy();
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
      
      // Get all classes
      const classes = await this.classroomService.getClassrooms().toPromise();
      if (!classes || classes.length === 0) {
        this.attendanceRate = 0;
        return;
      }

      let totalStudents = 0;
      let totalPresent = 0;

      // Calculate attendance rate across all classes
      for (const classroom of classes) {
        try {
          const attendanceData = await this.attendanceService.getAttendanceByClass(classroom._id, today).toPromise();
          if (attendanceData) {
            totalStudents += attendanceData.totalStudents;
            totalPresent += attendanceData.presentStudents;
          }
        } catch (error) {
          console.error(`Error loading attendance for class ${classroom.name}:`, error);
        }
      }

      // Calculate percentage
      this.attendanceRate = totalStudents > 0 ? Math.round((totalPresent / totalStudents) * 100) : 0;
      
    } catch (error) {
      console.error('Error calculating attendance rate:', error);
      this.attendanceRate = 85; // Default value
    }
  }

  private async initializeCharts(): Promise<void> {
    await this.createAttendanceChart();
    await this.createStudentsDistributionChart();
  }

  private async createAttendanceChart(): Promise<void> {
    if (!this.attendanceChartRef?.nativeElement) return;

    // Destroy existing chart if it exists
    if (this.attendanceChart) {
      this.attendanceChart.destroy();
    }

    const ctx = this.attendanceChartRef.nativeElement.getContext('2d');
    if (!ctx) return;

    // Get weekly attendance data
    const weeklyData = await this.getWeeklyAttendanceData();

    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels: ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'],
        datasets: [{
          label: 'معدل الحضور (%)',
          data: weeklyData,
          borderColor: '#667eea',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#667eea',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: {
              callback: function(value) {
                return value + '%';
              }
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          },
          x: {
            grid: {
              display: false
            }
          }
        }
      }
    };

    this.attendanceChart = new Chart(ctx, config);
  }

  private async createStudentsDistributionChart(): Promise<void> {
    if (!this.studentsChartRef?.nativeElement) return;

    // Destroy existing chart if it exists
    if (this.studentsChart) {
      this.studentsChart.destroy();
    }

    const ctx = this.studentsChartRef.nativeElement.getContext('2d');
    if (!ctx) return;

    // Get students distribution data
    const distributionData = await this.getStudentsDistribution();

    const config: ChartConfiguration = {
      type: 'doughnut',
      data: {
        labels: distributionData.labels,
        datasets: [{
          data: distributionData.data,
          backgroundColor: [
            '#667eea',
            '#764ba2',
            '#f093fb',
            '#f5576c',
            '#4facfe',
            '#00f2fe',
            '#43e97b',
            '#38f9d7'
          ],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 20,
              usePointStyle: true
            }
          }
        }
      }
    };

    this.studentsChart = new Chart(ctx, config);
  }

  private async getWeeklyAttendanceData(): Promise<number[]> {
    try {
      // Get the past 7 days
      const weeklyRates: number[] = [];
      const classes = await this.classroomService.getClassrooms().toPromise();
      
      if (!classes || classes.length === 0) {
        return [0, 0, 0, 0, 0, 0, 0];
      }

      for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        const dateString = date.toISOString().split('T')[0];

        let totalStudents = 0;
        let totalPresent = 0;

        // Calculate attendance rate for this date across all classes
        for (const classroom of classes) {
          try {
            const attendanceData = await this.attendanceService.getAttendanceByClass(classroom._id, dateString).toPromise();
            if (attendanceData) {
              totalStudents += attendanceData.totalStudents;
              totalPresent += attendanceData.presentStudents;
            }
          } catch (error) {
            console.error(`Error loading attendance for ${dateString}:`, error);
          }
        }

        const dayRate = totalStudents > 0 ? Math.round((totalPresent / totalStudents) * 100) : 0;
        weeklyRates.push(dayRate);
      }

      return weeklyRates;
    } catch (error) {
      console.error('Error loading weekly attendance data:', error);
      return [85, 88, 92, 87, 90, 89, 91]; // Fallback data
    }
  }

  private async getStudentsDistribution(): Promise<{labels: string[], data: number[]}> {
    try {
      // Get all classrooms and count students in each
      const classrooms = await this.classroomService.getClassrooms().toPromise();
      const allStudents = await this.studentService.getAllStudents().toPromise();
      
      if (!classrooms || !allStudents) {
        return { labels: [], data: [] };
      }

      const distribution = classrooms.map(classroom => {
        const studentsInClass = allStudents.filter(student => {
          // Handle both string and object classId
          const studentClassId = typeof student.classId === 'string' 
            ? student.classId 
            : student.classId?._id;
          return studentClassId === classroom._id;
        });
        
        return {
          label: `${classroom.name} - ${classroom.grade}`,
          count: studentsInClass.length
        };
      }).filter(item => item.count > 0); // Only show classes with students

      return {
        labels: distribution.map(item => item.label),
        data: distribution.map(item => item.count)
      };
    } catch (error) {
      console.error('Error loading students distribution:', error);
      return {
        labels: ['الصف الأول', 'الصف الثاني', 'الصف الثالث'],
        data: [25, 30, 20] // Fallback data
      };
    }
  }

  // Navigation methods
  navigateTo(route: string): void {
    this.router.navigate([route]);
  }
}

