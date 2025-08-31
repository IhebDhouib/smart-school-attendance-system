import { Component, OnInit, OnDestroy, ChangeDetectorRef, AfterViewInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter, takeUntil } from 'rxjs/operators';
import { Subject } from 'rxjs';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit, AfterViewInit, OnDestroy {
  showSidebar = true; // Start with true as default
  sidebarCollapsed = false; // Track sidebar collapsed state
  isLoaded = false; // Track if app has finished loading
  private destroy$ = new Subject<void>();
  private isViewInitialized = false;

  constructor(
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    // Listen for route changes with proper cleanup
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd),
      takeUntil(this.destroy$)
    ).subscribe((event) => {
      const navEndEvent = event as NavigationEnd;
      this.updateSidebarVisibility(navEndEvent.url);
    });
  }

  ngAfterViewInit() {
    this.isViewInitialized = true;
    
    // Make body visible
    if (typeof document !== 'undefined') {
      document.body.style.opacity = '1';
    }
    
    // Check the current route after the view is fully initialized
    setTimeout(() => {
      this.updateSidebarVisibility(this.router.url);
      // Mark as loaded after a small delay to prevent transition flicker
      setTimeout(() => {
        this.isLoaded = true;
        this.cdr.detectChanges();
      }, 100);
    }, 0);
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private updateSidebarVisibility(url: string) {
    // Hide sidebar only on login and register pages
    const shouldHideSidebar = url === '/login' || url === '/register';
    const newShowSidebar = !shouldHideSidebar;
    
    if (this.showSidebar !== newShowSidebar) {
      this.showSidebar = newShowSidebar;
      
      // Only trigger change detection if view is initialized
      if (this.isViewInitialized) {
        this.cdr.detectChanges();
      }
    }
    
    console.log('Route:', url, 'Sidebar visible:', this.showSidebar);
  }

  onSidebarCollapsedChange(collapsed: boolean) {
    this.sidebarCollapsed = collapsed;
  }
}
