import { useState } from 'react';
import { useSettingsStore } from '../../../stores/settingsStore';
import { Select } from '../../../components/ui/Input/Select';
import { Input } from '../../../components/ui/Input/Input';
import { Checkbox } from '../../../components/ui/Input/Checkbox';
import { Card } from '../../../components/ui/Card/Card';
import styles from '../Settings.module.css';

const REFRESH_OPTIONS = [
  { value: '30', label: '30 seconds' },
  { value: '60', label: '1 minute' },
  { value: '120', label: '2 minutes' },
  { value: '300', label: '5 minutes' },
];

const RETENTION_YEARS_OPTIONS = [
  { value: '1', label: '1 year' },
  { value: '3', label: '3 years' },
  { value: '5', label: '5 years' },
  { value: '10', label: '10 years' },
];

const BACKUP_RETENTION_OPTIONS = [
  { value: '7', label: '7 days' },
  { value: '14', label: '14 days' },
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
];

function isValidEmail(email: string): boolean {
  const trimmed = email.trim();
  if (!trimmed) return true; // empty is "valid" (just not set)
  return trimmed.includes('@') && trimmed.includes('.');
}

export function DataSourcesSection() {
  const settings = useSettingsStore((s) => s.settings);
  const setSetting = useSettingsStore((s) => s.set);
  const [emailError, setEmailError] = useState('');

  const handleEmailChange = (val: string) => {
    setSetting('sec_edgar_email', val);
    if (val.trim() && !isValidEmail(val)) {
      setEmailError('Enter a valid email address (must contain @ and .)');
    } else {
      setEmailError('');
    }
  };

  return (
    <div className={styles.sectionGroup}>
      <Card>
        <p className={styles.sectionTitle}>Market Data</p>
        <p className={styles.sectionDescription}>
          Configure how frequently market data refreshes and when to fetch.
        </p>
        <div className={styles.fieldGroup}>
          <Select
            label="Refresh Interval"
            value={settings.refresh_interval_seconds ?? '60'}
            onChange={(val) => setSetting('refresh_interval_seconds', val)}
            options={REFRESH_OPTIONS}
          />
          <Checkbox
            label="Only refresh during market hours"
            checked={settings.market_hours_only === 'true'}
            onChange={(checked) =>
              setSetting('market_hours_only', checked ? 'true' : 'false')
            }
          />
        </div>
      </Card>

      <Card>
        <p className={styles.sectionTitle}>SEC EDGAR</p>
        <p className={styles.sectionDescription}>
          Email is required by SEC EDGAR for API access. Filings are cached locally.
        </p>
        <div className={styles.fieldGroup}>
          <div>
            <Input
              label="EDGAR Contact Email"
              value={settings.sec_edgar_email ?? ''}
              onChange={handleEmailChange}
              placeholder="you@example.com"
            />
            {emailError && (
              <p style={{ color: 'var(--color-negative)', fontSize: 11, margin: '4px 0 0' }}>
                {emailError}
              </p>
            )}
            <p style={{ color: 'var(--text-tertiary)', fontSize: 11, margin: '4px 0 0', lineHeight: 1.4 }}>
              Required by SEC.gov for EDGAR API access. Your email is sent as identification in request headers.
            </p>
          </div>
          <Checkbox
            label="Auto-fetch filings for tracked tickers"
            checked={settings.auto_fetch_filings === 'true'}
            onChange={(checked) =>
              setSetting('auto_fetch_filings', checked ? 'true' : 'false')
            }
          />
          <Select
            label="Filing Retention"
            value={settings.filing_retention_years ?? '5'}
            onChange={(val) => setSetting('filing_retention_years', val)}
            options={RETENTION_YEARS_OPTIONS}
          />
        </div>
      </Card>

      <Card>
        <p className={styles.sectionTitle}>Backups</p>
        <p className={styles.sectionDescription}>
          Automatic backups of local data and settings.
        </p>
        <div className={styles.fieldGroup}>
          <Checkbox
            label="Enable automatic backups"
            checked={settings.backup_enabled === 'true'}
            onChange={(checked) =>
              setSetting('backup_enabled', checked ? 'true' : 'false')
            }
          />
          <Select
            label="Backup Retention"
            value={settings.backup_retention_days ?? '30'}
            onChange={(val) => setSetting('backup_retention_days', val)}
            options={BACKUP_RETENTION_OPTIONS}
            disabled={settings.backup_enabled !== 'true'}
          />
        </div>
      </Card>
    </div>
  );
}
