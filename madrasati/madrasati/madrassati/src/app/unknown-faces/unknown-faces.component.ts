import { Component, OnInit, OnDestroy, ViewEncapsulation } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { UnknownFacesService, UnknownFace, UnknownFacesStats } from '../../services/unknown-faces.service';

@Component({
  selector: 'app-unknown-faces',
  templateUrl: './unknown-faces.component.html',
  styleUrls: ['./unknown-faces.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class UnknownFacesComponent implements OnInit, OnDestroy {
  // Data
  unknownFaces: UnknownFace[] = [];
  filteredFaces: UnknownFace[] = [];
  stats: UnknownFacesStats = {
    total: 0,
    today: 0,
    this_week: 0,
    directory_exists: false
  };

  // State
  loading = false;
  error: string | null = null;

  // Filters
  searchTerm = '';
  selectedDateFilter = 'all'; // 'all', 'today', 'week', 'custom'
  customStartDate = '';
  customEndDate = '';

  // Pagination
  currentPage = 1;
  itemsPerPage = 20;
  totalPages = 0;

  // Selection
  selectedFaces: Set<string> = new Set();
  selectAll = false;

  // Auto-refresh
  private refreshInterval: any;
  autoRefresh = true;
  refreshIntervalSeconds = 30;

  constructor(private unknownFacesService: UnknownFacesService) { }

  async ngOnInit(): Promise<void> {
    await this.loadUnknownFaces();
    await this.loadStats();
    this.setupAutoRefresh();
  }

  ngOnDestroy(): void {
    this.clearAutoRefresh();
  }

  async loadUnknownFaces(): Promise<void> {
    this.loading = true;
    this.error = null;
    
    try {
      const response = await firstValueFrom(this.unknownFacesService.getUnknownFaces());
      this.unknownFaces = response.faces || [];
      this.applyFilters();
      
      if (response.message) {
        console.log('Unknown faces message:', response.message);
      }
    } catch (error: any) {
      this.error = `خطأ في تحميل الوجوه المجهولة: ${error.message || 'خطأ غير معروف'}`;
      console.error('Error loading unknown faces:', error);
      this.unknownFaces = [];
      this.filteredFaces = [];
    } finally {
      this.loading = false;
    }
  }

  async loadStats(): Promise<void> {
    try {
      this.stats = await firstValueFrom(this.unknownFacesService.getStats());
    } catch (error: any) {
      console.error('Error loading stats:', error);
    }
  }

  applyFilters(): void {
    let filtered = [...this.unknownFaces];

    // Apply search filter
    if (this.searchTerm.trim()) {
      const term = this.searchTerm.toLowerCase().trim();
      filtered = filtered.filter(face => 
        face.id.toLowerCase().includes(term) ||
        face.filename.toLowerCase().includes(term)
      );
    }

    // Apply date filter
    if (this.selectedDateFilter !== 'all') {
      const now = new Date();
      let startDate: Date;

      switch (this.selectedDateFilter) {
        case 'today':
          startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          filtered = filtered.filter(face => new Date(face.timestamp) >= startDate);
          break;
        case 'week':
          startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          filtered = filtered.filter(face => new Date(face.timestamp) >= startDate);
          break;
        case 'custom':
          if (this.customStartDate) {
            startDate = new Date(this.customStartDate);
            filtered = filtered.filter(face => new Date(face.timestamp) >= startDate);
          }
          if (this.customEndDate) {
            const endDate = new Date(this.customEndDate);
            endDate.setHours(23, 59, 59, 999);
            filtered = filtered.filter(face => new Date(face.timestamp) <= endDate);
          }
          break;
      }
    }

    this.filteredFaces = filtered;
    this.updatePagination();
  }

  updatePagination(): void {
    this.totalPages = Math.ceil(this.filteredFaces.length / this.itemsPerPage);
    if (this.currentPage > this.totalPages) {
      this.currentPage = Math.max(1, this.totalPages);
    }
  }

  get paginatedFaces(): UnknownFace[] {
    const start = (this.currentPage - 1) * this.itemsPerPage;
    const end = start + this.itemsPerPage;
    return this.filteredFaces.slice(start, end);
  }

  // Pagination methods
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  nextPage(): void {
    this.goToPage(this.currentPage + 1);
  }

  previousPage(): void {
    this.goToPage(this.currentPage - 1);
  }

  // Filter methods
  onSearchChange(): void {
    this.currentPage = 1;
    this.applyFilters();
  }

  onDateFilterChange(): void {
    this.currentPage = 1;
    this.applyFilters();
  }

  onCustomDateChange(): void {
    if (this.selectedDateFilter === 'custom') {
      this.onDateFilterChange();
    }
  }

  // Selection methods
  toggleFaceSelection(filename: string): void {
    if (this.selectedFaces.has(filename)) {
      this.selectedFaces.delete(filename);
    } else {
      this.selectedFaces.add(filename);
    }
    this.updateSelectAllState();
  }

  toggleSelectAll(): void {
    if (this.selectAll) {
      this.selectedFaces.clear();
    } else {
      this.paginatedFaces.forEach(face => this.selectedFaces.add(face.filename));
    }
    this.selectAll = !this.selectAll;
  }

  updateSelectAllState(): void {
    const visibleFilenames = new Set(this.paginatedFaces.map(face => face.filename));
    this.selectAll = this.paginatedFaces.length > 0 && 
      this.paginatedFaces.every(face => this.selectedFaces.has(face.filename));
  }

  // Action methods
  async deleteSelected(): Promise<void> {
    if (this.selectedFaces.size === 0) return;

    const confirmMessage = `هل أنت متأكد من حذف ${this.selectedFaces.size} صورة؟`;
    if (!confirm(confirmMessage)) return;

    this.loading = true;
    let successCount = 0;
    let errorCount = 0;

    for (const filename of this.selectedFaces) {
      try {
        await firstValueFrom(this.unknownFacesService.deleteUnknownFace(filename));
        successCount++;
      } catch (error) {
        errorCount++;
        console.error(`Error deleting ${filename}:`, error);
      }
    }

    this.selectedFaces.clear();
    this.selectAll = false;

    if (successCount > 0) {
      await this.loadUnknownFaces();
      await this.loadStats();
    }

    if (errorCount > 0) {
      alert(`تم حذف ${successCount} صورة بنجاح. فشل حذف ${errorCount} صورة.`);
    } else {
      alert(`تم حذف ${successCount} صورة بنجاح.`);
    }

    this.loading = false;
  }

  async deleteFace(filename: string): Promise<void> {
    if (!confirm('هل أنت متأكد من حذف هذه الصورة؟')) return;

    try {
      await firstValueFrom(this.unknownFacesService.deleteUnknownFace(filename));
      await this.loadUnknownFaces();
      await this.loadStats();
      alert('تم حذف الصورة بنجاح');
    } catch (error: any) {
      alert(`خطأ في حذف الصورة: ${error.message || 'خطأ غير معروف'}`);
    }
  }

  async refresh(): Promise<void> {
    await this.loadUnknownFaces();
    await this.loadStats();
  }

  // Auto-refresh methods
  setupAutoRefresh(): void {
    if (this.autoRefresh) {
      this.refreshInterval = setInterval(async () => {
        await this.loadUnknownFaces();
        await this.loadStats();
      }, this.refreshIntervalSeconds * 1000);
    }
  }

  clearAutoRefresh(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  toggleAutoRefresh(): void {
    this.autoRefresh = !this.autoRefresh;
    if (this.autoRefresh) {
      this.setupAutoRefresh();
    } else {
      this.clearAutoRefresh();
    }
  }

  // Utility methods
  getImageUrl(face: UnknownFace): string {
    return this.unknownFacesService.getImageUrl(face.filename);
  }

  formatTimestamp(timestamp: string): string {
    return new Date(timestamp).toLocaleString('ar-EG');
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  onImageError(event: Event): void {
    const target = event.target as HTMLElement;
    if (target) {
      target.style.display = 'none';
    }
  }
}
