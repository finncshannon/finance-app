import { useUIStore } from '../stores/uiStore';
import { useModelStore } from '../stores/modelStore';
import { useResearchStore } from '../stores/researchStore';
import { BASE_URL } from '../config';

export const navigationService = {
  /** Navigate to Model Builder with ticker pre-loaded */
  goToModelBuilder(ticker: string, modelType?: string) {
    const modelStore = useModelStore.getState();
    modelStore.setTicker(ticker);
    if (modelType) {
      modelStore.setModelType(modelType as 'dcf' | 'ddm' | 'comps' | 'revenue_based');
    }
    useUIStore.getState().setActiveModule('model-builder');
  },

  /** Navigate to Model Builder with a specific saved model */
  goToModel(ticker: string, modelId: number, modelType: string) {
    const modelStore = useModelStore.getState();
    modelStore.setTicker(ticker);
    modelStore.setModelType(modelType as 'dcf' | 'ddm' | 'comps' | 'revenue_based');
    modelStore.setActiveModelId(modelId);
    useUIStore.getState().setActiveModule('model-builder');
  },

  /** Navigate to Research with ticker pre-loaded */
  goToResearch(ticker: string, tab?: string) {
    useResearchStore.getState().setSelectedTicker(ticker.toUpperCase());
    const uiStore = useUIStore.getState();
    uiStore.setActiveModule('research');
    if (tab) {
      uiStore.setSubTab('research', tab);
    }
  },

  /** Navigate to Scanner */
  goToScanner() {
    useUIStore.getState().setActiveModule('scanner');
  },

  /** Navigate to Portfolio */
  goToPortfolio() {
    useUIStore.getState().setActiveModule('portfolio');
  },

  /** Navigate to Dashboard */
  goToDashboard() {
    useUIStore.getState().setActiveModule('dashboard');
  },

  /** Navigate to Portfolio → Upcoming Events tab */
  goToUpcomingEvents() {
    const uiStore = useUIStore.getState();
    uiStore.setActiveModule('portfolio');
    uiStore.setSubTab('portfolio', 'upcoming-events');
  },

  /** Add ticker to a watchlist */
  async addToWatchlist(ticker: string, watchlistId: number): Promise<boolean> {
    try {
      const res = await fetch(`${BASE_URL}/api/v1/dashboard/watchlists/${watchlistId}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: ticker.toUpperCase() }),
      });
      const json = await res.json();
      return json.success === true;
    } catch {
      return false;
    }
  },
};
