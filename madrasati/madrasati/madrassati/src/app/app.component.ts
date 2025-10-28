import { Component, OnInit, OnDestroy, ChangeDetectorRef, AfterViewInit, ViewChild } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter, takeUntil } from 'rxjs/operators';
import { Subject } from 'rxjs';
import { SidebarComponent } from './sidebar/sidebar.component';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('sidebar') sidebarComponent?: SidebarComponent;
  
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
    
    // Force la re-application des styles CSS après changement de route
    setTimeout(() => {
      if (this.isViewInitialized) {
        this.cdr.detectChanges();
        
        // Force le repaint des éléments avec .sidebar-adaptive-container
        const adaptiveContainers = document.querySelectorAll('.sidebar-adaptive-container');
        adaptiveContainers.forEach((container: Element) => {
          const htmlContainer = container as HTMLElement;
          // Force le recalcul des styles
          htmlContainer.style.display = 'none';
          htmlContainer.offsetHeight; // Trigger reflow
          htmlContainer.style.display = '';
          
          // Re-trigger les transitions CSS
          htmlContainer.classList.add('force-reflow');
          requestAnimationFrame(() => {
            htmlContainer.classList.remove('force-reflow');
          });
        });
        
        // Déclenche une re-application globale des styles CSS
        document.body.style.transform = 'translateZ(0)';
        requestAnimationFrame(() => {
          document.body.style.transform = '';
          this.cdr.detectChanges();
        });
      }
    }, 150); // Délai légèrement augmenté pour laisser le temps au DOM
    
    console.log('Route:', url, 'Sidebar visible:', this.showSidebar);
  }

  onSidebarCollapsedChange(collapsed: boolean) {
    this.sidebarCollapsed = collapsed;
    // Force la re-détection des changements pour assurer l'application correcte des styles
    setTimeout(() => {
      this.cdr.detectChanges();
    }, 50);
  }

  toggleSidebar() {
    if (this.sidebarComponent) {
      this.sidebarComponent.toggleSidebar();
    }
  }
}
