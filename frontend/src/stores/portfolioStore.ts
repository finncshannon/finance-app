import { create } from 'zustand';

interface Position {
  id: number;
  ticker: string;
  company_name: string;
  shares_held: number;
  cost_basis_per_share: number;
  current_price: number;
  market_value: number;
  gain_loss: number;
  gain_loss_pct: number;
  weight_pct: number;
  account: string;
}

interface Account {
  id: number;
  name: string;
  account_type: string;
  is_default: boolean;
}

interface PerformanceMetrics {
  total_market_value: number;
  total_cost_basis: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  day_change: number;
  day_change_pct: number;
  position_count: number;
}

interface PortfolioState {
  positions: Position[];
  accounts: Account[];
  selectedAccountId: number | null;
  performance: PerformanceMetrics | null;
  isLoading: boolean;

  setPositions: (positions: Position[]) => void;
  setAccounts: (accounts: Account[]) => void;
  setSelectedAccount: (id: number | null) => void;
  setPerformance: (metrics: PerformanceMetrics | null) => void;
  setIsLoading: (loading: boolean) => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  positions: [],
  accounts: [],
  selectedAccountId: null,
  performance: null,
  isLoading: false,

  setPositions: (positions) => set({ positions }),
  setAccounts: (accounts) => set({ accounts }),
  setSelectedAccount: (id) => set({ selectedAccountId: id }),
  setPerformance: (metrics) => set({ performance: metrics }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
