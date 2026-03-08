import { useModelStore } from '../../../stores/modelStore';
import { useUIStore } from '../../../stores/uiStore';
import { SlidersPanel } from './SlidersPanel';
import { TornadoChart } from './TornadoChart';
import { MonteCarloPanel } from './MonteCarloPanel';
import { DataTablePanel } from './DataTablePanel';
import styles from './SensitivityTab.module.css';

const TABS = [
  { id: 'sliders', label: 'Sliders' },
  { id: 'tornado', label: 'Tornado' },
  { id: 'monte-carlo', label: 'Monte Carlo' },
  { id: 'tables', label: 'Data Tables' },
] as const;

export function SensitivityTab() {
  const ticker = useModelStore((s) => s.activeTicker);
  const activeTab = useUIStore((s) => s.activeSensitivityTab);
  const setTab = useUIStore((s) => s.setSensitivityTab);

  if (!ticker) {
    return (
      <div className={styles.emptyState}>
        <span className={styles.emptyTitle}>Sensitivity Analysis</span>
        <span className={styles.emptyDesc}>
          Select a ticker to run sensitivity analysis.
        </span>
      </div>
    );
  }

  const renderPanel = () => {
    switch (activeTab) {
      case 'sliders':
        return <SlidersPanel />;
      case 'tornado':
        return <TornadoChart />;
      case 'monte-carlo':
        return <MonteCarloPanel />;
      case 'tables':
        return <DataTablePanel />;
      default:
        return <SlidersPanel />;
    }
  };

  return (
    <div className={styles.container}>
      {/* Inner pill / segment control */}
      <div className={styles.tabBar}>
        <div className={styles.segmentControl}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={[
                styles.segmentBtn,
                activeTab === tab.id ? styles.segmentBtnActive : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => setTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Active panel */}
      <div className={styles.panelArea}>{renderPanel()}</div>
    </div>
  );
}
