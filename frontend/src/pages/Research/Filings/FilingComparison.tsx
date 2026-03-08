import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import { type FilingSummary, type FilingSection } from '../types';
import styles from './FilingComparison.module.css';

interface FilingComparisonProps {
  ticker: string;
  filings: FilingSummary[];
}

interface ComparisonResult {
  left: { title: string; content: string };
  right: { title: string; content: string };
}

export function FilingComparison({ ticker, filings }: FilingComparisonProps) {
  const [leftId, setLeftId] = useState<number | null>(null);
  const [rightId, setRightId] = useState<number | null>(null);
  const [sectionKey, setSectionKey] = useState<string>('');
  const [leftSections, setLeftSections] = useState<FilingSection[]>([]);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);

  useEffect(() => {
    if (!leftId) { setLeftSections([]); return; }
    api.get<{ sections: FilingSection[] }>(`/api/v1/research/${ticker}/filing/${leftId}`)
      .then((d) => setLeftSections(d.sections))
      .catch(() => setLeftSections([]));
  }, [ticker, leftId]);

  const runComparison = useCallback(async () => {
    if (!leftId || !rightId || !sectionKey) return;
    try {
      const result = await api.post<ComparisonResult>(`/api/v1/research/${ticker}/compare-filings`, {
        left_filing_id: leftId,
        right_filing_id: rightId,
        section_key: sectionKey,
      });
      setComparisonResult(result);
    } catch {
      setComparisonResult(null);
    }
  }, [ticker, leftId, rightId, sectionKey]);

  useEffect(() => { runComparison(); }, [runComparison]);

  const leftParagraphs = comparisonResult?.left.content.split('\n\n') ?? [];
  const rightParagraphs = comparisonResult?.right.content.split('\n\n') ?? [];
  const leftSet = new Set(leftParagraphs);
  const rightSet = new Set(rightParagraphs);

  return (
    <div className={styles.container ?? ''}>
      <div className={styles.controls ?? ''}>
        <span className={styles.label ?? ''}>Left</span>
        <select
          className={styles.select ?? ''}
          value={leftId ?? ''}
          onChange={(e) => setLeftId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Select filing...</option>
          {filings.map((f) => (
            <option key={f.id} value={f.id}>{f.form_type} - {f.filing_date}</option>
          ))}
        </select>

        <span className={styles.label ?? ''}>Right</span>
        <select
          className={styles.select ?? ''}
          value={rightId ?? ''}
          onChange={(e) => setRightId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Select filing...</option>
          {filings.map((f) => (
            <option key={f.id} value={f.id}>{f.form_type} - {f.filing_date}</option>
          ))}
        </select>

        <span className={styles.label ?? ''}>Section</span>
        <select
          className={styles.select ?? ''}
          value={sectionKey}
          onChange={(e) => setSectionKey(e.target.value)}
        >
          <option value="">Select section...</option>
          {leftSections.map((s) => (
            <option key={s.section_key} value={s.section_key}>{s.section_title}</option>
          ))}
        </select>
      </div>

      {comparisonResult ? (
        <div className={styles.panels ?? ''}>
          <div className={styles.panel ?? ''}>
            <div className={styles.panelTitle ?? ''}>{comparisonResult.left.title}</div>
            {leftParagraphs.map((p, i) => (
              <div
                key={i}
                className={`${styles.paragraph ?? ''} ${!rightSet.has(p) ? styles.paragraphRemoved ?? '' : ''}`}
              >
                {p}
              </div>
            ))}
          </div>
          <div className={styles.panel ?? ''}>
            <div className={styles.panelTitle ?? ''}>{comparisonResult.right.title}</div>
            {rightParagraphs.map((p, i) => (
              <div
                key={i}
                className={`${styles.paragraph ?? ''} ${!leftSet.has(p) ? styles.paragraphNew ?? '' : ''}`}
              >
                {p}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className={styles.empty ?? ''}>Select two filings and a section to compare</div>
      )}
    </div>
  );
}
