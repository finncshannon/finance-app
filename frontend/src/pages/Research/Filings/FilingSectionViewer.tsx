import { useEffect } from 'react';
import { type FilingSection } from '../types';
import { SectionNav } from './SectionNav';
import styles from './FilingSectionViewer.module.css';

interface FilingSectionViewerProps {
  sections: FilingSection[];
  activeKey: string | null;
  onSectionSelect: (key: string) => void;
}

export function FilingSectionViewer({ sections, activeKey, onSectionSelect }: FilingSectionViewerProps) {
  useEffect(() => {
    if (!activeKey && sections.length > 0) {
      onSectionSelect(sections[0]!.section_key);
    }
  }, [activeKey, sections, onSectionSelect]);

  if (sections.length === 0) {
    return <div className={styles.empty ?? ''}>No sections available</div>;
  }

  const active = sections.find((s) => s.section_key === activeKey);

  return (
    <div className={styles.viewer ?? ''}>
      <SectionNav sections={sections} activeKey={activeKey} onSelect={onSectionSelect} />
      <div className={styles.content ?? ''}>
        {active ? (
          <>
            <h2 className={styles.sectionTitle ?? ''}>{active.section_title}</h2>
            <div className={styles.sectionBody ?? ''}>{active.content_text}</div>
          </>
        ) : (
          <div className={styles.empty ?? ''}>Select a section</div>
        )}
      </div>
    </div>
  );
}
