/** App-wide configuration. Centralizes backend URL for Electron packaging. */
export const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_URL = BASE_URL.replace(/^http/, 'ws');
