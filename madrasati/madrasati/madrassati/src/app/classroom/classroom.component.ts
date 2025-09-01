import { Component, OnInit, ViewEncapsulation, ChangeDetectorRef, AfterViewInit } from '@angular/core';
import { ClassroomService } from 'src/services/classroom.service';
import { GRADES } from '../models/grades';

@Component({
  selector: 'app-classroom',
  templateUrl: './classroom.component.html',
  styleUrls: ['./classroom.component.css'],
  encapsulation:ViewEncapsulation.None
})
export class ClassroomComponent implements OnInit, AfterViewInit {
  classrooms: any[] = [];
  newClassroom = { name: '', grade: '' };
  grades = GRADES;

  constructor(
    private classroomService: ClassroomService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadClassrooms();
  }

  ngAfterViewInit() {
    // Force le reflow initial pour assurer l'application correcte des styles
    setTimeout(() => {
      this.forceStyleReflow();
    }, 100);
  }

  private forceStyleReflow() {
    const container = document.querySelector('.sidebar-adaptive-container');
    if (container) {
      const htmlContainer = container as HTMLElement;
      htmlContainer.style.transform = 'translateZ(0)';
      htmlContainer.offsetHeight; // Trigger reflow
      htmlContainer.style.transform = '';
      this.cdr.detectChanges();
    }
  }

  loadClassrooms() {
    this.classroomService.getClassrooms().subscribe(data => this.classrooms = data);
  }

  addClassroom() {
    this.classroomService.createClassroom(this.newClassroom).subscribe(() => {
      this.newClassroom = { name: '', grade: '' };
      this.loadClassrooms();
    });
  }

  deleteClassroom(id: string) {
    this.classroomService.deleteClassroom(id).subscribe(() => this.loadClassrooms());
  }
}