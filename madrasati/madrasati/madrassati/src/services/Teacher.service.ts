import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Teacher {
  userId: string;
  firstName: string;
  lastName: string;
  subject: string;
  photo?: string;
}

@Injectable({
  providedIn: 'root'
})
export class TeacherService {
  private apiUrl = 'http://backend:3000/api/teachers'; // Make sure this matches your backend path

  constructor(private http: HttpClient) {}

  // Get all teachers
  getTeachers(): Observable<Teacher[]> {
    return this.http.get<Teacher[]>(this.apiUrl);
  }

  // Get a single teacher by userId (optional)
  getOne(userId: string): Observable<Teacher> {
    return this.http.get<Teacher>(`${this.apiUrl}/${userId}`);
  }

  // Create a new teacher with optional photo file
  createTeacher(teacher: Teacher, file?: File): Observable<Teacher> {
    const formData = new FormData();
    formData.append('userId', teacher.userId);
    formData.append('firstName', teacher.firstName);
    formData.append('lastName', teacher.lastName);
    formData.append('subject', teacher.subject);
    if (file) formData.append('photo', file);

    return this.http.post<Teacher>(this.apiUrl, formData);
  }

  // Update an existing teacher by userId with optional photo file
  updateTeacher(userId: string, teacher: Teacher, file?: File): Observable<Teacher> {
    const formData = new FormData();
    formData.append('userId', teacher.userId);
    formData.append('firstName', teacher.firstName);
    formData.append('lastName', teacher.lastName);
    formData.append('subject', teacher.subject);
    if (file) formData.append('photo', file);

    return this.http.put<Teacher>(`${this.apiUrl}/${userId}`, formData);
  }

  // Delete teacher by userId
  deleteTeacher(userId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${userId}`);
  }
}
