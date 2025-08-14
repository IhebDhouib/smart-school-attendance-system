import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { StudentService, Student, Classroom } from 'src/services/student.service';
import { ClassroomService } from 'src/services/classroom.service';

@Component({
  selector: 'app-student',
  templateUrl: './student.component.html',
  styleUrls: ['./student.component.css'],
  encapsulation:ViewEncapsulation.None
})
export class StudentComponent implements OnInit {
  newStudent: Student = {
    matricule: '',
    fullName: '',
    nomPere: '',
    dateNaissance: '',
    photos: [],
    classId: ''
  };

  // Filtres et tri
  searchText = '';
  selectedClass = '';
  selectedYear = '';
  sortColumn = 'matricule';
  sortDirection = 'asc' as 'asc' | 'desc';
  
  filteredStudents: Student[] = [];
  allStudents: Student[] = [];
  classrooms: Classroom[] = [];
  birthYears: number[] = [];
  
  selectedFiles: File[] = [];
  isEditing = false;
  editingStudentId: string | null = null;
  excelFile: File | null = null;

  constructor(
    private studentService: StudentService,
    private classroomService: ClassroomService
  ) {}

  ngOnInit() {
    this.getClassrooms();
    this.getStudents();
    this.generateBirthYears();
  }

  generateBirthYears() {
    const currentYear = new Date().getFullYear();
    for (let year = currentYear ; year >= currentYear - 20; year--) {
      this.birthYears.push(year);
    }
  }

  getClassrooms() {
    this.classroomService.getClassrooms().subscribe({
      next: (data) => {
        this.classrooms = data;
        this.applyFilters();
      },
      error: (err) => {
        console.error('Erreur lors du chargement des classes', err);
      }
    });
  }

  getStudents() {
    this.studentService.getAllStudents().subscribe({
      next: (data) => {
        this.allStudents = data;
        this.applyFilters();
      },
      error: (err) => {
        console.error('Erreur lors du chargement des étudiants', err);
      }
    });
  }

  applyFilters() {
    this.filteredStudents = this.allStudents.filter(student => {
      // Filtre par texte de recherche
      const matchesSearch = 
        this.searchText === '' ||
        student.fullName.toLowerCase().includes(this.searchText.toLowerCase()) ||
        student.matricule.toLowerCase().includes(this.searchText.toLowerCase()) ||
        (student.nomPere && student.nomPere.toLowerCase().includes(this.searchText.toLowerCase()));
      
      // Filtre par classe
      const matchesClass = 
        this.selectedClass === '' || 
        student.classId === this.selectedClass ||
        (typeof student.classId === 'object' && student.classId._id === this.selectedClass);
      
      // Filtre par année de naissance
      let matchesYear = true;
      if (this.selectedYear !== '' && student.dateNaissance) {
        const birthYear = new Date(student.dateNaissance).getFullYear();
        matchesYear = birthYear.toString() === this.selectedYear;
      }
      
      return matchesSearch && matchesClass && matchesYear;
    });

    this.sortStudents();
  }

  sortBy(column: string) {
    if (this.sortColumn === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = column;
      this.sortDirection = 'asc';
    }
    this.sortStudents();
  }

  sortStudents() {
    this.filteredStudents.sort((a, b) => {
      let valueA: any, valueB: any;
      
      if (this.sortColumn === 'dateNaissance') {
        valueA = a.dateNaissance ? new Date(a.dateNaissance).getTime() : 0;
        valueB = b.dateNaissance ? new Date(b.dateNaissance).getTime() : 0;
      } else {
        valueA = a[this.sortColumn as keyof Student];
        valueB = b[this.sortColumn as keyof Student];
        
        if (typeof valueA === 'string') valueA = valueA.toLowerCase();
        if (typeof valueB === 'string') valueB = valueB.toLowerCase();
      }
      
      if (valueA < valueB) return this.sortDirection === 'asc' ? -1 : 1;
      if (valueA > valueB) return this.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }

  onFileSelected(event: any) {
    this.selectedFiles = Array.from(event.target.files);
  }

  onExcelSelected(event: any) {
    this.excelFile = event.target.files[0];
  }

  importExcel() {
    if (!this.excelFile) {
      alert('Veuillez sélectionner un fichier Excel');
      return;
    }

    const formData = new FormData();
    formData.append("file", this.excelFile);

    this.studentService.importExcel(formData).subscribe({
      next: () => {
        this.getStudents();
        this.getClassrooms();
        this.excelFile = null;
        // Réinitialiser l'input file
        const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
      },
      error: (err) => {
        console.error("Erreur d'importation Excel", err);
        alert("Une erreur est survenue lors de l'importation");
      }
    });
  }

  addStudent() {
    if (!this.newStudent.matricule || !this.newStudent.fullName || !this.newStudent.classId) {
      alert('Veuillez remplir les champs obligatoires (Matricule, Nom Complet, Classe)');
      return;
    }

    const formData = new FormData();
    formData.append('matricule', this.newStudent.matricule);
    formData.append('fullName', this.newStudent.fullName);
    if (this.newStudent.nomPere) formData.append('nomPere', this.newStudent.nomPere);
    if (this.newStudent.dateNaissance) formData.append('dateNaissance', this.newStudent.dateNaissance);
    formData.append('classId', this.newStudent.classId.toString());

    for (let file of this.selectedFiles) {
      formData.append('photos', file);
    }

    this.studentService.addStudent(formData).subscribe({
      next: () => {
        this.getStudents();
        this.resetForm();
      },
      error: (err) => {
        console.error("Erreur lors de l'ajout de l'étudiant", err);
        alert("Une erreur est survenue lors de l'ajout");
      }
    });
  }

  editStudent(student: Student) {
    this.newStudent = { ...student };
    this.isEditing = true;
    this.editingStudentId = student._id || null;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  updateStudent() {
    if (!this.editingStudentId) return;

    const studentToUpdate = {
      ...this.newStudent,
      classId: this.newStudent.classId.toString()
    };

    this.studentService.updateStudent(this.editingStudentId, studentToUpdate).subscribe({
      next: () => {
        this.getStudents();
        this.resetForm();
      },
      error: (err) => {
        console.error("Erreur lors de la mise à jour", err);
        alert("Une erreur est survenue lors de la mise à jour");
      }
    });
  }

  deleteStudent(id: string) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet étudiant ?')) {
      this.studentService.deleteStudent(id).subscribe({
        next: () => {
          this.getStudents();
        },
        error: (err) => {
          console.error("Erreur lors de la suppression", err);
          alert("Une erreur est survenue lors de la suppression");
        }
      });
    }
  }

  resetForm() {
    this.newStudent = {
      matricule: '',
      fullName: '',
      nomPere: '',
      dateNaissance: '',
      photos: [],
      classId: ''
    };
    this.selectedFiles = [];
    this.isEditing = false;
    this.editingStudentId = null;
  }

  getClassroomName(classroom: any): string {
    if (!classroom) return 'Non assigné';
    
    if (typeof classroom === 'object') {
      return `${classroom.name} - ${classroom.grade}`;
    }
    
    const foundClass = this.classrooms.find(c => c._id === classroom);
    return foundClass ? `${foundClass.name} - ${foundClass.grade}` : 'Classe inconnue';
  }
}