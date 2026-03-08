import { create } from 'zustand';

interface ResearchState {
  selectedTicker: string;
  selectedFilingId: number | null;
  selectedSection: string | null;
  comparisonMode: boolean;
  isLoading: boolean;

  setSelectedTicker: (ticker: string) => void;
  setSelectedFilingId: (id: number | null) => void;
  setSelectedSection: (key: string | null) => void;
  setComparisonMode: (mode: boolean) => void;
  setIsLoading: (loading: boolean) => void;
}

export const useResearchStore = create<ResearchState>((set) => ({
  selectedTicker: typeof window !== 'undefined'
    ? localStorage.getItem('research_ticker') ?? ''
    : '',
  selectedFilingId: null,
  selectedSection: null,
  comparisonMode: false,
  isLoading: false,

  setSelectedTicker: (ticker) => {
    localStorage.setItem('research_ticker', ticker);
    set({ selectedTicker: ticker, selectedFilingId: null, selectedSection: null });
  },
  setSelectedFilingId: (id) => set({ selectedFilingId: id, selectedSection: null }),
  setSelectedSection: (key) => set({ selectedSection: key }),
  setComparisonMode: (mode) => set({ comparisonMode: mode }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
