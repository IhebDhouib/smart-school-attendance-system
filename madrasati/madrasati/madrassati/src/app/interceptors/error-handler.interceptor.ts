import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Injectable()
export class ErrorHandlerInterceptor implements HttpInterceptor {

  constructor() {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(request).pipe(
      catchError((error: HttpErrorResponse) => {
        console.warn('Backend connection error intercepted:', error.message);
        
        // If it's a connection error, return mock data instead of failing
        if (error.status === 0 || error.status === 504) {
          console.log('Returning empty response due to backend unavailability');
          
          // Return appropriate mock response based on the URL
          if (request.url.includes('/students')) {
            return of({
              type: 4, // HttpEventType.Response
              body: [],
              status: 200,
              statusText: 'OK (Mock)',
              headers: error.headers,
              url: request.url
            } as any);
          }
          
          if (request.url.includes('/classrooms')) {
            return of({
              type: 4,
              body: [],
              status: 200,
              statusText: 'OK (Mock)',
              headers: error.headers,
              url: request.url
            } as any);
          }
          
          if (request.url.includes('/cameras')) {
            return of({
              type: 4,
              body: [],
              status: 200,
              statusText: 'OK (Mock)',
              headers: error.headers,
              url: request.url
            } as any);
          }
          
          // Default empty response
          return of({
            type: 4,
            body: { success: true, message: 'Mock response - backend unavailable' },
            status: 200,
            statusText: 'OK (Mock)',
            headers: error.headers,
            url: request.url
          } as any);
        }
        
        // For other errors, pass them through
        return throwError(() => error);
      })
    );
  }
}
