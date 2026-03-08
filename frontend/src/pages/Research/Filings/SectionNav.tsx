import { type FilingSection } from '../types';
import styles from './SectionNav.module.css';

interface SectionNavProps {
  sections: FilingSection[];
  activeKey: string | null;
  onSelect: (key: string) => void;
}

export function SectionNav({ sections, activeKey, onSelect }: SectionNavProps) {
  return (
    <div className={styles.nav ?? ''}>
      {sections.map((s) => (
        <button
          key={s.section_key}
          className={`${styles.item ?? ''} ${s.section_key === activeKey ? styles.itemActive ?? '' : ''}`}
          onClick={() => onSelect(s.section_key)}
        >
          {s.section_title}
          {s.word_count != null && (
            <span className={styles.wordCount ?? ''}>{s.word_count.toLocaleString()} words</span>
          )}
        </button>
      ))}
    </div>
  );
}
