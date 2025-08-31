import { Injectable, NgZone } from '@angular/core';
import { Observable, Subject, timer } from 'rxjs';
import { filter } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class AttendanceWebSocketService {
  private ws: WebSocket | null = null;
  private subject = new Subject<any>();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;

  constructor(private ngZone: NgZone) {}

  connect(url: string): Observable<any> {
    if (this.ws) {
      this.ws.close();
    }
    
    console.log('Connecting to WebSocket:', url);
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected successfully');
      this.resetReconnectAttempts();
    };
    
    this.ws.onmessage = (event) => {
      console.log('WebSocket message received:', event.data);
      this.ngZone.run(() => {
        try {
          const data = JSON.parse(event.data);
          console.log('Parsed WebSocket data:', data);
          this.subject.next(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      });
    };
    
    this.ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      this.ngZone.run(() => {
        this.subject.error(event);
      });
    };
    
    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.ngZone.run(() => {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          timer(this.reconnectInterval).subscribe(() => {
            this.connect(url);
          });
        } else {
          console.log('Max reconnection attempts reached');
          this.subject.complete();
        }
      });
    };
    
    return this.subject.asObservable();
  }

  // Get attendance record updates (new records)
  getAttendanceRecords(): Observable<any> {
    return this.subject.asObservable().pipe(
      filter(data => data.type === 'attendance_record')
    );
  }

  // Get status updates (present/absent changes)
  getStatusUpdates(): Observable<any> {
    return this.subject.asObservable().pipe(
      filter(data => data.type === 'status_update')
    );
  }

  private resetReconnectAttempts() {
    this.reconnectAttempts = 0;
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
