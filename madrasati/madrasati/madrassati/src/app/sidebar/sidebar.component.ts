import { Component, HostListener, OnInit, OnDestroy, Inject, PLATFORM_ID, ViewEncapsulation } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { NavigationEnd, Router } from '@angular/router';
import { AuthService } from 'src/services/auth.service';

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.css'],
  encapsulation:ViewEncapsulation.None
})
export class SidebarComponent implements OnInit, OnDestroy {
  isCollapsed = false;
  isMobile = false;
  userCount = 24;
  pendingAttendance = 3;
  newReports = 2;

  private routerSubscription: Subscription = new Subscription();
  private resizeTimeout: any;

  constructor(
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: Object,
    private auth: AuthService
  ) {}

  ngOnInit() {
    if (isPlatformBrowser(this.platformId)) {
      this.checkScreenSize();
      if (this.isMobile) {
        this.isCollapsed = true;
      }
      if (!this.isMobile) {
        const savedState = localStorage.getItem('sidebarCollapsed');
        this.isCollapsed = savedState === 'true';
      }
      this.setupRouterSubscription();
    }
  }

  ngOnDestroy() {
    this.routerSubscription.unsubscribe();
    if (this.resizeTimeout) {
      clearTimeout(this.resizeTimeout);
    }
  }

  private setupRouterSubscription() {
    this.routerSubscription = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        if (this.isMobile && !this.isCollapsed) {
          this.toggleSidebar();
        }
      });
  }

  @HostListener('window:resize', ['$event'])
  onResize(event: any) {
    if (this.resizeTimeout) {
      clearTimeout(this.resizeTimeout);
    }
    this.resizeTimeout = setTimeout(() => {
      this.checkScreenSize();
    }, 150);
  }

  @HostListener('document:keydown.escape')
  onEscapeKey() {
    if (this.isMobile && !this.isCollapsed) {
      this.toggleSidebar();
    }
  }

  checkScreenSize() {
    if (isPlatformBrowser(this.platformId)) {
      const wasMobile = this.isMobile;
      this.isMobile = window.innerWidth <= 768;
      if (wasMobile && !this.isMobile) {
        const savedState = localStorage.getItem('sidebarCollapsed');
        this.isCollapsed = savedState === 'true';
      }
      if (!wasMobile && this.isMobile) {
        this.isCollapsed = true;
      }
    }
  }

  toggleSidebar() {
    this.isCollapsed = !this.isCollapsed;
    if (!this.isMobile && isPlatformBrowser(this.platformId)) {
      localStorage.setItem('sidebarCollapsed', this.isCollapsed.toString());
    }
    this.provideFeedback();
  }

  onNavClick() {
    if (this.isMobile && !this.isCollapsed) {
      this.toggleSidebar();
    }
  }

  logout() {
    this.auth.logout();
    this.router.navigate(['/login']);
  }

  private provideFeedback() {
    if (isPlatformBrowser(this.platformId)) {
      const feedbackElement = document.createElement('div');
      feedbackElement.setAttribute('aria-live', 'polite');
      feedbackElement.setAttribute('class', 'sr-only');
      feedbackElement.textContent = `Sidebar ${this.isCollapsed ? 'fermée' : 'ouverte'}`;
      document.body.appendChild(feedbackElement);
      setTimeout(() => {
        feedbackElement.remove();
      }, 1000);
    }
  }
}