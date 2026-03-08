import styles from './ErrorState.module.css';

interface ErrorStateProps {
  headline?: string;
  detail?: string;
  retryLabel?: string;
  onRetry?: () => void;
}

export function ErrorState({
  headline = 'Failed to load data',
  detail,
  retryLabel = 'Retry',
  onRetry,
}: ErrorStateProps) {
  return (
    <div className={styles.container}>
      <div className={styles.icon}>
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <div className={styles.headline}>{headline}</div>
      {detail && <div className={styles.detail}>{detail}</div>}
      {onRetry && (
        <button className={styles.retryBtn} onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}
