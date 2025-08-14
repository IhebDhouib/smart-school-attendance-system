// src/app/interfaces/class-schedule.interface.ts
export interface ClassSchedule {
  classId: string;
  teacherId: string;
  subject: string;
  dayOfWeek: 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday' | 'Saturday';
  startTime: string; // Format: "HH:mm"
  endTime: string; // Format: "HH:mm"
}
