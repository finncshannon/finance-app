import styles from './Input.module.css';

interface InputProps {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  mono?: boolean;
  className?: string;
  disabled?: boolean;
}

export function Input({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
  mono = false,
  className,
  disabled,
}: InputProps) {
  return (
    <div className={[styles.fieldWrapper, className ?? ''].filter(Boolean).join(' ')}>
      {label && <label className={styles.label}>{label}</label>}
      <input
        type={type}
        className={[styles.input, mono ? styles.mono : ''].filter(Boolean).join(' ')}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
    </div>
  );
}
