import { Component, ViewEncapsulation } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from 'src/services/auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
  encapsulation: ViewEncapsulation.Emulated  // Changed to Emulated for scoped styles
})
export class LoginComponent {
  email = '';
  password = '';
  error = '';
  isLoading = false;

  constructor(private auth: AuthService, private router: Router) {}

  onLogin() {
    this.isLoading = true;
    this.error = '';
    
    this.auth.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        this.isLoading = false;
        this.router.navigate(['/teacher']);
      },
      error: (err) => {
        this.isLoading = false;
        this.error = err.error?.error || 'فشل تسجيل الدخول';
      }
    });
  }
}
