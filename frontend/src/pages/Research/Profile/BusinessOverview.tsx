import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import type { FilingSummary, FilingSection } from '../types';
import styles from './BusinessOverview.module.css';

interface Props {
  ticker: string;
}

function truncateWords(text: string, maxWords: number): { truncated: string; wasTruncated: boolean } {
  const words = text.split(/\s+/);
  if (words.length <= maxWords) return { truncated: text, wasTruncated: false };
  return { truncated: words.slice(0, maxWords).join(' ') + '...', wasTruncated: true };
}

export function BusinessOverview({ ticker }: Props) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [noFiling, setNoFiling] = useState(false);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNoFiling(false);
    setContent(null);

    (async () => {
      try {
        // Get 10-K filings
        const data = await api.get<{ filings: FilingSummary[] }>(
          `/api/v1/research/${ticker}/filings?form_type=10-K`
        );

        if (!data.filings || data.filings.length === 0) {
          if (!cancelled) setNoFiling(true);
          return;
        }

        // Get sections of the most recent 10-K
        const firstFiling = data.filings[0];
        if (!firstFiling) { if (!cancelled) setNoFiling(true); return; }
        const filingId = firstFiling.id;
        const sectionData = await api.get<{ sections: FilingSection[] }>(
          `/api/v1/research/${ticker}/filing/${filingId}`
        );

        // Find Item 1 / Business section
        const businessSection = sectionData.sections.find(
          (s) =>
            s.section_key?.toLowerCase().includes('item_1') ||
            s.section_key?.toLowerCase() === 'item1' ||
            s.section_title?.toLowerCase().includes('business') ||
            s.section_title?.toLowerCase().includes('item 1')
        );

        if (!cancelled) {
          if (businessSection?.content_text) {
            setContent(businessSection.content_text);
          } else {
            setNoFiling(true);
          }
        }
      } catch {
        if (!cancelled) setNoFiling(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [ticker]);

  const handleFetch = async () => {
    setFetching(true);
    try {
      await api.post(`/api/v1/research/${ticker}/filings/fetch`, {});
      // Reload by re-triggering effect
      setLoading(true);
      setNoFiling(false);
      setContent(null);

      const data = await api.get<{ filings: FilingSummary[] }>(
        `/api/v1/research/${ticker}/filings?form_type=10-K`
      );
      const latestFiling = data.filings?.[0];
      if (latestFiling) {
        const sectionData = await api.get<{ sections: FilingSection[] }>(
          `/api/v1/research/${ticker}/filing/${latestFiling.id}`
        );
        const businessSection = sectionData.sections.find(
          (s) =>
            s.section_key?.toLowerCase().includes('item_1') ||
            s.section_title?.toLowerCase().includes('business')
        );
        if (businessSection?.content_text) {
          setContent(businessSection.content_text);
          setNoFiling(false);
        }
      }
    } catch { /* ignore */ }
    finally {
      setFetching(false);
      setLoading(false);
    }
  };

  if (loading) {
    return null;
  }

  if (noFiling) {
    return (
      <div className={styles.card}>
        <h3 className={styles.title}>Business Overview</h3>
        <div className={styles.noFiling}>
          <span>No 10-K filing available.</span>
          <button className={styles.fetchBtn} onClick={handleFetch} disabled={fetching}>
            {fetching ? 'Fetching...' : 'Fetch Latest'}
          </button>
        </div>
      </div>
    );
  }

  if (!content) return null;

  const { truncated, wasTruncated } = truncateWords(content, 500);

  return (
    <div className={styles.card}>
      <h3 className={styles.title}>Business Overview</h3>
      <p className={styles.text}>{truncated}</p>
      {wasTruncated && (
        <span className={styles.readMore}>Read full filing in Filings tab</span>
      )}
    </div>
  );
}
