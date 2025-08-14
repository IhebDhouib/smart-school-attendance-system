import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { ClassroomService } from 'src/services/classroom.service';
import { GRADES } from '../models/grades';

@Component({
  selector: 'app-classroom',
  templateUrl: './classroom.component.html',
  styleUrls: ['./classroom.component.css'],
  encapsulation:ViewEncapsulation.None
})
export class ClassroomComponent implements OnInit {
  classrooms: any[] = [];
  newClassroom = { name: '', grade: '' };
  grades = GRADES;

  constructor(private classroomService: ClassroomService) {}

  ngOnInit() {
    this.loadClassrooms();
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