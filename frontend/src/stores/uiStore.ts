import { create } from 'zustand';
import type { ModuleId } from '../components/Navigation/ModuleTabBar';

/** Sub-tab maps per module (from Phase 0D) */
const MODULE_SUB_TABS: Record<string, string[]> = {
  'model-builder': ['overview', 'assumptions', 'projections', 'sensitivity', 'history'],
  scanner: ['screens', 'filters', 'results', 'universe'],
  portfolio: ['holdings', 'performance', 'allocation', 'income', 'transactions', 'alerts', 'upcoming-events'],
  research: ['profile', 'financials', 'ratios', 'filings', 'segments', 'peers'],
  settings: ['general', 'data-sources', 'defaults', 'about'],
};

/** Sensitivity sub-tabs (Tier 3) */
const SENSITIVITY_SUB_TABS = ['sliders', 'tornado', 'monte-carlo', 'tables'];

interface SystemStatus {
  market_open: boolean;
  last_price_refresh: string | null;
  active_refresh_tickers: number;
  api_calls_remaining: number | null;
  backend_uptime_seconds: number;
}

interface UIState {
  activeModule: ModuleId;
  activeSubTabs: Record<string, string>;
  activeSensitivityTab: string;
  loading: Record<string, boolean>;
  systemStatus: SystemStatus | null;
  backendReady: boolean;
  justBooted: boolean;
  dashboardAnimationPlayed: boolean;
  eventsSource: 'watchlist' | 'portfolio' | 'market';
  eventsWatchlistId: number | null;
  eventsTypes: string[];

  setActiveModule: (module: ModuleId) => void;
  setSubTab: (module: string, tab: string) => void;
  setSensitivityTab: (tab: string) => void;
  setLoading: (key: string, value: boolean) => void;
  updateSystemStatus: (status: SystemStatus) => void;
  setBackendReady: (ready: boolean) => void;
  setJustBooted: (val: boolean) => void;
  setDashboardAnimationPlayed: (val: boolean) => void;
  setEventsSource: (source: 'watchlist' | 'portfolio' | 'market') => void;
  setEventsWatchlistId: (id: number | null) => void;
  setEventsTypes: (types: string[]) => void;
  toggleEventType: (type: string) => void;
  getSubTabsForModule: (module: string) => string[];
}

export const useUIStore = create<UIState>((set) => ({
  activeModule: 'dashboard',
  activeSubTabs: {
    'model-builder': 'overview',
    scanner: 'screens',
    portfolio: 'holdings',
    research: 'profile',
    settings: 'general',
  },
  activeSensitivityTab: 'sliders',
  loading: {},
  systemStatus: null,
  backendReady: false,
  justBooted: false,
  dashboardAnimationPlayed: false,
  eventsSource: 'portfolio',
  eventsWatchlistId: null,
  eventsTypes: ['earnings', 'ex_dividend'],

  setActiveModule: (module) => set({ activeModule: module }),

  setSubTab: (module, tab) =>
    set((state) => ({
      activeSubTabs: { ...state.activeSubTabs, [module]: tab },
    })),

  setSensitivityTab: (tab) => set({ activeSensitivityTab: tab }),

  setLoading: (key, value) =>
    set((state) => ({
      loading: { ...state.loading, [key]: value },
    })),

  updateSystemStatus: (status) => set({ systemStatus: status }),

  setBackendReady: (ready) => set({ backendReady: ready }),

  setJustBooted: (val) => set({ justBooted: val }),

  setDashboardAnimationPlayed: (val) => set({ dashboardAnimationPlayed: val }),

  setEventsSource: (source) => set({ eventsSource: source }),

  setEventsWatchlistId: (id) => set({ eventsWatchlistId: id }),

  setEventsTypes: (types) => set({ eventsTypes: types }),

  toggleEventType: (type) =>
    set((state) => {
      const has = state.eventsTypes.includes(type);
      if (has && state.eventsTypes.length <= 1) return state;
      return {
        eventsTypes: has
          ? state.eventsTypes.filter((t) => t !== type)
          : [...state.eventsTypes, type],
      };
    }),

  getSubTabsForModule: (module) => {
    if (module === 'sensitivity') return SENSITIVITY_SUB_TABS;
    return MODULE_SUB_TABS[module] ?? [];
  },
}));
