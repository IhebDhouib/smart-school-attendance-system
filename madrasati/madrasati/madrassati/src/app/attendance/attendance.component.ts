import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { AttendanceService } from '../../services/attendance.service';
import { ClassroomService } from '../../services/classroom.service';
import { ScheduleService } from '../../services/schedule.service';
import { StudentService } from '../../services/student.service';

interface Classroom {
  _id: string;
  name: string;
  grade: string;
}

interface Schedule {
  _id: string;
  subject: string;
  day: string;
  startTime: string;
  endTime: string;
  classId: string;
}

interface Student {
  _id?: string;
  matricule: string;
  fullName: string;
  nomPere: string;
  classId?: string | { _id: string; name?: string; grade?: string };
}

interface AttendanceRecord {
  studentId: string;
  classId: string;
  scheduleId: string;
  timestamp: string;
}

interface AttendanceMatrix {
  [studentMatricule: string]: {
    [date: string]: {
      present: boolean;
      timestamp?: string;
    }
  }
}

@Component({
  selector: 'app-attendance',
  templateUrl: './attendance.component.html',
  styleUrls: ['./attendance.component.css'],
  encapsulation:ViewEncapsulation.None
})
export class AttendanceComponent implements OnInit {
  // Data properties
  classrooms: any[] = [];
  classSchedules: any[] = [];
  students: any[] = [];
  attendanceData: any[] = [];
  attendanceMatrix: AttendanceMatrix = {};
  
  // Filter properties
  selectedClassId: string = '';
  selectedSubjectId: string = '';
  startDate: string = '';
  endDate: string = '';
  searchTerm: string = '';
  
  // Display properties
  lessonDates: string[] = [];
  filteredStudents: any[] = [];
  
  // Statistics
  totalStudents: number = 0;
  averagePresent: number = 0;
  averageAbsent: number = 0;
  attendanceRate: number = 0;
  
  // Pagination
  currentPage: number = 1;
  itemsPerPage: number = 20;
  totalPages: number = 0;
  
  // State
  isLoading: boolean = false;
  Math = Math;

  constructor(
    private attendanceService: AttendanceService,
    private classroomService: ClassroomService,
    private scheduleService: ScheduleService,
    private studentService: StudentService
  ) {
    // Set default date range (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    this.endDate = today.toISOString().split('T')[0];
    this.startDate = thirtyDaysAgo.toISOString().split('T')[0];
  }

  ngOnInit(): void {
    this.loadClassrooms();
  }

  async loadClassrooms(): Promise<void> {
    try {
      const classrooms = await this.classroomService.getClassrooms().toPromise();
      this.classrooms = classrooms || [];
    } catch (error) {
      console.error('Error loading classrooms:', error);
    }
  }

  async onClassChange(): Promise<void> {
    this.selectedSubjectId = '';
    this.classSchedules = [];
    this.students = [];
    this.attendanceData = [];
    this.lessonDates = [];
    this.filteredStudents = [];
    
    if (this.selectedClassId) {
      await this.loadClassSchedules();
      await this.loadStudents();
    }
  }

  async loadClassSchedules(): Promise<void> {
    try {
      const schedules = await this.scheduleService.getSchedulesByClass(this.selectedClassId).toPromise();
      this.classSchedules = schedules || [];
    } catch (error) {
      console.error('Error loading schedules:', error);
    }
  }

  async loadStudents(): Promise<void> {
    try {
      const allStudents = await this.studentService.getAllStudents().toPromise();
     this.students = (allStudents || []).filter((student: Student) => {
        const studentClassId = typeof student.classId === 'string' ? student.classId : student.classId?._id;
        console.log('Comparing student classId:', studentClassId, 'with selectedClassId:', this.selectedClassId);
        return studentClassId === this.selectedClassId;
      });      this.totalStudents = this.students.length;
      this.filteredStudents = [...this.students];
      console.log(allStudents);
      console.log(this.students);
    } catch (error) {
      console.error('Error loading students:', error);
    }
  }

  onSubjectChange(): void {
    this.attendanceData = [];
    this.lessonDates = [];
    this.attendanceMatrix = {};
  }

  onDateRangeChange(): void {
    if (this.selectedClassId && this.selectedSubjectId) {
      this.generateLessonDates();
    }
  }

  generateLessonDates(): void {
    if (!this.selectedSubjectId || !this.startDate || !this.endDate) {
      return;
    }

    const selectedSchedule = this.classSchedules.find(s => s._id === this.selectedSubjectId);
    if (!selectedSchedule) {
      console.log("houni lmochkla");
      return;
    }
    console.log(selectedSchedule);
    const dates: string[] = [];
    const start = new Date(this.startDate);
    const end = new Date(this.endDate);
    
    // Map day names to numbers (0 = Sunday, 1 = Monday, etc.)
    const dayMap: { [key: string]: number } = {
      'Dimanche': 0, 'Lundi': 1, 'Mardi': 2, 'Mercredi': 3,
      'Jeudi': 4, 'Vendredi': 5, 'Samedi': 6
    };
    
    const targetDay = dayMap[selectedSchedule.day];
    if (targetDay === undefined) {
      return;
    }

    // Find all dates that match the schedule day
    const current = new Date(start);
    while (current <= end) {
      if (current.getDay() === targetDay) {
        dates.push(current.toISOString().split('T')[0]);
      }
      current.setDate(current.getDate() + 1);
    }

    this.lessonDates = dates;
  }

  async loadAttendanceData(): Promise<void> {
    if (!this.selectedClassId || !this.selectedSubjectId) {
      return;
    }

    this.isLoading = true;
    this.generateLessonDates();

    try {
      // Load attendance data for the date range
      const params = {
        classId: this.selectedClassId,
        scheduleId: this.selectedSubjectId,
        startDate: this.startDate,
        endDate: this.endDate
      };

      const attendanceData = await this.attendanceService.getAttendanceByDateRange(params).toPromise();
      this.attendanceData = attendanceData || [];
      console.log(this.attendanceData);
      this.buildAttendanceMatrix();
      this.calculateStatistics();
      this.filterStudents();
    } catch (error) {
      console.error('Error loading attendance data:', error);
    } finally {
      this.isLoading = false;
    }
  }

buildAttendanceMatrix(): void {
    this.attendanceMatrix = {};

    // Initialize matrix for all students and dates
    this.students.forEach(student => {
      this.attendanceMatrix[student.matricule] = {};
      this.lessonDates.forEach(date => {
        this.attendanceMatrix[student.matricule][date] = { present: false };
      });
    });

    // Fill matrix with actual attendance data
    this.attendanceData.forEach(record => {
      const student = this.students.find(s => s.matricule === record.studentId);
      if (student) {
        const date = new Date(record.timestamp).toISOString().split('T')[0];
        if (this.attendanceMatrix[student.matricule] && this.attendanceMatrix[student.matricule][date]) {
          this.attendanceMatrix[student.matricule][date] = {
            present: true,
            timestamp: record.timestamp
          };
        }
      }
    });

    console.log('Attendance matrix:', this.attendanceMatrix);
  }

  calculateStatistics(): void {
    if (this.lessonDates.length === 0 || this.students.length === 0) {
      this.averagePresent = 0;
      this.averageAbsent = 0;
      this.attendanceRate = 0;
      return;
    }

    let totalPresent = 0;
    let totalPossible = this.students.length * this.lessonDates.length;

    this.students.forEach(student => {
      this.lessonDates.forEach(date => {
        if (this.attendanceMatrix[student.matricule] && 
            this.attendanceMatrix[student.matricule][date] && 
            this.attendanceMatrix[student.matricule][date].present) {
          totalPresent++;
        }
      });
    });

    this.averagePresent = Math.round(totalPresent / this.students.length);
    this.averageAbsent = Math.round((this.students.length * this.lessonDates.length - totalPresent) / this.students.length);
    this.attendanceRate = Math.round((totalPresent / totalPossible) * 100);
  }

  filterStudents(): void {
    let filtered = [...this.students];

    if (this.searchTerm) {
      const term = this.searchTerm.toLowerCase();
      filtered = filtered.filter(student =>
        student.fullName.toLowerCase().includes(term) ||
        student.matricule.toLowerCase().includes(term) ||
        student.nomPere.toLowerCase().includes(term)
      );
    }

    this.filteredStudents = filtered;
    this.totalPages = Math.ceil(this.filteredStudents.length / this.itemsPerPage);
    this.currentPage = 1;
  }

  isPresent(matricule: string, date: string): boolean {
    return this.attendanceMatrix[matricule] && 
           this.attendanceMatrix[matricule][date] && 
           this.attendanceMatrix[matricule][date].present;
  }

  getAttendanceStatus(matricule: string, date: string): string {
    return this.isPresent(matricule, date) ? 'present' : 'absent';
  }

  getAttendanceTooltip(matricule: string, date: string): string {
    if (this.isPresent(matricule, date)) {
      const timestamp = this.attendanceMatrix[matricule][date].timestamp;
      if (timestamp) {
        const time = new Date(timestamp).toLocaleTimeString('fr-FR', { 
          hour: '2-digit', 
          minute: '2-digit' 
        });
        return `Présent à ${time}`;
      }
      return 'Présent';
    }
    return 'Absent';
  }

  formatDateDay(date: string): string {
    const d = new Date(date);
    const days = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
    return days[d.getDay()];
  }

  formatDateFull(date: string): string {
    const d = new Date(date);
    return d.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: '2-digit' 
    });
  }

  trackByStudentId(index: number, student: any): string {
    return student._id;
  }

  // Pagination methods
  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  exportToCSV(): void {
    if (this.filteredStudents.length === 0 || this.lessonDates.length === 0) {
      return;
    }

    const headers = ['Matricule', 'Nom Complet', 'Nom du Père', ...this.lessonDates.map(date => this.formatDateFull(date))];
    const csvContent = [headers.join(',')];

    this.filteredStudents.forEach(student => {
      const row = [
        student.matricule,
        `"${student.fullName}"`,
        `"${student.nomPere}"`,
        ...this.lessonDates.map(date => this.isPresent(student.matricule, date) ? 'Présent' : 'Absent')
      ];
      csvContent.push(row.join(','));
    });

    const blob = new Blob([csvContent.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `presences_${this.selectedClassId}_${this.selectedSubjectId}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

