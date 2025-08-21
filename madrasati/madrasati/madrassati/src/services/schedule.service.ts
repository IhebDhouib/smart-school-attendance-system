import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ScheduleService {
  private apiUrl = 'http://backend:3000/api/schedules';

  constructor(private http: HttpClient) {}

  getSchedulesByClass(classId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/class/${classId}`);
  }

  getAllSchedules(): Observable<any[]> {
    return this.http.get<any[]>(this.apiUrl);
  }

  uploadSchedule(file: File, className: string, grade: string): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('className', className);
    formData.append('grade', grade);
    return this.http.post(`${this.apiUrl}/upload`, formData);
  }
}
