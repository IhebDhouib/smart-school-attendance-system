import { Component, ViewEncapsulation } from '@angular/core';
import { ClassroomService } from '../../services/classroom.service';
import { ScheduleService } from '../../services/schedule.service';
import { Observable } from 'rxjs';
import { GRADES } from '../models/grades';

export interface Classroom {
  _id: string;
  name: string;
  grade: string;
}
@Component({
  selector: 'app-schedule-upload',
  templateUrl: './schedule-upload.component.html',
  styleUrls: ['./schedule-upload.component.css'],
  encapsulation: ViewEncapsulation.None  // ✅ Ajout de cette ligne

})
export class ScheduleUploadComponent {
  selectedClass: Classroom | null = null;
  className: string = '';
  grade: string = '';
  file: File | null = null;
  loading: boolean = false;
  error: string = '';
  success: string = '';
  grades = GRADES;
  classrooms: Classroom[] = [];


  constructor(
    private classroomService: ClassroomService,
    private scheduleService: ScheduleService,
  ) {}

  ngOnInit(): void {
    this.classroomService.getClassrooms().subscribe({
      next: (classrooms) => {
        this.classrooms = classrooms;
      },
      error: (err) => {
        this.error = 'Failed to load classrooms';
        console.error(err);
      }
    });
  }
  onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.file = input.files[0];
    }
  }

  onSubmit(): void {
    if (!this.file || !this.selectedClass) {
      this.error = 'Please select a classroom and an Excel file';
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';

    this.scheduleService.uploadSchedule(this.file, this.selectedClass.name, this.selectedClass.grade).subscribe({
      next: (response) => {
        this.loading = false;
        this.success = response.message;
        this.selectedClass = null;
        this.file = null;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error.message || 'Failed to upload schedule';
      },
    });
  }
}