import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class ClassroomService {
  private apiUrl = `${environment.apiUrl}/classrooms`;

  constructor(private http: HttpClient) {}

  getClassrooms(): Observable<any[]> {
    return this.http.get<any[]>(this.apiUrl);
  }

   getClassroomByNameAndGrade(name: string, grade: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/name/${encodeURIComponent(name)}`, {
      params: { grade: encodeURIComponent(grade) },
    });
  }

  createClassroom(data: { name: string; grade: string }): Observable<any> {
    return this.http.post(this.apiUrl, data);
  }

  deleteClassroom(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }
}
