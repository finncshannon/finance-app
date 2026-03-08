import styles from './Loading.module.css';

interface LoadingSpinnerProps {
  className?: string;
}

export function LoadingSpinner({ className }: LoadingSpinnerProps) {
  return (
    <span
      className={[styles.spinner, className ?? ''].filter(Boolean).join(' ')}
      role="status"
      aria-label="Loading"
    />
  );
}
