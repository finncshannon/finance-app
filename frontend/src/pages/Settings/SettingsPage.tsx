import { useState } from 'react';
import { Tabs } from '../../components/ui/Tabs/Tabs';
import { GeneralSection } from './sections/GeneralSection';
import { DataSourcesSection } from './sections/DataSourcesSection';
import { ModelDefaultsSection } from './sections/ModelDefaultsSection';
import { PortfolioSection } from './sections/PortfolioSection';
import { ScannerSection } from './sections/ScannerSection';
import { AboutSection } from './sections/AboutSection';
import styles from './Settings.module.css';

const SETTINGS_TABS = [
  { id: 'general', label: 'General' },
  { id: 'data-sources', label: 'Data Sources' },
  { id: 'model-defaults', label: 'Model Defaults' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'scanner', label: 'Scanner' },
  { id: 'about', label: 'About' },
];

function getSection(id: string) {
  switch (id) {
    case 'data-sources': return DataSourcesSection;
    case 'model-defaults': return ModelDefaultsSection;
    case 'portfolio': return PortfolioSection;
    case 'scanner': return ScannerSection;
    case 'about': return AboutSection;
    default: return GeneralSection;
  }
}

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general');
  const ActiveSection = getSection(activeTab);

  return (
    <div className={styles.page}>
      <Tabs
        tabs={SETTINGS_TABS}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
      <div className={styles.content}>
        <div className={styles.contentInner}>
          <ActiveSection />
        </div>
      </div>
    </div>
  );
}
