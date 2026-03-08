import styles from './Input.module.css';

interface CheckboxProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  className?: string;
  disabled?: boolean;
}

export function Checkbox({ label, checked, onChange, className, disabled }: CheckboxProps) {
  return (
    <label
      className={[styles.checkboxWrapper, className ?? ''].filter(Boolean).join(' ')}
      style={disabled ? { opacity: 0.5, pointerEvents: 'none' } : undefined}
    >
      <input
        type="checkbox"
        className={styles.checkboxInput}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
      <span className={styles.checkboxBox}>
        <svg
          className={styles.checkmark}
          width="10"
          height="8"
          viewBox="0 0 10 8"
          fill="none"
        >
          <path
            d="M1 4L3.5 6.5L9 1"
            stroke="white"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className={styles.checkboxLabel}>{label}</span>
    </label>
  );
}
