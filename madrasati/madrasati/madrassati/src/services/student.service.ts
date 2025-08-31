import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

export interface Classroom {
  _id: string;
  grade: string;
  name: string;

}

export interface Student {
  _id?: string;
  matricule: string;   // <- ajouté
  fullName: string;
  nomPere: string;
  dateNaissance: string;
  photos: string[];
  classId: string | Classroom;
}

@Injectable({
  providedIn: 'root',
})
export class StudentService {
  private apiUrl = `${environment.apiUrl}/students`;

  constructor(private http: HttpClient) {}

  addStudent(formData: FormData): Observable<any> {
    return this.http.post(this.apiUrl, formData);
  }

  getAllStudents(): Observable<any[]> {
    return this.http.get<any[]>(this.apiUrl);
  }

  deleteStudent(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }

  updateStudent(id: string, student: Student): Observable<any> {
    return this.http.put(`${this.apiUrl}/${id}`, student);
  }
  importExcel(formData: FormData): Observable<any> {
  return this.http.post(`${this.apiUrl}/import-excel`, formData);
}

}
