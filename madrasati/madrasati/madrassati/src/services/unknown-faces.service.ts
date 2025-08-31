import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

export interface UnknownFace {
  id: string;
  filename: string;
  timestamp: string;
  size: number;
  path: string;
}

export interface UnknownFacesResponse {
  faces: UnknownFace[];
  total: number;
  directory: string;
  message?: string;
}

export interface UnknownFacesStats {
  total: number;
  today: number;
  this_week: number;
  directory_exists: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class UnknownFacesService {
  // Face detection service runs on port 5001
  private apiUrl = environment.production 
    ? `/unknown-faces-api`  // Will be proxied by nginx
    : 'http://localhost:5001/api/unknown-faces';

  constructor(private http: HttpClient) { }

  /**
   * Get all unknown faces
   */
  getUnknownFaces(): Observable<UnknownFacesResponse> {
    return this.http.get<UnknownFacesResponse>(this.apiUrl);
  }

  /**
   * Get unknown faces statistics
   */
  getStats(): Observable<UnknownFacesStats> {
    return this.http.get<UnknownFacesStats>(`${this.apiUrl}/stats`);
  }

  /**
   * Delete an unknown face
   */
  deleteUnknownFace(filename: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${filename}`);
  }

  /**
   * Get image URL for display
   */
  getImageUrl(filename: string): string {
    return `${this.apiUrl}/image/${filename}`;
  }
}
