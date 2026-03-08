import { useState } from 'react';
import type { Position, PortfolioSummary, Account } from '../types';
import { SummaryHeader } from './SummaryHeader';
import { HoldingsTable } from './HoldingsTable';
import { RecordTransactionModal } from './RecordTransactionModal';
import styles from './HoldingsTab.module.css';

interface Props {
  positions: Position[];
  summary: PortfolioSummary | null;
  accounts: Account[];
  selectedAccount: string;
  onRefresh: () => void;
}

export function HoldingsTab({ positions, summary, accounts, onRefresh }: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [txTicker, setTxTicker] = useState<string | null>(null);

  const handleExpand = (id: number | null) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const handleRecordTx = (ticker: string) => {
    setTxTicker(ticker);
  };

  return (
    <div className={styles.container}>
      <SummaryHeader summary={summary} />
      <HoldingsTable
        positions={positions}
        expandedId={expandedId}
        onExpand={handleExpand}
        onRecordTx={handleRecordTx}
        onRefresh={onRefresh}
      />

      {txTicker != null && (
        <RecordTransactionModal
          ticker={txTicker}
          accounts={accounts}
          onClose={() => setTxTicker(null)}
          onSuccess={() => { setTxTicker(null); onRefresh(); }}
        />
      )}
    </div>
  );
}
