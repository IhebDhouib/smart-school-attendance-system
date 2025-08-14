import { TestBed } from '@angular/core/testing';
import { TeacherService } from './Teacher.service';


describe('EnseignantService', () => {
  let service: TeacherService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TeacherService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
