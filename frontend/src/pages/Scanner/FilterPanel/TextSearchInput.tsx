import styles from './FilterRow.module.css';

interface TextSearchInputProps {
  value: string;
  formTypes: string[];
  onChange: (value: string) => void;
  onFormTypesChange: (types: string[]) => void;
}

const FORM_TYPE_OPTIONS = ['10-K', '10-Q', '8-K'];

export function TextSearchInput({ value, formTypes, onChange, onFormTypesChange }: TextSearchInputProps) {
  const toggleFormType = (type: string) => {
    if (formTypes.includes(type)) {
      onFormTypesChange(formTypes.filter((t) => t !== type));
    } else {
      onFormTypesChange([...formTypes, type]);
    }
  };

  return (
    <div>
      <input
        className={styles.valueInput}
        style={{
          width: '100%',
          textAlign: 'left',
          padding: '6px 8px',
          fontSize: '12px',
          boxSizing: 'border-box',
        }}
        type="text"
        placeholder="Search SEC filings..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <div
        style={{
          display: 'flex',
          gap: '8px',
          marginTop: '6px',
          alignItems: 'center',
        }}
      >
        {FORM_TYPE_OPTIONS.map((type) => (
          <label
            key={type}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '3px',
              fontSize: '11px',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <input
              type="checkbox"
              checked={formTypes.includes(type)}
              onChange={() => toggleFormType(type)}
              style={{
                width: '12px',
                height: '12px',
                margin: 0,
                accentColor: 'var(--accent-primary)',
              }}
            />
            {type}
          </label>
        ))}
      </div>
    </div>
  );
}
