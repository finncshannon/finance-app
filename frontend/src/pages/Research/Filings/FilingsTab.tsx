import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import { useResearchStore } from '../../../stores/researchStore';
import { type FilingSummary, type FilingSection } from '../types';
import { FilingList } from './FilingList';
import { FilingSectionViewer } from './FilingSectionViewer';
import { FilingComparison } from './FilingComparison';
import styles from './FilingsTab.module.css';

interface FilingsTabProps {
  ticker: string;
}

const FORM_FILTERS = ['all', '10-K', '10-Q', '8-K'] as const;

export function FilingsTab({ ticker }: FilingsTabProps) {
  const { selectedFilingId, setSelectedFilingId, selectedSection, setSelectedSection, comparisonMode, setComparisonMode } = useResearchStore();
  const [filings, setFilings] = useState<FilingSummary[]>([]);
  const [sections, setSections] = useState<FilingSection[]>([]);
  const [formFilter, setFormFilter] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);

  const fetchFilings = useCallback(async () => {
    setLoading(true);
    try {
      const params = formFilter !== 'all' ? `?form_type=${formFilter}` : '';
      const data = await api.get<{ filings: FilingSummary[] }>(`/api/v1/research/${ticker}/filings${params}`);
      setFilings(data.filings);
    } catch {
      setFilings([]);
    } finally {
      setLoading(false);
    }
  }, [ticker, formFilter]);

  useEffect(() => {
    setSelectedFilingId(null);
    setSections([]);
    fetchFilings();
  }, [ticker, formFilter, fetchFilings, setSelectedFilingId]);

  const [loadingSections, setLoadingSections] = useState(false);

  useEffect(() => {
    if (!selectedFilingId) { setSections([]); return; }
    setLoadingSections(true);
    api.get<{ sections: FilingSection[] }>(`/api/v1/research/${ticker}/filing/${selectedFilingId}`)
      .then((d) => setSections(d.sections))
      .catch(() => setSections([]))
      .finally(() => setLoadingSections(false));
  }, [ticker, selectedFilingId]);

  const handleSelectFiling = useCallback((id: number) => {
    setSelectedFilingId(id);
  }, [setSelectedFilingId]);

  const handleSectionSelect = useCallback((key: string) => {
    setSelectedSection(key);
  }, [setSelectedSection]);

  const handleFetchFilings = async () => {
    setFetching(true);
    try {
      await api.post(`/api/v1/research/${ticker}/filings/fetch`, {});
      await fetchFilings();
    } catch { /* ignore */ }
    finally { setFetching(false); }
  };

  // Show fetch button if no filings or most recent filing is > 90 days old
  const showFetchBtn = (() => {
    if (filings.length === 0) return true;
    const newest = filings[0];
    if (!newest?.filing_date) return true;
    const daysSince = (Date.now() - new Date(newest.filing_date).getTime()) / (1000 * 60 * 60 * 24);
    return daysSince > 90;
  })();

  if (loading && filings.length === 0) {
    return <div className={styles.empty ?? ''}>Loading filings...</div>;
  }

  return (
    <div className={styles.container ?? ''}>
      <div className={styles.topBar ?? ''}>
        {FORM_FILTERS.map((f) => (
          <button
            key={f}
            className={`${styles.filterBtn ?? ''} ${formFilter === f ? styles.filterBtnActive ?? '' : ''}`}
            onClick={() => setFormFilter(f)}
          >
            {f === 'all' ? 'All' : f}
          </button>
        ))}
        {showFetchBtn && (
          <button
            className={styles.fetchBtn ?? ''}
            onClick={handleFetchFilings}
            disabled={fetching}
          >
            {fetching ? 'Fetching...' : 'Fetch Latest Filings'}
          </button>
        )}
        <button
          className={`${styles.compareBtn ?? ''} ${comparisonMode ? styles.compareBtnActive ?? '' : ''}`}
          onClick={() => setComparisonMode(!comparisonMode)}
        >
          Compare
        </button>
      </div>

      {comparisonMode ? (
        <div className={styles.panelsSingle ?? ''}>
          <FilingComparison ticker={ticker} filings={filings} />
        </div>
      ) : (
        <div className={styles.panels ?? ''}>
          <FilingList filings={filings} selectedId={selectedFilingId} onSelect={handleSelectFiling} />
          {selectedFilingId ? (
            loadingSections ? (
              <div className={styles.empty ?? ''}>Downloading & parsing filing...</div>
            ) : (
              <FilingSectionViewer
                sections={sections}
                activeKey={selectedSection}
                onSectionSelect={handleSectionSelect}
                docUrl={filings.find((f) => f.id === selectedFilingId)?.doc_url ?? null}
              />
            )
          ) : (
            <div className={styles.empty ?? ''}>Select a filing to view</div>
          )}
        </div>
      )}
    </div>
  );
}
