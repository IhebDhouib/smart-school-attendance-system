import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CameraFeedComponent } from './camera-feed.component';

describe('CameraFeedComponent', () => {
  let component: CameraFeedComponent;
  let fixture: ComponentFixture<CameraFeedComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [CameraFeedComponent]
    });
    fixture = TestBed.createComponent(CameraFeedComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
