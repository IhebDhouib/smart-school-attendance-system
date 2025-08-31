export const environment = {
  production: true,
  // Use relative URLs - will automatically use the same IP as the frontend
  apiUrl: '/api',  // Nginx will proxy to backend:3000/api
  websocketUrl: `ws://${window.location.hostname}:3001`  // Use current hostname
};
