import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

interface LoginResponse {
  token: string;
  user: {
    id: string;
    name: string;
    email: string;
    role: string;
  };
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private apiUrl = `${environment.apiUrl}/auth`;

  constructor(private http: HttpClient, private router: Router) {}

  /** Login user and store token + user in localStorage */
  login(credentials: { email: string; password: string }): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/login`, credentials).pipe(
      tap((res) => {
        localStorage.setItem('token', res.token);
        localStorage.setItem('user', JSON.stringify(res.user));
      })
    );
  }

  /** Register a new user (optionally provide role) */
  register(data: { name: string; email: string; password: string; role?: string }): Observable<any> {
    return this.http.post(`${this.apiUrl}/register`, data);
  }

  /** Clears stored auth info */
  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.router.navigate(['/login']);
  }

  /** Check if token exists */
  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }

  /** Get raw token */
  getToken(): string | null {
    return localStorage.getItem('token');
  }

  /** Get stored user */
  getUser(): { id: string; name: string; email: string; role: string } | null {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }
}
