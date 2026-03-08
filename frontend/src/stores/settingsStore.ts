import { create } from 'zustand';
import { BASE_URL } from '../config';

interface SettingsState {
  settings: Record<string, string>;
  loaded: boolean;

  hydrate: () => Promise<void>;
  get: (key: string) => string | undefined;
  set: (key: string, value: string) => Promise<void>;
  setMany: (updates: Record<string, string>) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: {},
  loaded: false,

  hydrate: async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/v1/settings/`);
      const json = await res.json();
      if (json.success && json.data?.settings) {
        set({ settings: json.data.settings, loaded: true });
      }
    } catch {
      // Backend not ready yet — will retry
    }
  },

  get: (key) => get().settings[key],

  set: async (key, value) => {
    set((state) => ({
      settings: { ...state.settings, [key]: value },
    }));
    try {
      await fetch(`${BASE_URL}/api/v1/settings/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
      });
    } catch {
      // Silently fail — settings will persist on next hydrate
    }
  },

  setMany: async (updates) => {
    set((state) => ({
      settings: { ...state.settings, ...updates },
    }));
    try {
      await fetch(`${BASE_URL}/api/v1/settings/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
    } catch {
      // Silently fail
    }
  },
}));
