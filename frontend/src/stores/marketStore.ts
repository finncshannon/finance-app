import { create } from 'zustand';

interface PriceData {
  current_price: number;
  day_change: number;
  day_change_pct: number;
  volume: number;
  updated_at: string;
}

interface MarketState {
  prices: Record<string, PriceData>;
  marketOpen: boolean;
  wsConnected: boolean;
  lastUpdate: string | null;

  updatePrices: (data: Record<string, PriceData>) => void;
  setMarketOpen: (open: boolean) => void;
  setWsConnected: (connected: boolean) => void;
  getPrice: (ticker: string) => PriceData | undefined;
}

export const useMarketStore = create<MarketState>((set, get) => ({
  prices: {},
  marketOpen: false,
  wsConnected: false,
  lastUpdate: null,

  updatePrices: (data) =>
    set((state) => ({
      prices: { ...state.prices, ...data },
      lastUpdate: new Date().toISOString(),
    })),

  setMarketOpen: (open) => set({ marketOpen: open }),

  setWsConnected: (connected) => set({ wsConnected: connected }),

  getPrice: (ticker) => get().prices[ticker],
}));
