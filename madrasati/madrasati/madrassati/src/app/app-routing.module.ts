import { NgModule } from '@angular/core';
import { LoginComponent } from './pages/login/login.component';
import { RegisterComponent } from './pages/register/register.component';
import { AuthGuard } from 'src/guards/auth.guard';
import { RouterModule, Routes } from '@angular/router';
import { ClassroomComponent } from './classroom/classroom.component';
import { StudentComponent } from './student/student.component';
import { AttendanceComponent } from './attendance/attendance.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { CameraComponent } from './camera/camera.component';
import { CameraFeedComponent } from './camera-feed/camera-feed.component';
import { UnknownFacesComponent } from './unknown-faces/unknown-faces.component';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
  { path: 'class', component: ClassroomComponent, canActivate: [AuthGuard] },
  { path: 'student', component: StudentComponent, canActivate: [AuthGuard] },
  { path: 'attendance', component: AttendanceComponent, canActivate: [AuthGuard] },
  { path: 'camera', component: CameraComponent, canActivate: [AuthGuard] },
  { path: 'camera-feed', component: CameraFeedComponent, canActivate: [AuthGuard] },
  { path: 'unknown-faces', component: UnknownFacesComponent, canActivate: [AuthGuard] },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' }, // Default route
  { path: '**', redirectTo: 'dashboard' } // Wildcard fallback
];
@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }