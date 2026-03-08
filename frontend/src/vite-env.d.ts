/// <reference types="vite/client" />

interface ElectronAPI {
  getBackendUrl: () => Promise<string>;
  getLayoutMode: () => Promise<string>;
  isBackendReady: () => Promise<boolean>;
  onBackendReady: (callback: () => void) => () => void;
  onLayoutChange: (callback: (mode: string) => void) => () => void;
}

interface Window {
  electronAPI?: ElectronAPI;
}
