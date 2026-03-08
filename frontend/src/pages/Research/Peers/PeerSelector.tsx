import { useState } from 'react';
import { api } from '../../../services/api';
import type { CompanyProfile } from '../types';
import styles from './PeerSelector.module.css';

interface PeerSelectorProps {
  onAdd: (ticker: string) => void;
  existingTickers: string[];
}

export function PeerSelector({ onAdd, existingTickers }: PeerSelectorProps) {
  const [inputVal, setInputVal] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const ticker = inputVal.trim().toUpperCase();
    if (!ticker) return;

    if (existingTickers.includes(ticker)) {
      setError(`${ticker} is already in the list`);
      return;
    }

    setError('');
    setLoading(true);
    try {
      await api.get<CompanyProfile>(`/api/v1/research/${ticker}/profile`);
      onAdd(ticker);
      setInputVal('');
    } catch {
      setError(`Could not find ${ticker}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className={styles.row ?? ''} onSubmit={handleSubmit}>
      <input
        className={styles.input ?? ''}
        type="text"
        value={inputVal}
        onChange={(e) => { setInputVal(e.target.value); setError(''); }}
        placeholder="Add ticker..."
        disabled={loading}
      />
      <button
        className={styles.button ?? ''}
        type="submit"
        disabled={loading || !inputVal.trim()}
      >
        {loading ? '...' : 'Add Peer'}
      </button>
      {error && <span className={styles.error ?? ''}>{error}</span>}
    </form>
  );
}
