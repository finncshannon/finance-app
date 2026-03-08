import { Card } from '../../../components/ui/Card/Card';
import { DatabaseStats } from './DatabaseStats';
import styles from '../Settings.module.css';

export function AboutSection() {
  return (
    <div className={styles.sectionGroup}>
      <Card>
        <p className={styles.sectionTitle}>Application Info</p>
        <div className={styles.aboutGrid}>
          <div className={styles.aboutRow}>
            <span className={styles.aboutLabel}>Version</span>
            <span className={styles.aboutValue}>1.0.0</span>
          </div>
          <div className={styles.aboutRow}>
            <span className={styles.aboutLabel}>Built with</span>
            <span className={styles.aboutValue}>Electron + React + FastAPI</span>
          </div>
        </div>
      </Card>
      <DatabaseStats />
    </div>
  );
}
