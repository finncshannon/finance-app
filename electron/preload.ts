import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: (): Promise<string> => ipcRenderer.invoke('get-backend-url'),
  getLayoutMode: (): Promise<string> => ipcRenderer.invoke('get-layout-mode'),
  isBackendReady: (): Promise<boolean> => ipcRenderer.invoke('is-backend-ready'),

  onBackendReady: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on('backend-ready', handler);
    return () => ipcRenderer.removeListener('backend-ready', handler);
  },

  onLayoutChange: (callback: (mode: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, mode: string) => callback(mode);
    ipcRenderer.on('layout-change', handler);
    return () => ipcRenderer.removeListener('layout-change', handler);
  },
});
