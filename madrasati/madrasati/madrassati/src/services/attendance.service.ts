import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface AttendanceRecord {
  _id: string;
  studentId: string;
  classId: any;
  scheduleId: any;
  timestamp: Date;
}

export interface AttendanceSummary {
  studentId: string;
  fullName: string;
  nomPere: string;
  isPresent: boolean;
  timestamp: Date | null;
  attendanceId: string | null;
}

export interface ClassAttendanceResponse {
  classInfo: any;
  scheduleInfo: any;
  attendanceSummary: AttendanceSummary[];
  totalStudents: number;
  presentStudents: number;
  absentStudents: number;
}

export interface AttendanceStats {
  totalStudents: number;
  attendanceByDate: any;
  overallStats: {
    totalDays: number;
    averageAttendance: number;
  };
}

@Injectable({ providedIn: 'root' })
export class AttendanceService {
  private apiUrl = 'http://localhost:3000/api/attendance';

  constructor(private http: HttpClient) {}

  // Get all attendance records
  getAllAttendance(): Observable<AttendanceRecord[]> {
    return this.http.get<AttendanceRecord[]>(this.apiUrl);
  }

  // Get attendance records by class ID
  getAttendanceByClass(classId: string, date?: string, scheduleId?: string): Observable<ClassAttendanceResponse> {
    let params: any = {};
    if (date) params.date = date;
    if (scheduleId) params.scheduleId = scheduleId;
    
    return this.http.get<ClassAttendanceResponse>(`${this.apiUrl}/class/${classId}`, { params });
  }

  // Get attendance records by date range
  getAttendanceByDateRange(params: { classId: string, scheduleId: string, startDate: string, endDate: string }): Observable<AttendanceRecord[]> {
    return this.http.get<AttendanceRecord[]>(this.apiUrl, { params });
  }

  // Get attendance statistics for a class
  getAttendanceStats(classId: string, startDate?: string, endDate?: string): Observable<AttendanceStats> {
    let params: any = {};
    if (startDate) params.startDate = startDate;
    if (endDate) params.endDate = endDate;
    
    return this.http.get<AttendanceStats>(`${this.apiUrl}/stats/${classId}`, { params });
  }

  // Create new attendance record
  createAttendance(data: { studentId: string; classId: string; scheduleId: string }): Observable<AttendanceRecord> {
    return this.http.post<AttendanceRecord>(this.apiUrl, data);
  }

  // Delete attendance record
  deleteAttendance(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }
}

