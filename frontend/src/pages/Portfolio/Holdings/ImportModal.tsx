import { useState, useRef } from 'react';
import { api } from '../../../services/api';
import type { ImportPreview, ImportResult } from '../types';
import { fmtDollar, fmtShares } from '../types';
import styles from './ImportModal.module.css';

type ImportType = 'positions' | 'transactions';
type Broker = 'generic' | 'fidelity' | 'schwab' | 'ibkr';
type Step = 1 | 2 | 3 | 4;

interface Props {
  onClose: () => void;
  onSuccess: () => void;
  defaultImportType?: ImportType;
}

const BROKERS: { value: Broker; label: string }[] = [
  { value: 'generic', label: 'Generic CSV' },
  { value: 'fidelity', label: 'Fidelity' },
  { value: 'schwab', label: 'Schwab' },
  { value: 'ibkr', label: 'Interactive Brokers' },
];

interface TxPreviewRow {
  date: string;
  type: string;
  ticker: string;
  shares: number;
  price: number;
  fees: number;
  account: string | null;
}

interface TxPreviewData {
  success: boolean;
  transactions: TxPreviewRow[];
  errors: string[];
  warnings: string[];
  row_count: number;
  skipped_count: number;
}

const POSITION_MAPPING_FIELDS = [
  { value: '', label: 'Skip' },
  { value: 'ticker', label: 'Ticker' },
  { value: 'shares', label: 'Shares' },
  { value: 'cost_basis', label: 'Cost Basis' },
  { value: 'date', label: 'Date Acquired' },
  { value: 'account', label: 'Account' },
  { value: 'name', label: 'Company Name' },
];

const TX_MAPPING_FIELDS = [
  { value: '', label: 'Skip' },
  { value: 'ticker', label: 'Ticker / Symbol' },
  { value: 'date', label: 'Date' },
  { value: 'type', label: 'Action (Buy/Sell)' },
  { value: 'shares', label: 'Shares / Quantity' },
  { value: 'price', label: 'Price' },
  { value: 'fees', label: 'Fees / Commission' },
  { value: 'account', label: 'Account' },
];

export function ImportModal({ onClose, onSuccess, defaultImportType }: Props) {
  const [step, setStep] = useState<Step>(1);
  const [importType, setImportType] = useState<ImportType>(defaultImportType ?? 'positions');
  const [broker, setBroker] = useState<Broker>('generic');
  const [content, setContent] = useState('');
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [txPreview, setTxPreview] = useState<TxPreviewData | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [txResult, setTxResult] = useState<{ created: number; failed: number; total: number } | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Column mapping state
  const [showMapping, setShowMapping] = useState(false);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [columnMap, setColumnMap] = useState<Record<string, string>>({});

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setContent((ev.target?.result as string) ?? '');
    };
    reader.readAsText(file);
  };

  const handlePreview = async () => {
    if (!content.trim()) {
      setError('Please paste CSV content or upload a file');
      return;
    }
    setLoading(true);
    setError('');
    setShowMapping(false);

    try {
      if (importType === 'transactions') {
        const data = await api.post<TxPreviewData>(
          '/api/v1/portfolio/import/transactions/preview',
          { csv_content: content, broker }
        );
        if (!data.success && data.errors.length > 0) {
          // Auto-detection failed
          const firstLine = content.split('\n')[0] ?? '';
          const headers = firstLine.split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
          setCsvHeaders(headers);
          setShowMapping(true);
          setError(data.errors[0] ?? 'Auto-detection failed');
        } else {
          setTxPreview(data);
          setStep(3);
        }
      } else {
        const data = await api.post<ImportPreview>(
          '/api/v1/portfolio/import/preview',
          { content, broker }
        );
        if (data.positions.length === 0 && data.warnings.some((w) =>
          w.includes('Could not') || w.includes('auto-detect')
        )) {
          // Auto-detection failed
          const firstLine = content.split('\n')[0] ?? '';
          const headers = firstLine.split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
          setCsvHeaders(headers);
          setShowMapping(true);
          if (data.warnings.length > 0) setError(data.warnings[0] ?? '');
        } else {
          setPreview(data);
          setStep(3);
        }
      }
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Preview failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePreviewWithMapping = async () => {
    // Re-map CSV using the user's column mapping
    const lines = content.split('\n');
    if (lines.length < 2) {
      setError('CSV must have at least a header and one data row');
      return;
    }

    // Build a remapped CSV with standard column names
    const reverseMap: Record<string, string> = {};
    const txStandardNames: Record<string, string> = {
      ticker: 'Symbol', date: 'Date', type: 'Action',
      shares: 'Quantity', price: 'Price', fees: 'Commission', account: 'Account',
    };
    const posStandardNames: Record<string, string> = {
      ticker: 'Symbol', shares: 'Quantity', cost_basis: 'Cost Basis',
      date: 'Date Acquired', account: 'Account', name: 'Description',
    };
    const nameMap = importType === 'transactions' ? txStandardNames : posStandardNames;
    for (const [csvCol, internalField] of Object.entries(columnMap)) {
      if (internalField) {
        reverseMap[csvCol] = nameMap[internalField] ?? csvCol;
      }
    }

    // Remap header row
    const origHeaders = csvHeaders;
    const newHeaders = origHeaders.map((h) => reverseMap[h] ?? h);
    const newLines = [newHeaders.join(','), ...lines.slice(1)];
    const remappedContent = newLines.join('\n');

    setContent(remappedContent);
    setShowMapping(false);
    setError('');

    // Re-run preview with generic parser on remapped CSV
    setLoading(true);
    try {
      if (importType === 'transactions') {
        const data = await api.post<TxPreviewData>(
          '/api/v1/portfolio/import/transactions/preview',
          { csv_content: remappedContent, broker: 'generic' }
        );
        setTxPreview(data);
        setStep(3);
      } else {
        const data = await api.post<ImportPreview>(
          '/api/v1/portfolio/import/preview',
          { content: remappedContent, broker: 'generic' }
        );
        setPreview(data);
        setStep(3);
      }
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Preview failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    setLoading(true);
    setError('');
    try {
      if (importType === 'transactions' && txPreview) {
        const data = await api.post<{ created: number; failed: number; total: number }>(
          '/api/v1/portfolio/import/transactions/execute',
          { transactions: txPreview.transactions }
        );
        setTxResult(data);
        setStep(4);
      } else if (preview) {
        const data = await api.post<ImportResult>(
          '/api/v1/portfolio/import/execute',
          { preview }
        );
        setResult(data);
        setStep(4);
      }
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (step === 1) setStep(2);
    else if (step === 2) handlePreview();
    else if (step === 3) handleExecute();
    else { onSuccess(); }
  };

  const handleBack = () => {
    setError('');
    setShowMapping(false);
    if (step === 2) setStep(1);
    else if (step === 3) setStep(2);
  };

  const canGoNext = () => {
    if (step === 1) return true;
    if (step === 2) return content.trim().length > 0 && !loading && !showMapping;
    if (step === 3) return (preview != null || txPreview != null) && !loading;
    return true;
  };

  const nextLabel = () => {
    if (step === 2) return loading ? 'Previewing...' : 'Preview';
    if (step === 3) return loading ? 'Importing...' : 'Import';
    if (step === 4) return 'Close';
    return 'Next';
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3 className={styles.title}>
          Import {importType === 'transactions' ? 'Transactions' : 'Positions'}
        </h3>
        <div className={styles.stepIndicator}>Step {step} of 4</div>

        {/* ── Step 1: Import Type + Broker ── */}
        {step === 1 && (
          <>
            <div className={styles.importTypeToggle}>
              <button
                className={importType === 'positions' ? styles.typeActive : styles.typeBtn}
                onClick={() => setImportType('positions')}
              >
                Current Positions
              </button>
              <button
                className={importType === 'transactions' ? styles.typeActive : styles.typeBtn}
                onClick={() => setImportType('transactions')}
              >
                Transactions
              </button>
            </div>
            <div className={styles.radioGroup}>
              {BROKERS.map((b) => (
                <label
                  key={b.value}
                  className={
                    broker === b.value
                      ? styles.radioLabelSelected
                      : styles.radioLabel
                  }
                >
                  <input
                    type="radio"
                    name="broker"
                    className={styles.radioInput}
                    value={b.value}
                    checked={broker === b.value}
                    onChange={() => setBroker(b.value)}
                  />
                  {b.label}
                </label>
              ))}
            </div>
          </>
        )}

        {/* ── Step 2: Upload CSV ── */}
        {step === 2 && (
          <div className={styles.uploadArea}>
            <label className={styles.textareaLabel}>
              Paste CSV content
            </label>
            <textarea
              className={styles.textarea}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste CSV data here..."
            />
            <div className={styles.orDivider}>or</div>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.txt"
              className={styles.fileInput}
              onChange={handleFileChange}
            />

            {/* Column Mapping Fallback */}
            {showMapping && (
              <div className={styles.mappingSection}>
                <p className={styles.mappingHint}>
                  We couldn&apos;t auto-detect your CSV format. Please map the columns:
                </p>
                <div className={styles.mappingGrid}>
                  {csvHeaders.map((header) => (
                    <div key={header} className={styles.mappingRow}>
                      <span className={styles.csvHeader}>&ldquo;{header}&rdquo;</span>
                      <span className={styles.mappingArrow}>&rarr;</span>
                      <select
                        className={styles.mappingSelect}
                        value={columnMap[header] ?? ''}
                        onChange={(e) =>
                          setColumnMap({ ...columnMap, [header]: e.target.value })
                        }
                      >
                        {(importType === 'transactions' ? TX_MAPPING_FIELDS : POSITION_MAPPING_FIELDS).map((f) => (
                          <option key={f.value} value={f.value}>{f.label}</option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
                <button
                  className={styles.btnPrimary}
                  onClick={handlePreviewWithMapping}
                  disabled={!Object.values(columnMap).some((v) => v === 'ticker')}
                >
                  Preview with this mapping
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Step 3: Preview ── */}
        {step === 3 && importType === 'positions' && preview && (
          <>
            <table className={styles.previewTable}>
              <thead>
                <tr>
                  <th className={styles.previewThRemove} />
                  <th className={styles.previewTh}>Ticker</th>
                  <th className={styles.previewThRight}>Shares</th>
                  <th className={styles.previewThRight}>Cost/Share</th>
                  <th className={styles.previewTh}>Date</th>
                  <th className={styles.previewTh}>Account</th>
                </tr>
              </thead>
              <tbody>
                {preview.positions.map((p, i) => (
                  <tr key={i}>
                    <td className={styles.previewTdRemove}>
                      <button
                        className={styles.removeRowBtn}
                        onClick={() => setPreview({
                          ...preview,
                          positions: preview.positions.filter((_, j) => j !== i),
                        })}
                        title="Remove from import"
                      >&times;</button>
                    </td>
                    <td className={styles.previewTdTicker}>{p.ticker}</td>
                    <td className={styles.previewTdRight}>{fmtShares(p.shares)}</td>
                    <td className={styles.previewTdRight}>
                      {fmtDollar(p.cost_basis_per_share)}
                    </td>
                    <td className={styles.previewTd}>{p.date_acquired ?? '—'}</td>
                    <td className={styles.previewTd}>{p.account ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {preview.warnings.length > 0 && (
              <div className={styles.warnings}>
                {preview.warnings.map((w, i) => (
                  <div key={i} className={styles.warning}>{w}</div>
                ))}
              </div>
            )}
          </>
        )}

        {step === 3 && importType === 'transactions' && txPreview && (
          <>
            <table className={styles.previewTable}>
              <thead>
                <tr>
                  <th className={styles.previewThRemove} />
                  <th className={styles.previewTh}>Date</th>
                  <th className={styles.previewTh}>Type</th>
                  <th className={styles.previewTh}>Ticker</th>
                  <th className={styles.previewThRight}>Shares</th>
                  <th className={styles.previewThRight}>Price</th>
                  <th className={styles.previewThRight}>Fees</th>
                </tr>
              </thead>
              <tbody>
                {txPreview.transactions.map((tx, i) => (
                  <tr key={i}>
                    <td className={styles.previewTdRemove}>
                      <button
                        className={styles.removeRowBtn}
                        onClick={() => setTxPreview({
                          ...txPreview,
                          transactions: txPreview.transactions.filter((_, j) => j !== i),
                        })}
                        title="Remove from import"
                      >&times;</button>
                    </td>
                    <td className={styles.previewTd}>{tx.date || '—'}</td>
                    <td className={styles.previewTd}>
                      <span className={
                        tx.type === 'BUY' ? styles.badgeBuy
                          : tx.type === 'SELL' ? styles.badgeSell
                          : styles.badgeDiv
                      }>
                        {tx.type}
                      </span>
                    </td>
                    <td className={styles.previewTdTicker}>{tx.ticker}</td>
                    <td className={styles.previewTdRight}>{fmtShares(tx.shares)}</td>
                    <td className={styles.previewTdRight}>{fmtDollar(tx.price)}</td>
                    <td className={styles.previewTdRight}>{fmtDollar(tx.fees)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {txPreview.warnings.length > 0 && (
              <div className={styles.warnings}>
                {txPreview.warnings.map((w, i) => (
                  <div key={i} className={styles.warning}>{w}</div>
                ))}
              </div>
            )}
          </>
        )}

        {/* ── Step 4: Result ── */}
        {step === 4 && importType === 'positions' && result && (
          <div className={styles.resultSummary}>
            <div className={styles.resultLine}>
              Imported: <span className={styles.resultCount}>{result.imported}</span>
            </div>
            <div className={styles.resultLine}>
              Skipped: <span>{result.skipped}</span>
            </div>
            {result.warnings.length > 0 && (
              <div className={styles.warnings}>
                {result.warnings.map((w, i) => (
                  <div key={i} className={styles.warning}>{w}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 4 && importType === 'transactions' && txResult && (
          <div className={styles.resultSummary}>
            <div className={styles.resultLine}>
              Created: <span className={styles.resultCount}>{txResult.created}</span>
            </div>
            <div className={styles.resultLine}>
              Failed: <span>{txResult.failed}</span>
            </div>
            <div className={styles.resultLine}>
              Total: <span>{txResult.total}</span>
            </div>
          </div>
        )}

        {error && <div className={styles.error}>{error}</div>}

        {/* ── Actions ── */}
        <div className={styles.actions}>
          {step > 1 && step < 4 && (
            <button className={styles.btn} onClick={handleBack} disabled={loading}>
              Back
            </button>
          )}
          {step === 4 ? (
            <button className={styles.btnPrimary} onClick={onClose}>
              Close
            </button>
          ) : (
            <>
              <button className={styles.btn} onClick={onClose}>
                Cancel
              </button>
              <button
                className={styles.btnPrimary}
                onClick={handleNext}
                disabled={!canGoNext()}
              >
                {nextLabel()}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
