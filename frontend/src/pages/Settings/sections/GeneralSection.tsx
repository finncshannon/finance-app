import { useSettingsStore } from '../../../stores/settingsStore';
import { Select } from '../../../components/ui/Input/Select';
import { Checkbox } from '../../../components/ui/Input/Checkbox';
import { Card } from '../../../components/ui/Card/Card';
import { KeyboardShortcuts } from './KeyboardShortcuts';
import { CacheManagement } from './CacheManagement';
import styles from '../Settings.module.css';

const STARTUP_OPTIONS = [
  { value: 'dashboard', label: 'Dashboard' },
  { value: 'model-builder', label: 'Model Builder' },
  { value: 'scanner', label: 'Scanner' },
  { value: 'portfolio', label: 'Portfolio' },
  { value: 'research', label: 'Research' },
];

export function GeneralSection() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.set);

  return (
    <div className={styles.sectionGroup}>
      <Card>
        <p className={styles.sectionTitle}>Startup</p>
        <p className={styles.sectionDescription}>
          Choose which module loads when the app starts.
        </p>
        <div className={styles.fieldGroup}>
          <Select
            label="Startup Module"
            value={settings.startup_module ?? 'dashboard'}
            onChange={(val) => setSetting('startup_module', val)}
            options={STARTUP_OPTIONS}
          />
          <Checkbox
            label="Enable boot animation"
            checked={settings.boot_animation_enabled === 'true'}
            onChange={(checked) =>
              setSetting('boot_animation_enabled', checked ? 'true' : 'false')
            }
          />
          <Checkbox
            label="Enable startup sounds"
            checked={settings.sound_enabled !== 'false'}
            onChange={(checked) =>
              setSetting('sound_enabled', checked ? 'true' : 'false')
            }
          />
        </div>
      </Card>
      <KeyboardShortcuts />
      <CacheManagement />
    </div>
  );
}
