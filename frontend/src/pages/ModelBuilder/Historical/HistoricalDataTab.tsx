import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import { displayModelName } from '../../../utils/displayNames';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import { DataReadinessTab } from './DataReadinessTab';
import type { DataReadinessResult, FieldMetadataEntry } from '../../../types/models';
import styles from './HistoricalDataTab.module.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FinancialRecord {
  fiscal_year: number;
  period_end_date: string | null;
  revenue: number | null;
  revenue_growth: number | null;
  cost_of_revenue: number | null;
  gross_profit: number | null;
  gross_margin: number | null;
  research_development: number | null;
  selling_general_admin: number | null;
  operating_expenses: number | null;
  operating_income: number | null;
  operating_margin: number | null;
  interest_expense: number | null;
  pretax_income: number | null;
  income_tax: number | null;
  effective_tax_rate: number | null;
  net_income: number | null;
  net_margin: number | null;
  eps_basic: number | null;
  eps_diluted: number | null;
  shares_outstanding: number | null;
  cash_and_equivalents: number | null;
  short_term_investments: number | null;
  accounts_receivable: number | null;
  inventory: number | null;
  total_current_assets: number | null;
  property_plant_equipment: number | null;
  goodwill: number | null;
  intangible_assets: number | null;
  total_assets: number | null;
  accounts_payable: number | null;
  short_term_debt: number | null;
  total_current_liabilities: number | null;
  long_term_debt: number | null;
  total_liabilities: number | null;
  total_equity: number | null;
  book_value_per_share: number | null;
  operating_cash_flow: number | null;
  depreciation_amortization: number | null;
  stock_based_comp: number | null;
  working_capital_changes: number | null;
  capital_expenditures: number | null;
  acquisitions: number | null;
  investing_cash_flow: number | null;
  debt_issued_repaid: number | null;
  dividends_paid: number | null;
  share_buybacks: number | null;
  financing_cash_flow: number | null;
  free_cash_flow: number | null;
  fcf_margin: number | null;
}

type SubTab = 'income' | 'balance' | 'cashflow' | 'readiness';

// ---------------------------------------------------------------------------
// Field key mapping: frontend FinancialRecord key → backend column name
// ---------------------------------------------------------------------------

const FIELD_KEY_MAP: Record<string, string> = {
  research_development: 'rd_expense',
  selling_general_admin: 'sga_expense',
  operating_expenses: 'operating_expense',
  operating_income: 'ebit',
  income_tax: 'tax_provision',
  total_current_assets: 'current_assets',
  total_current_liabilities: 'current_liabilities',
  total_equity: 'stockholders_equity',
  working_capital_changes: 'change_in_working_capital',
  capital_expenditures: 'capital_expenditure',
};

function toBackendKey(frontendKey: string): string {
  return FIELD_KEY_MAP[frontendKey] ?? frontendKey;
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

type FormatKind = 'dollar' | 'pct' | 'eps' | 'shares';

function fmtDollarAuto(v: number | null): string {
  if (v == null) return '\u2014';
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${abs.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  return `${sign}$${abs.toFixed(0)}`;
}

function fmtPct(v: number | null): string {
  if (v == null) return '\u2014';
  return `${(v * 100).toFixed(1)}%`;
}

function fmtEps(v: number | null): string {
  if (v == null) return '\u2014';
  return `$${v.toFixed(2)}`;
}

function fmtShares(v: number | null): string {
  if (v == null) return '\u2014';
  const abs = Math.abs(v);
  if (abs >= 1e9) return `${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(abs / 1e6).toFixed(2)}M`;
  return abs.toLocaleString('en-US');
}

function formatValue(v: number | null, kind: FormatKind): string {
  switch (kind) {
    case 'dollar': return fmtDollarAuto(v);
    case 'pct':    return fmtPct(v);
    case 'eps':    return fmtEps(v);
    case 'shares': return fmtShares(v);
  }
}

function isNeg(v: number | null): boolean {
  return v != null && v < 0;
}

function isMissing(v: number | null): boolean {
  return v == null;
}

// ---------------------------------------------------------------------------
// Line item definitions
// ---------------------------------------------------------------------------

interface LineItem {
  label: string;
  key: keyof FinancialRecord;
  format: FormatKind;
  separator?: boolean;
}

const INCOME_ITEMS: LineItem[] = [
  { label: 'Revenue',          key: 'revenue',              format: 'dollar' },
  { label: 'Revenue Growth',   key: 'revenue_growth',       format: 'pct' },
  { label: 'Cost of Revenue',  key: 'cost_of_revenue',      format: 'dollar' },
  { label: 'Gross Profit',     key: 'gross_profit',         format: 'dollar' },
  { label: 'Gross Margin',     key: 'gross_margin',         format: 'pct' },
  { label: 'R&D',              key: 'research_development', format: 'dollar' },
  { label: 'SG&A',             key: 'selling_general_admin',format: 'dollar' },
  { label: 'Total OpEx',       key: 'operating_expenses',   format: 'dollar' },
  { label: 'Operating Income', key: 'operating_income',     format: 'dollar', separator: true },
  { label: 'Operating Margin', key: 'operating_margin',     format: 'pct' },
  { label: 'Interest Expense', key: 'interest_expense',     format: 'dollar' },
  { label: 'Pre-Tax Income',   key: 'pretax_income',        format: 'dollar' },
  { label: 'Income Tax',       key: 'income_tax',           format: 'dollar' },
  { label: 'Effective Tax Rate',key: 'effective_tax_rate',  format: 'pct' },
  { label: 'Net Income',       key: 'net_income',           format: 'dollar', separator: true },
  { label: 'Net Margin',       key: 'net_margin',           format: 'pct' },
  { label: 'EPS (Basic)',      key: 'eps_basic',            format: 'eps' },
  { label: 'EPS (Diluted)',    key: 'eps_diluted',          format: 'eps' },
  { label: 'Shares Outstanding',key: 'shares_outstanding', format: 'shares' },
];

const BALANCE_ITEMS: LineItem[] = [
  { label: 'Cash & Equivalents',    key: 'cash_and_equivalents',    format: 'dollar' },
  { label: 'Short-term Investments', key: 'short_term_investments', format: 'dollar' },
  { label: 'Accounts Receivable',   key: 'accounts_receivable',    format: 'dollar' },
  { label: 'Inventory',             key: 'inventory',               format: 'dollar' },
  { label: 'Total Current Assets',  key: 'total_current_assets',   format: 'dollar', separator: true },
  { label: 'PP&E Net',              key: 'property_plant_equipment',format: 'dollar' },
  { label: 'Goodwill',              key: 'goodwill',                format: 'dollar' },
  { label: 'Intangibles',           key: 'intangible_assets',       format: 'dollar' },
  { label: 'Total Assets',          key: 'total_assets',            format: 'dollar', separator: true },
  { label: 'Accounts Payable',      key: 'accounts_payable',        format: 'dollar' },
  { label: 'Short-term Debt',       key: 'short_term_debt',         format: 'dollar' },
  { label: 'Total Current Liabilities', key: 'total_current_liabilities', format: 'dollar', separator: true },
  { label: 'Long-term Debt',        key: 'long_term_debt',          format: 'dollar' },
  { label: 'Total Liabilities',     key: 'total_liabilities',       format: 'dollar', separator: true },
  { label: 'Total Equity',          key: 'total_equity',            format: 'dollar', separator: true },
  { label: 'Book Value/Share',      key: 'book_value_per_share',    format: 'eps' },
];

const CASHFLOW_ITEMS: LineItem[] = [
  { label: 'Net Income',              key: 'net_income',              format: 'dollar' },
  { label: 'D&A',                     key: 'depreciation_amortization',format: 'dollar' },
  { label: 'Stock-Based Comp',        key: 'stock_based_comp',        format: 'dollar' },
  { label: 'Working Capital Changes', key: 'working_capital_changes', format: 'dollar' },
  { label: 'Operating Cash Flow',     key: 'operating_cash_flow',     format: 'dollar', separator: true },
  { label: 'CapEx',                   key: 'capital_expenditures',    format: 'dollar' },
  { label: 'Acquisitions',            key: 'acquisitions',            format: 'dollar' },
  { label: 'Investing Cash Flow',     key: 'investing_cash_flow',     format: 'dollar', separator: true },
  { label: 'Debt Issued/Repaid',      key: 'debt_issued_repaid',      format: 'dollar' },
  { label: 'Dividends Paid',          key: 'dividends_paid',          format: 'dollar' },
  { label: 'Share Buybacks',          key: 'share_buybacks',          format: 'dollar' },
  { label: 'Financing Cash Flow',     key: 'financing_cash_flow',     format: 'dollar', separator: true },
  { label: 'Free Cash Flow',          key: 'free_cash_flow',          format: 'dollar', separator: true },
  { label: 'FCF Margin',              key: 'fcf_margin',              format: 'pct' },
];

type FinancialSubTab = 'income' | 'balance' | 'cashflow';

const ITEMS_BY_TAB: Record<FinancialSubTab, LineItem[]> = {
  income: INCOME_ITEMS,
  balance: BALANCE_ITEMS,
  cashflow: CASHFLOW_ITEMS,
};

const SUB_TAB_LABELS: { key: SubTab; label: string }[] = [
  { key: 'income',    label: 'Income Statement' },
  { key: 'balance',   label: 'Balance Sheet' },
  { key: 'cashflow',  label: 'Cash Flow' },
  { key: 'readiness', label: 'Data Readiness' },
];

// ---------------------------------------------------------------------------
// Inspect helpers
// ---------------------------------------------------------------------------

function getFieldMeta(
  fieldKey: string,
  readinessData: DataReadinessResult | null,
): FieldMetadataEntry | null {
  if (!readinessData) return null;
  const backendKey = toBackendKey(fieldKey);
  return readinessData.field_metadata[backendKey] ?? null;
}

function getMissingIndicatorLevel(meta: FieldMetadataEntry | null): 'critical' | 'important' | null {
  if (!meta || meta.engines.length === 0) return null;
  if (meta.engines.some((e) => e.level === 'critical')) return 'critical';
  if (meta.engines.some((e) => e.level === 'important')) return 'important';
  return null;
}

// ---------------------------------------------------------------------------
// Popover state
// ---------------------------------------------------------------------------

interface PopoverInfo {
  fieldKey: string;
  label: string;
  value: string;
  year: number;
  meta: FieldMetadataEntry;
  rect: DOMRect;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function HistoricalDataTab() {
  const activeTicker = useModelStore((s) => s.activeTicker);
  const [subTab, setSubTab] = useState<SubTab>('income');
  const [data, setData] = useState<FinancialRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inspect mode
  const [inspectMode, setInspectMode] = useState(false);
  const [readinessData, setReadinessData] = useState<DataReadinessResult | null>(null);
  const [popover, setPopover] = useState<PopoverInfo | null>(null);
  const tableWrapperRef = useRef<HTMLDivElement>(null);

  const fetchFinancials = useCallback(async (ticker: string) => {
    setLoading(true);
    setError(null);
    setData([]);
    try {
      const result = await api.get<FinancialRecord[]>(
        `/api/v1/companies/${ticker}/financials?years=10`,
      );
      setData(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load financials';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTicker) {
      void fetchFinancials(activeTicker);
      setReadinessData(null);
      setInspectMode(false);
    } else {
      setData([]);
      setError(null);
    }
  }, [activeTicker, fetchFinancials]);

  // Fetch readiness data when inspect mode turns on
  useEffect(() => {
    if (inspectMode && !readinessData && activeTicker) {
      void (async () => {
        try {
          const result = await api.get<DataReadinessResult>(
            `/api/v1/model-builder/${activeTicker}/data-readiness`,
          );
          setReadinessData(result);
        } catch {
          // Silently fail — inspect just won't show metadata
        }
      })();
    }
  }, [inspectMode, readinessData, activeTicker]);

  const years = useMemo(() => data.map((d) => d.fiscal_year), [data]);
  const isFinancialTab = subTab === 'income' || subTab === 'balance' || subTab === 'cashflow';
  const lineItems = isFinancialTab ? ITEMS_BY_TAB[subTab as FinancialSubTab] : [];

  // Freshness info
  const freshnessDate = useMemo(() => {
    if (data.length === 0) return null;
    const newest = data[0];
    return newest?.period_end_date ?? `FY ${newest?.fiscal_year}`;
  }, [data]);

  // Cell hover handlers
  function handleCellEnter(
    e: React.MouseEvent<HTMLTableCellElement>,
    fieldKey: string,
    label: string,
    value: string,
    year: number,
  ) {
    if (!inspectMode || !readinessData) return;
    const meta = getFieldMeta(fieldKey, readinessData);
    if (!meta) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setPopover({ fieldKey, label, value, year, meta, rect });
  }

  function handleCellLeave() {
    setPopover(null);
  }

  // --- No ticker ---
  if (!activeTicker) {
    return (
      <div className={styles.empty}>Select a ticker to view historical financials.</div>
    );
  }

  // --- Loading ---
  if (loading) {
    return (
      <div className={styles.loading}>
        <LoadingSpinner />
        <span className={styles.loadingText}>Loading financials for {activeTicker}...</span>
      </div>
    );
  }

  // --- Error ---
  if (error) {
    return (
      <div className={styles.error}>
        <span className={styles.errorText}>{error}</span>
        <button className={styles.retryBtn} onClick={() => void fetchFinancials(activeTicker)}>
          Retry
        </button>
      </div>
    );
  }

  // --- No data (but only block on financial tabs, readiness tab fetches its own data) ---
  if (data.length === 0 && isFinancialTab) {
    return <div className={styles.empty}>No financial data available for {activeTicker}.</div>;
  }

  return (
    <div className={styles.container}>
      {/* Sub-tab bar + inspect toggle */}
      <div className={styles.subTabBarRow}>
        <div className={styles.subTabBar}>
          {SUB_TAB_LABELS.map(({ key, label }) => (
            <button
              key={key}
              className={`${styles.subTab} ${subTab === key ? styles.subTabActive : ''}`}
              onClick={() => { setSubTab(key); setPopover(null); }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Inspect toggle — only on financial tabs */}
        {isFinancialTab && (
          <div className={styles.inspectToggle}>
            <label className={styles.toggleLabel}>
              <input
                type="checkbox"
                checked={inspectMode}
                onChange={(e) => { setInspectMode(e.target.checked); setPopover(null); }}
                className={styles.toggleInput}
              />
              <span className={styles.toggleSlider} />
              <span className={styles.toggleText}>Inspect</span>
            </label>
          </div>
        )}
      </div>

      {/* Readiness tab */}
      {subTab === 'readiness' && <DataReadinessTab />}

      {/* Financial table tabs */}
      {isFinancialTab && (
        <>
          {/* Freshness indicator */}
          {freshnessDate && (
            <div className={styles.freshnessRow}>
              <span className={styles.freshnessText}>
                Data as of {freshnessDate} &middot; {data.length} fiscal years
              </span>
              <button
                className={styles.refreshBtn}
                onClick={() => void fetchFinancials(activeTicker)}
              >
                &#x21bb; Refresh
              </button>
            </div>
          )}

          {/* Transposed table */}
          <div className={styles.tableWrapper} ref={tableWrapperRef}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.headerRow}>
                  <th>Line Item</th>
                  {years.map((y) => (
                    <th key={y} className={styles.yearCol}>FY {y}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, rowIdx) => {
                  const isSep = item.separator === true;
                  const rowClass = [
                    styles.dataRow,
                    isSep ? styles.sectionSeparator : (rowIdx % 2 === 0 ? styles.rowOdd : styles.rowEven),
                  ].join(' ');

                  return (
                    <tr key={item.key} className={rowClass}>
                      <td>{item.label}</td>
                      {data.map((record, colIdx) => {
                        const raw = record[item.key] as number | null;
                        const formatted = formatValue(raw, item.format);
                        const missing = isMissing(raw);
                        const negative = !missing && isNeg(raw);

                        // Inspect mode classes
                        let inspectClass = '';
                        if (inspectMode && readinessData) {
                          const meta = getFieldMeta(item.key, readinessData);
                          if (missing && meta) {
                            const level = getMissingIndicatorLevel(meta);
                            if (level === 'critical') inspectClass = styles.missingCritical ?? '';
                            else if (level === 'important') inspectClass = styles.missingImportant ?? '';
                          } else if (!missing && meta && (meta.status === 'present' || meta.status === 'derived')) {
                            inspectClass = styles.glassBubble ?? '';
                          }
                        }

                        const cellClasses = [
                          missing ? styles.missing : negative ? styles.negative : undefined,
                          inspectClass || undefined,
                        ].filter(Boolean).join(' ') || undefined;

                        return (
                          <td
                            key={colIdx}
                            className={cellClasses}
                            title={missing ? `Not reported by ${activeTicker}` : undefined}
                            onMouseEnter={(e) => handleCellEnter(e, item.key, item.label, formatted, record.fiscal_year)}
                            onMouseLeave={handleCellLeave}
                          >
                            {formatted}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Popover */}
            {popover && tableWrapperRef.current && (() => {
              const wrapperRect = tableWrapperRef.current!.getBoundingClientRect();
              const top = popover.rect.top - wrapperRect.top;
              const cellCenterX = popover.rect.left - wrapperRect.left + popover.rect.width / 2;
              const popoverWidth = 260;
              // Position to right of cell, or left if near right edge
              const nearRightEdge = cellCenterX + popoverWidth > wrapperRect.width;
              const left = nearRightEdge
                ? popover.rect.left - wrapperRect.left - popoverWidth - 4
                : popover.rect.right - wrapperRect.left + 4;

              return (
                <div
                  className={styles.popover}
                  style={{ top, left: Math.max(0, left) }}
                >
                  <div className={styles.popoverTitle}>
                    {popover.label} &middot; FY {popover.year}
                  </div>
                  <div className={styles.popoverValue}>{popover.value}</div>
                  <div className={styles.popoverDivider} />
                  <div className={styles.popoverRow}>
                    <span>Source:</span>
                    <span>
                      {popover.meta.status === 'missing'
                        ? 'NOT REPORTED'
                        : popover.meta.source?.startsWith('computed')
                          ? popover.meta.source
                          : 'Yahoo Finance (direct)'}
                    </span>
                  </div>
                  <div className={styles.popoverRow}>
                    <span>Years:</span>
                    <span>{popover.meta.years_available}</span>
                  </div>
                  {popover.meta.engines.length > 0 && (
                    <>
                      <div className={styles.popoverDivider} />
                      <div className={styles.popoverEngineHeader}>Used by:</div>
                      {popover.meta.engines.map((eng, i) => (
                        <div key={i} className={styles.popoverEngineRow}>
                          {displayModelName(eng.engine)} — {eng.level} ({eng.reason})
                        </div>
                      ))}
                    </>
                  )}
                </div>
              );
            })()}
          </div>
        </>
      )}
    </div>
  );
}
