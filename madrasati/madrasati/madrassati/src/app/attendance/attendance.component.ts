import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AttendanceService } from '../../services/attendance.service';
import { ClassroomService } from '../../services/classroom.service';
import { StudentService } from '../../services/student.service';
import { AttendanceWebSocketService } from '../../services/attendance-websocket.service';
import { environment } from '../../environments/environment';

interface Classroom {
  _id: string;
  name: string;
  grade: string;
}

interface Student {
  _id?: string;
  matricule: string;
  fullName: string;
  nomPere: string;
  classId?: string | { _id: string; name?: string; grade?: string };
}

interface AttendanceSummary {
  studentId: string;
  fullName: string;
  nomPere: string;
  isPresent: boolean;
  timestamp: string | null;
  attendanceId: string | null;
}

@Component({
  selector: 'app-attendance',
  templateUrl: './attendance.component.html',
  styleUrls: ['./attendance.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class AttendanceComponent implements OnInit {
  // exposer Math au template pour éviter l'erreur "Property 'Math' does not exist..."
  Math = Math;

  // données
  classrooms: Classroom[] = [];
  students: Student[] = [];
  attendanceSummary: AttendanceSummary[] = [];
  presentCount: number = 0;
  absentCount: number = 0;

  // filtres / dates - unified approach
  selectedClassId: string = '';
  selectedDate: string = ''; // single date that controls both status and records

  // UI / recherche / pagination
  searchTerm: string = '';
  filteredStudents: Student[] = [];
  currentPage: number = 1;
  itemsPerPage: number = 20;
  totalPages: number = 0;

  // état
  loading: boolean = false;
  expandedStudentMatricule: string | null = null;
  studentRecords: { [matricule: string]: any[] } = {}; // cache des enregistrements par étudiant
  private attendanceRecordsSubscription: any;

  constructor(
    private attendanceService: AttendanceService,
    private classroomService: ClassroomService,
    private studentService: StudentService,
    private attendanceWebSocket: AttendanceWebSocketService
  ) {
    // Set default to today
    const today = new Date();
    this.selectedDate = today.toISOString().split('T')[0];
  }

  ngOnInit(): void {
    this.loadClassrooms();
    this.setupWebSocketConnections();
  }

  ngOnDestroy(): void {
    console.log('Destroying attendance component, cleaning up WebSocket subscriptions');
    if (this.attendanceRecordsSubscription) {
      this.attendanceRecordsSubscription.unsubscribe();
    }
    this.attendanceWebSocket.disconnect();
  }

  setupWebSocketConnections() {
    console.log('Setting up WebSocket connection for attendance updates');
    
    // Connect to WebSocket
    this.attendanceWebSocket.connect(environment.websocketUrl);
    
    // Subscribe to attendance updates (handles both records and status)
    this.attendanceRecordsSubscription = this.attendanceWebSocket.connect(environment.websocketUrl)
      .subscribe({
        next: (event: any) => {
          console.log('WebSocket event received:', event);
          if (event && event.type === 'attendance_update') {
            console.log('Attendance update event detected:', {
              eventClassId: event.classId,
              selectedClassId: this.selectedClassId,
              match: event.classId === this.selectedClassId
            });
            if (event.classId === this.selectedClassId) {
              console.log('Reloading attendance due to real-time update');
              // Reload the attendance for current date to get updated data
              this.loadAttendanceForSelectedDate();
            }
          }
        },
        error: (error) => {
          console.error('WebSocket error:', error);
        },
        complete: () => {
          console.log('WebSocket connection completed');
        }
      });
  }

  // Get student status from attendanceSummary - helper for template
  getStudentAttendanceStatus(matricule: string): AttendanceSummary | undefined {
    return this.attendanceSummary.find(summary => summary.studentId === matricule);
  }

  // Simple method to get status for template binding
  isStudentPresent(matricule: string): boolean {
    const status = this.attendanceSummary.find(s => s.studentId === matricule);
    return status ? status.isPresent : false;
  }

  isStudentAbsent(matricule: string): boolean {
    const status = this.attendanceSummary.find(s => s.studentId === matricule);
    return status ? !status.isPresent : false;
  }

  isStudentUnknown(matricule: string): boolean {
    return !this.attendanceSummary.find(s => s.studentId === matricule);
  }

  // load classrooms (safe typing + fallback)
  async loadClassrooms(): Promise<void> {
    try {
      const res: Classroom[] | undefined = await firstValueFrom(this.classroomService.getClassrooms());
      this.classrooms = res ?? []; // fallback to empty array
    } catch (error) {
      console.error('Erreur chargement classes:', error);
      this.classrooms = [];
    }
  }

  // quand on change la classe : charger les étudiants et le résumé de présence pour selectedDate
  async onClassChange(): Promise<void> {
    this.attendanceSummary = [];
    this.students = [];
    this.filteredStudents = [];
    this.currentPage = 1;
    this.studentRecords = {};
    this.expandedStudentMatricule = null;

    if (!this.selectedClassId) return;

    try {
      const allStudents: any[] = (await firstValueFrom(this.studentService.getAllStudents())) ?? [];
      this.students = (allStudents || []).filter(s => {
        const cid = typeof s.classId === 'string' ? s.classId : s.classId?._id;
        return cid === this.selectedClassId;
      });

      this.filteredStudents = [...this.students];
      this.updatePagination();
      
      // Load today's attendance by default
      await this.loadTodaysAttendance();
    } catch (error) {
      console.error('Erreur chargement étudiants:', error);
      this.students = [];
      this.filteredStudents = [];
      this.updatePagination();
    }
  }

  // New unified method: load today's attendance (both status and records)
  async loadTodaysAttendance(): Promise<void> {
    const today = new Date().toISOString().split('T')[0];
    this.selectedDate = today;
    await this.loadAttendanceForSelectedDate();
  }

  // New unified method: load attendance for selected date (both status and records)
  async loadAttendanceForSelectedDate(): Promise<void> {
    if (!this.selectedClassId) return;
    console.log('Loading attendance for date:', this.selectedDate);
    this.loading = true;
    
    // Clear student records cache when date changes
    this.studentRecords = {};
    this.expandedStudentMatricule = null;

    try {
      const res: any = await firstValueFrom(this.attendanceService.getAttendanceByClass(this.selectedClassId, this.selectedDate));
      console.log('Attendance response for date:', this.selectedDate, res);
      this.attendanceSummary = (res?.attendanceSummary as AttendanceSummary[]) ?? [];
      
      // Update present/absent counts
      this.presentCount = this.attendanceSummary.filter(s => s.isPresent).length;
      this.absentCount = this.attendanceSummary.filter(s => !s.isPresent).length;
      
      console.log(`Present: ${this.presentCount}, Absent: ${this.absentCount}`);
      // s'assurer que filteredStudents est cohérent
      this.filterStudents();
    } catch (error) {
      console.error('Erreur chargement présence classe:', error);
      this.attendanceSummary = [];
      this.presentCount = 0;
      this.absentCount = 0;
    } finally {
      this.loading = false;
    }
  }

  // Date change handler - unified approach
  async onDateChange(): Promise<void> {
    if (this.selectedClassId && this.selectedDate) {
      await this.loadAttendanceForSelectedDate();
    }
  }

  // bouton pour afficher l'historique d'un étudiant pour la date sélectionnée
  async viewStudentAttendance(student: { studentId?: string; matricule?: string; fullName?: string }) {
    const mat = student.studentId || student.matricule;
    if (!mat) return;

    // toggle expansion
    if (this.expandedStudentMatricule === mat) {
      this.expandedStudentMatricule = null;
      return;
    }
    this.expandedStudentMatricule = mat;

    // Always fetch fresh data for the selected date
    try {
      const records: any[] = (await firstValueFrom(this.attendanceService.getAttendanceByStudent(mat, this.selectedDate, this.selectedDate, this.selectedClassId))) ?? [];
      this.studentRecords[mat] = records;
    } catch (error) {
      console.error('Erreur chargement enregistrements étudiant:', error);
      this.studentRecords[mat] = [];
    }
  }

  // utilitaires affichage
  isPresent(matricule: string): boolean {
    return !!this.attendanceSummary.find(a => a.studentId === matricule && a.isPresent);
  }
formatTime(ts: string | null): string {
  if (!ts) return '';
  
  try {
    const date = new Date(ts);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return ts ?? '';
    }
    
    // Format date as DD/MM and time as HH:mm
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    
    return `${day}/${month} ${hours}:${minutes}`;
  } catch (error) {
    console.error('Error formatting time:', error);
    return ts ?? '';
  }
}

// Alternative method if you want to include the year
formatTimeWithYear(ts: string | null): string {
  if (!ts) return '';
  
  try {
    const date = new Date(ts);
    
    if (isNaN(date.getTime())) {
      return ts ?? '';
    }
    
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  } catch (error) {
    console.error('Error formatting time:', error);
    return ts ?? '';
  }
}

  // recherche + pagination
  filterStudents(): void {
    let list = [...this.students];
    if (this.searchTerm) {
      const term = this.searchTerm.trim().toLowerCase();
      list = list.filter(s =>
        (s.fullName || '').toLowerCase().includes(term) ||
        (s.matricule || '').toLowerCase().includes(term) ||
        (s.nomPere || '').toLowerCase().includes(term)
      );
    }

    this.filteredStudents = list;
    this.currentPage = 1;
    this.updatePagination();
  }

  updatePagination(): void {
    this.totalPages = Math.max(1, Math.ceil(this.filteredStudents.length / this.itemsPerPage));
  }

  // obtenir les étudiants à afficher sur la page courante
  get pagedStudents(): Student[] {
    const start = (this.currentPage - 1) * this.itemsPerPage;
    return this.filteredStudents.slice(start, start + this.itemsPerPage);
  }

  previousPage(): void {
    if (this.currentPage > 1) this.currentPage--;
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) this.currentPage++;
  }

  // export CSV simple (matricule, nom, nomPere, présent le selectedDate (Oui/Non), count présences pour la date)
  exportToCSV(): void {
    if (!this.selectedClassId) return;
    const headers = ['Matricule', 'Nom Complet', 'Nom du Père', `Présent le ${this.selectedDate}`, `Nombre d'enregistrements le ${this.selectedDate}`];
    const rows: string[] = [headers.join(',')];

    const buildCount = (mat: string) => {
      const arr = this.studentRecords[mat] || [];
      return arr.length.toString();
    };

    this.filteredStudents.forEach(s => {
      const present = this.isPresent(s.matricule) ? 'Oui' : 'Non';
      const count = buildCount(s.matricule);
      const row = [
        `"${s.matricule}"`,
        `"${s.fullName}"`,
        `"${s.nomPere}"`,
        present,
        count
      ];
      rows.push(row.join(','));
    });

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    const fileName = `presences_${this.selectedClassId}_${this.selectedDate}.csv`;
    link.setAttribute('download', fileName);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  trackByStudent(index: number, student: Student) {
    return student._id || student.matricule;
  }
}
