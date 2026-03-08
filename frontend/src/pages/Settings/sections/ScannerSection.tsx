import { useSettingsStore } from '../../../stores/settingsStore';
import { Select } from '../../../components/ui/Input/Select';
import { Checkbox } from '../../../components/ui/Input/Checkbox';
import { Card } from '../../../components/ui/Card/Card';
import styles from '../Settings.module.css';

const LIMIT_OPTIONS = [
  { value: '25', label: '25 results' },
  { value: '50', label: '50 results' },
  { value: '100', label: '100 results' },
  { value: '200', label: '200 results' },
];

export function ScannerSection() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.set);

  return (
    <div className={styles.sectionGroup}>
      <Card>
        <p className={styles.sectionTitle}>Scanner Defaults</p>
        <p className={styles.sectionDescription}>
          Control scan behavior and result limits.
        </p>
        <div className={styles.fieldGroup}>
          <Checkbox
            label="Auto-add scan results to watchlist"
            checked={settings.scanner_auto_add === 'true'}
            onChange={(checked) =>
              setSetting('scanner_auto_add', checked ? 'true' : 'false')
            }
          />
          <Select
            label="Default Result Limit"
            value={settings.scanner_default_limit ?? '50'}
            onChange={(val) => setSetting('scanner_default_limit', val)}
            options={LIMIT_OPTIONS}
          />
        </div>
      </Card>
    </div>
  );
}
