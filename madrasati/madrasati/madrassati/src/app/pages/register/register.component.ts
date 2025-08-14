import { Component, ViewEncapsulation } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from 'src/services/auth.service';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css'],
  encapsulation:ViewEncapsulation.None
})
export class RegisterComponent {
  name = '';
  email = '';
  password = '';
  role = 'teacher';
  error = '';
  success = '';

  constructor(private auth: AuthService, private router: Router) {}

  onRegister() {
    this.auth.register({ name: this.name, email: this.email, password: this.password, role: this.role }).subscribe({
      next: () => {
        this.success = 'Registered successfully!';
        this.router.navigate(['/login']);
      },
      error: (err) => (this.error = err.error?.error || 'Registration failed'),
    });
  }
}
