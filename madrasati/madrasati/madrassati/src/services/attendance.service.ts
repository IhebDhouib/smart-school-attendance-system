// attendance.service.ts
import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../environments/environment';

export interface AttendanceRecord {
  _id: string;
  studentId: string;
  classId: any;
  timestamp: string;
}

export interface AttendanceSummary {
  studentId: string;
  fullName: string;
  nomPere: string;
  isPresent: boolean;
  timestamp: string | null;
  attendanceId: string | null;
}

export interface ClassAttendanceResponse {
  classInfo: any | null;
  attendanceSummary: AttendanceSummary[];
  totalStudents: number;
  presentStudents: number;
  absentStudents: number;
}

@Injectable({ providedIn: 'root' })
export class AttendanceService {
  private apiUrl = `${environment.apiUrl}/attendance`;

  constructor(private http: HttpClient) {}

  /**
   * Récupération du résumé de présence pour une classe (et optionnellement pour une date précise).
   * Renvoie toujours un ClassAttendanceResponse (pas undefined).
   */
  getAttendanceByClass(classId: string, date?: string): Observable<ClassAttendanceResponse> {
    let params = new HttpParams();
    if (date) params = params.set('date', date);

    return this.http
      .get<ClassAttendanceResponse>(`${this.apiUrl}/class/${classId}`, { params })
      .pipe(
        map(res => res ?? {
          classInfo: null,
          attendanceSummary: [],
          totalStudents: 0,
          presentStudents: 0,
          absentStudents: 0
        })
      );
  }

  /**
   * Récupérer les présences d'un étudiant sur une période (retourne toujours un tableau, potentiellement vide).
   */
  getAttendanceByStudent(matricule: string, startDate?: string, endDate?: string, classId?: string): Observable<AttendanceRecord[]> {
    let params = new HttpParams();
    if (startDate) params = params.set('startDate', startDate);
    if (endDate) params = params.set('endDate', endDate);
    if (classId) params = params.set('classId', classId);

    return this.http
      .get<AttendanceRecord[]>(`${this.apiUrl}/student/${matricule}`, { params })
      .pipe(map(res => res ?? []));
  }

  /**
   * Création d'un enregistrement de présence.
   */
  createAttendance(data: { studentId: string; classId: string }) {
    return this.http.post<AttendanceRecord>(`${this.apiUrl}`, data);
  }

  /**
   * Suppression d'un enregistrement (retour flexible selon ton API).
   */
  deleteAttendance(id: string) {
    return this.http.delete<{ message?: string }>(`${this.apiUrl}/${id}`);
  }

  /**
   * Helper: récupérer les présences sur une plage de dates (toujours tableau).
   */
  getAttendanceByDateRange(startDate: string, endDate: string, classId?: string): Observable<AttendanceRecord[]> {
    let params = new HttpParams().set('startDate', startDate).set('endDate', endDate);
    if (classId) params = params.set('classId', classId);

    return this.http
      .get<AttendanceRecord[]>(`${this.apiUrl}/date-range`, { params })
      .pipe(map(res => res ?? []));
  }

  /**
   * Get current status for all students in a class (present/absent based on latest entry/exit)
   */
  getCurrentStatusByClass(classId: string): Observable<ClassAttendanceResponse> {
    return this.http
      .get<ClassAttendanceResponse>(`${this.apiUrl}/class/${classId}/current-status`)
      .pipe(
        map(res => res ?? {
          classInfo: null,
          attendanceSummary: [],
          totalStudents: 0,
          presentStudents: 0,
          absentStudents: 0
        })
      );
  }
}
