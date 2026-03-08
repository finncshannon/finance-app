import { useSettingsStore } from '../../../stores/settingsStore';
import { Select } from '../../../components/ui/Input/Select';
import { Input } from '../../../components/ui/Input/Input';
import { Card } from '../../../components/ui/Card/Card';
import styles from '../Settings.module.css';

const TAX_LOT_OPTIONS = [
  { value: 'fifo', label: 'FIFO (First In, First Out)' },
  { value: 'lifo', label: 'LIFO (Last In, First Out)' },
  { value: 'highest_cost', label: 'Highest Cost' },
  { value: 'lowest_cost', label: 'Lowest Cost' },
];

export function PortfolioSection() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.set);

  return (
    <div className={styles.sectionGroup}>
      <Card>
        <p className={styles.sectionTitle}>Portfolio Defaults</p>
        <p className={styles.sectionDescription}>
          Default benchmark and accounting method for portfolio tracking.
        </p>
        <div className={styles.fieldGroup}>
          <Input
            label="Default Benchmark"
            value={settings.default_benchmark ?? ''}
            onChange={(val) => setSetting('default_benchmark', val)}
            placeholder="SPY"
          />
          <Select
            label="Tax Lot Method"
            value={settings.tax_lot_method ?? 'fifo'}
            onChange={(val) => setSetting('tax_lot_method', val)}
            options={TAX_LOT_OPTIONS}
          />
        </div>
      </Card>
    </div>
  );
}
