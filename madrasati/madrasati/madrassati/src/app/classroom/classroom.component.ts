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
  // Exposer Math au template
  Math = Math;
  
  classrooms: any[] = [];
  filteredClassrooms: any[] = [];
  newClassroom = { name: '', grade: '' };
  grades = GRADES;
  
  // Filtres et tri
  searchText = '';
  selectedGrade = '';
  sortColumn = 'name';
  sortDirection = 'asc' as 'asc' | 'desc';
  
  // Pagination
  currentPage = 1;
  itemsPerPage = 10;
  totalPages = 0;
  
  // Edition
  isEditing = false;
  editingClassroomId: string | null = null;

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
    this.classroomService.getClassrooms().subscribe(data => {
      this.classrooms = data;
      this.applyFilters();
    });
  }

  applyFilters() {
    this.filteredClassrooms = this.classrooms.filter(classroom => {
      const matchesSearch = 
        this.searchText === '' ||
        classroom.name.toLowerCase().includes(this.searchText.toLowerCase()) ||
        classroom.grade.toLowerCase().includes(this.searchText.toLowerCase());
      
      const matchesGrade = 
        this.selectedGrade === '' || 
        classroom.grade === this.selectedGrade;
      
      return matchesSearch && matchesGrade;
    });

    this.sortClassrooms();
    this.currentPage = 1;
    this.updatePagination();
  }

  sortBy(column: string) {
    if (this.sortColumn === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = column;
      this.sortDirection = 'asc';
    }
    this.sortClassrooms();
  }

  sortClassrooms() {
    this.filteredClassrooms.sort((a, b) => {
      let aValue = a[this.sortColumn];
      let bValue = b[this.sortColumn];

      if (aValue < bValue) return this.sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return this.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }

  addClassroom() {
    if (!this.newClassroom.name || !this.newClassroom.grade) {
      alert('الرجاء ملء جميع الحقول');
      return;
    }

    this.classroomService.createClassroom(this.newClassroom).subscribe(() => {
      this.resetForm();
      this.loadClassrooms();
    });
  }

  editClassroom(classroom: any) {
    this.newClassroom = { ...classroom };
    this.isEditing = true;
    this.editingClassroomId = classroom._id;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  resetForm() {
    this.newClassroom = { name: '', grade: '' };
    this.isEditing = false;
    this.editingClassroomId = null;
  }

  deleteClassroom(id: string) {
    if (confirm('هل أنت متأكد من حذف هذا الفصل؟')) {
      this.classroomService.deleteClassroom(id).subscribe(() => this.loadClassrooms());
    }
  }

  // Méthodes de pagination
  get pagedClassrooms(): any[] {
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    return this.filteredClassrooms.slice(startIndex, endIndex);
  }

  updatePagination() {
    this.totalPages = Math.ceil(this.filteredClassrooms.length / this.itemsPerPage);
    if (this.currentPage > this.totalPages && this.totalPages > 0) {
      this.currentPage = this.totalPages;
    }
    if (this.currentPage < 1) {
      this.currentPage = 1;
    }
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  get pageNumbers(): number[] {
    const pages: number[] = [];
    const maxPagesToShow = 5;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(this.totalPages, startPage + maxPagesToShow - 1);

    if (endPage - startPage + 1 < maxPagesToShow) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }
    return pages;
  }

  changeItemsPerPage(event: any) {
    this.itemsPerPage = parseInt(event.target.value);
    this.currentPage = 1;
    this.updatePagination();
  }
}