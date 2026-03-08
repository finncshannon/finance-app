import { create } from 'zustand';

interface ScannerFilter {
  metric: string;
  operator: 'gt' | 'lt' | 'gte' | 'lte' | 'between';
  value: number;
  value_high?: number;
}

interface ScanResult {
  ticker: string;
  company_name: string;
  sector: string;
  relevance_score: number;
  keyword_matches: string[];
  metrics: Record<string, number>;
}

interface ScannerPreset {
  id: number;
  name: string;
  query_text: string | null;
  filters_json: string | null;
}

interface ScannerState {
  filters: ScannerFilter[];
  keywords: string[];
  universe: 'r3000' | 'sp500' | 'custom';
  results: ScanResult[];
  totalMatches: number;
  presets: ScannerPreset[];
  activePresetId: number | null;
  isScanning: boolean;

  setFilters: (filters: ScannerFilter[]) => void;
  addFilter: (filter: ScannerFilter) => void;
  removeFilter: (index: number) => void;
  setKeywords: (keywords: string[]) => void;
  setUniverse: (universe: 'r3000' | 'sp500' | 'custom') => void;
  setResults: (results: ScanResult[], total: number) => void;
  setPresets: (presets: ScannerPreset[]) => void;
  setActivePreset: (id: number | null) => void;
  setIsScanning: (scanning: boolean) => void;
  reset: () => void;
}

export const useScannerStore = create<ScannerState>((set) => ({
  filters: [],
  keywords: [],
  universe: 'sp500',
  results: [],
  totalMatches: 0,
  presets: [],
  activePresetId: null,
  isScanning: false,

  setFilters: (filters) => set({ filters }),
  addFilter: (filter) => set((s) => ({ filters: [...s.filters, filter] })),
  removeFilter: (index) =>
    set((s) => ({ filters: s.filters.filter((_, i) => i !== index) })),
  setKeywords: (keywords) => set({ keywords }),
  setUniverse: (universe) => set({ universe }),
  setResults: (results, total) => set({ results, totalMatches: total }),
  setPresets: (presets) => set({ presets }),
  setActivePreset: (id) => set({ activePresetId: id }),
  setIsScanning: (scanning) => set({ isScanning: scanning }),
  reset: () =>
    set({
      filters: [],
      keywords: [],
      results: [],
      totalMatches: 0,
      activePresetId: null,
      isScanning: false,
    }),
}));
