import { useCallback, useState } from 'react';
import { navigationService } from '../services/navigationService';

export function useTickerNavigation(ticker: string) {
  const [showWatchlistPicker, setShowWatchlistPicker] = useState(false);

  const openInModelBuilder = useCallback(() => {
    navigationService.goToModelBuilder(ticker);
  }, [ticker]);

  const openInResearch = useCallback((tab?: string) => {
    navigationService.goToResearch(ticker, tab);
  }, [ticker]);

  const handleHeaderNavigate = useCallback((target: string) => {
    switch (target) {
      case 'model':
        navigationService.goToModelBuilder(ticker);
        break;
      case 'research':
        navigationService.goToResearch(ticker);
        break;
      case 'watchlist':
        setShowWatchlistPicker(true);
        break;
    }
  }, [ticker]);

  return {
    openInModelBuilder,
    openInResearch,
    handleHeaderNavigate,
    showWatchlistPicker,
    setShowWatchlistPicker,
  };
}
