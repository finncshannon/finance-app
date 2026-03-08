import React from 'react';
import styles from './EmptyState.module.css';

interface EmptyStateProps {
  headline: string;
  subtext?: string;
  ctaLabel?: string;
  onCta?: () => void;
  icon?: React.ReactNode;
}

export function EmptyState({ headline, subtext, ctaLabel, onCta, icon }: EmptyStateProps) {
  return (
    <div className={styles.container}>
      <div className={styles.icon}>
        {icon ?? (
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" />
          </svg>
        )}
      </div>
      <div className={styles.headline}>{headline}</div>
      {subtext && <div className={styles.subtext}>{subtext}</div>}
      {ctaLabel && (
        <button className={styles.ctaButton} onClick={onCta}>
          {ctaLabel}
        </button>
      )}
    </div>
  );
}
