import { Component, OnInit, ViewChild, ElementRef, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, NgForm } from '@angular/forms';
import { Teacher, TeacherService } from 'src/services/Teacher.service';

@Component({
  selector: 'app-teacher',
  standalone: true,
  imports: [CommonModule, FormsModule], // ✅ Add required modules
  templateUrl: './teacher.component.html',
  styleUrls: ['./teacher.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class TeacherComponent implements OnInit {
  teachers: Teacher[] = [];
  selectedTeacher: Teacher = { userId: '', firstName: '', lastName: '', subject: '' };
  selectedFile?: File;
  imagePreview: string | null = null;
  isEditing = false;
  errorMessage: string | null = null;
  backendUrl = 'http://localhost:3000';
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  constructor(private teacherService: TeacherService) {}

  ngOnInit(): void {
    this.loadTeachers();
  }

  loadTeachers(): void {
    this.teacherService.getTeachers().subscribe({
      next: (data) => (this.teachers = data),
      error: (err) => {
        this.errorMessage = 'Erreur lors du chargement des enseignants : ' + err.message;
      },
    });
  }

  selectTeacher(teacher: Teacher): void {
    this.selectedTeacher = { ...teacher };
    this.selectedFile = undefined;
    this.imagePreview = null;
    this.isEditing = true;
    this.errorMessage = null;
    if (this.fileInput) this.fileInput.nativeElement.value = '';
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile = input.files?.[0];
    this.imagePreview = this.selectedFile ? URL.createObjectURL(this.selectedFile) : null;
  }

  saveTeacher(form: NgForm): void {
    if (!form.valid) {
      this.errorMessage = 'Veuillez remplir tous les champs.';
      return;
    }

    if (this.isEditing) {
      this.teacherService
        .updateTeacher(this.selectedTeacher.userId, this.selectedTeacher, this.selectedFile)
        .subscribe({
          next: () => {
            this.loadTeachers();
            this.resetForm();
          },
          error: (err) => {
            this.errorMessage = err.error?.message || err.message;
          },
        });
    } else {
      this.teacherService.createTeacher(this.selectedTeacher, this.selectedFile).subscribe({
        next: () => {
          this.loadTeachers();
          this.resetForm();
        },
        error: (err) => {
          this.errorMessage = err.error?.message || err.message;
        },
      });
    }
  }

  deleteTeacher(userId: string): void {
    if (confirm('Supprimer cet enseignant ?')) {
      this.teacherService.deleteTeacher(userId).subscribe({
        next: () => {
          this.loadTeachers();
        },
        error: (err) => {
          this.errorMessage = err.error?.message || err.message;
        },
      });
    }
  }

  resetForm(): void {
    this.selectedTeacher = { userId: '', firstName: '', lastName: '', subject: '' };
    this.selectedFile = undefined;
    this.imagePreview = null;
    this.isEditing = false;
    this.errorMessage = null;
    if (this.fileInput) this.fileInput.nativeElement.value = '';
  }

  getImageUrl(photoPath: string | undefined): string {
    return photoPath ? `${this.backendUrl}${photoPath}` : '';
  }
}
