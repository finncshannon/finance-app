import styles from './Loading.module.css';

interface LoadingBarProps {
  progress: number;
  title?: string;
  subtitle?: string;
  status?: string;
}

export function LoadingBar({ progress, title, subtitle, status }: LoadingBarProps) {
  const clampedProgress = Math.max(0, Math.min(100, progress));

  return (
    <div className={styles.overlay}>
      <div className={styles.container}>
        {title && <div className={styles.title}>{title}</div>}
        {subtitle && <div className={styles.subtitle}>{subtitle}</div>}
        <div className={styles.track}>
          <div
            className={styles.fill}
            style={{ width: `${clampedProgress}%` }}
          />
        </div>
        {status && <div className={styles.status}>{status}</div>}
      </div>
    </div>
  );
}
