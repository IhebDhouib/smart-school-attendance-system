import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';

import { AppModule } from './app/app.module';


platformBrowserDynamic().bootstrapModule(AppModule)
  .then(() => {
    // Reveal body after Angular is ready
    document.body.style.opacity = '1';
  })
  .catch(err => console.error(err));
