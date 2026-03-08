import styles from './ModuleTabBar.module.css';

export const MODULE_TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'model-builder', label: 'Model Builder' },
  { id: 'scanner', label: 'Scanner' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'research', label: 'Research' },
  { id: 'settings', label: 'Settings' },
] as const;

export type ModuleId = (typeof MODULE_TABS)[number]['id'];

interface Props {
  activeModule: ModuleId;
  onModuleChange: (id: ModuleId) => void;
}

export function ModuleTabBar({ activeModule, onModuleChange }: Props) {
  return (
    <nav className={styles.tabBar} role="tablist">
      {MODULE_TABS.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeModule === tab.id}
          className={`${styles.tab} ${activeModule === tab.id ? styles.active : ''}`}
          onClick={() => onModuleChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
