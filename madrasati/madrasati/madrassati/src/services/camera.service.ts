import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

export interface Camera {
  _id?: string;
  name: string;
  ip: string;
  port: number;
  username: string;
  password: string;
  classroom: string;
  type: 'entry' | 'exit';
  status: 'active' | 'inactive' | 'error';
  createdAt?: Date;
  updatedAt?: Date;
}

@Injectable({
  providedIn: 'root',
})
export class CameraService {
  private apiUrl = `${environment.apiUrl}/cameras`;

  constructor(private http: HttpClient) {}

  getAllCameras(): Observable<Camera[]> {
    return this.http.get<Camera[]>(this.apiUrl);
  }

  addCamera(camera: Camera): Observable<any> {
    return this.http.post(this.apiUrl, camera);
  }

  updateCamera(id: string, camera: Camera): Observable<any> {
    return this.http.put(`${this.apiUrl}/${id}`, camera);
  }

  deleteCamera(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }

  testConnection(camera: Camera): Observable<any> {
    return this.http.post(`${this.apiUrl}/test-connection`, {
      ip: camera.ip,
      port: camera.port,
      username: camera.username,
      password: camera.password
    });
  }
}
