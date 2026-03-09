import { useEffect } from 'react';
import { type FilingSection } from '../types';
import { SectionNav } from './SectionNav';
import styles from './FilingSectionViewer.module.css';

interface FilingSectionViewerProps {
  sections: FilingSection[];
  activeKey: string | null;
  onSectionSelect: (key: string) => void;
  docUrl: string | null;
}

export function FilingSectionViewer({ sections, activeKey, onSectionSelect, docUrl }: FilingSectionViewerProps) {
  useEffect(() => {
    if (!activeKey && sections.length > 0) {
      onSectionSelect(sections[0]!.section_key);
    }
  }, [activeKey, sections, onSectionSelect]);

  if (sections.length === 0) {
    return (
      <div className={styles.empty ?? ''}>
        <div>No parsed sections available</div>
        {docUrl && (
          <button className={styles.secBtn ?? ''} onClick={() => window.open(docUrl, '_blank')}>
            Open Filing on SEC.gov
          </button>
        )}
      </div>
    );
  }

  const active = sections.find((s) => s.section_key === activeKey);

  return (
    <div className={styles.viewer ?? ''}>
      <SectionNav sections={sections} activeKey={activeKey} onSelect={onSectionSelect} />
      <div className={styles.content ?? ''}>
        {active ? (
          <>
            <div className={styles.sectionHeader ?? ''}>
              <h2 className={styles.sectionTitle ?? ''}>{active.section_title}</h2>
              {docUrl && (
                <button className={styles.secBtn ?? ''} onClick={() => window.open(docUrl, '_blank')}>
                  Open on SEC.gov
                </button>
              )}
            </div>
            <div className={styles.sectionBody ?? ''}>{active.content_text}</div>
          </>
        ) : (
          <div className={styles.empty ?? ''}>Select a section</div>
        )}
      </div>
    </div>
  );
}
