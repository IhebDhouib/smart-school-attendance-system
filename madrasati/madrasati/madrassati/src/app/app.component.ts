import { Component, OnInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  showSidebar = false; // Start with false to hide initially

  constructor(private router: Router) {}

  ngOnInit() {
    // Check initial route
    this.checkRoute(this.router.url);
    
    // Listen for route changes
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event) => {
      const navEndEvent = event as NavigationEnd;
      this.checkRoute(navEndEvent.url);
    });
  }

  private checkRoute(url: string) {
    // Hide sidebar on login and register pages
    if (url === '/login' || url === '/register' || url === '/') {
      this.showSidebar = false;
    } else {
      this.showSidebar = true;
    }
  }
}
