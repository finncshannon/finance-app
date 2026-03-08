import { useSettingsStore } from '../../../stores/settingsStore';
import { Select } from '../../../components/ui/Input/Select';
import { Input } from '../../../components/ui/Input/Input';
import { Checkbox } from '../../../components/ui/Input/Checkbox';
import { Card } from '../../../components/ui/Card/Card';
import styles from '../Settings.module.css';

const PROJECTION_YEARS_OPTIONS = [
  { value: '5', label: '5 years' },
  { value: '7', label: '7 years' },
  { value: '10', label: '10 years' },
  { value: '15', label: '15 years' },
];

const RISK_FREE_SOURCE_OPTIONS = [
  { value: 'auto', label: 'Auto (10Y Treasury)' },
  { value: 'manual', label: 'Manual' },
];

const TERMINAL_GROWTH_SOURCE_OPTIONS = [
  { value: 'auto', label: 'Auto (GDP-linked)' },
  { value: 'fixed', label: 'Fixed' },
];

const MONTE_CARLO_OPTIONS = [
  { value: '1000', label: '1,000' },
  { value: '5000', label: '5,000' },
  { value: '10000', label: '10,000' },
  { value: '50000', label: '50,000' },
  { value: '100000', label: '100,000' },
];

const VERBOSITY_OPTIONS = [
  { value: 'summary', label: 'Summary' },
  { value: 'detailed', label: 'Detailed' },
];

export function ModelDefaultsSection() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.set);

  return (
    <div className={styles.sectionGroup}>
      <Card>
        <p className={styles.sectionTitle}>Cost of Capital</p>
        <p className={styles.sectionDescription}>
          Default inputs for WACC and discount rate calculations.
        </p>
        <div className={styles.fieldGroup}>
          <Input
            label="Default Equity Risk Premium"
            value={settings.default_erp ?? ''}
            onChange={(val) => setSetting('default_erp', val)}
            placeholder="0.055"
            mono
          />
          <Checkbox
            label="Apply size premium adjustment"
            checked={settings.size_premium_enabled === 'true'}
            onChange={(checked) =>
              setSetting('size_premium_enabled', checked ? 'true' : 'false')
            }
          />
          <Select
            label="Risk-Free Rate Source"
            value={settings.risk_free_rate_source ?? 'auto'}
            onChange={(val) => setSetting('risk_free_rate_source', val)}
            options={RISK_FREE_SOURCE_OPTIONS}
          />
          {settings.risk_free_rate_source === 'manual' && (
            <Input
              label="Risk-Free Rate (manual)"
              value={settings.risk_free_rate_manual ?? ''}
              onChange={(val) => setSetting('risk_free_rate_manual', val)}
              placeholder="0.04"
              mono
            />
          )}
        </div>
      </Card>

      <Card>
        <p className={styles.sectionTitle}>Projections</p>
        <p className={styles.sectionDescription}>
          Defaults for DCF projection horizon and terminal value.
        </p>
        <div className={styles.fieldGroup}>
          <Select
            label="Default Projection Years"
            value={settings.default_projection_years ?? '10'}
            onChange={(val) => setSetting('default_projection_years', val)}
            options={PROJECTION_YEARS_OPTIONS}
          />
          <Select
            label="Terminal Growth Source"
            value={settings.terminal_growth_source ?? 'auto'}
            onChange={(val) => setSetting('terminal_growth_source', val)}
            options={TERMINAL_GROWTH_SOURCE_OPTIONS}
          />
          {settings.terminal_growth_source === 'fixed' && (
            <Input
              label="Terminal Growth Rate (fixed)"
              value={settings.terminal_growth_manual ?? ''}
              onChange={(val) => setSetting('terminal_growth_manual', val)}
              placeholder="0.025"
              mono
            />
          )}
        </div>
      </Card>

      <Card>
        <p className={styles.sectionTitle}>Simulation</p>
        <p className={styles.sectionDescription}>
          Monte Carlo and AI reasoning configuration.
        </p>
        <div className={styles.fieldGroup}>
          <Select
            label="Monte Carlo Iterations"
            value={settings.monte_carlo_iterations ?? '10000'}
            onChange={(val) => setSetting('monte_carlo_iterations', val)}
            options={MONTE_CARLO_OPTIONS}
          />
          <Select
            label="Reasoning Verbosity"
            value={settings.reasoning_verbosity ?? 'summary'}
            onChange={(val) => setSetting('reasoning_verbosity', val)}
            options={VERBOSITY_OPTIONS}
          />
        </div>
      </Card>
    </div>
  );
}
