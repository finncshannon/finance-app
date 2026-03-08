import { useState, useEffect, useCallback } from 'react';
import { useModelStore } from '../../../stores/modelStore';
import { api } from '../../../services/api';
import { LoadingSpinner } from '../../../components/ui/Loading/LoadingSpinner';
import type { Table2DResult, SensitivityParameterDef } from '../../../types/models';
import styles from './DataTablePanel.module.css';

/** Map backend color name to CSS class. */
function colorClass(color: string): string {
  switch (color) {
    case 'bright_green': return styles.cellBrightGreen ?? '';
    case 'green':        return styles.cellGreen ?? '';
    case 'light_green':  return styles.cellLightGreen ?? '';
    case 'light_red':    return styles.cellLightRed ?? '';
    case 'red':          return styles.cellRed ?? '';
    case 'bright_red':   return styles.cellBrightRed ?? '';
    case 'neutral':
    default:             return styles.cellNeutral ?? '';
  }
}

function formatCellValue(value: number): string {
  return `$${value.toFixed(2)}`;
}

function formatUpside(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(1)}%`;
}

/** Format header values based on magnitude (percentage vs dollar). */
function formatHeaderValue(value: number): string {
  // Heuristic: if value < 1, it's likely a percentage/rate
  if (Math.abs(value) < 1) {
    return `${(value * 100).toFixed(1)}%`;
  }
  return value.toFixed(1);
}

const PRESETS = [
  { label: 'WACC \u00d7 Terminal Growth', row: 'scenarios.{s}.wacc', col: 'scenarios.{s}.terminal_growth_rate' },
  { label: 'WACC \u00d7 Exit Multiple', row: 'scenarios.{s}.wacc', col: 'model_assumptions.dcf.terminal_exit_multiple' },
  { label: 'Rev Growth \u00d7 Op Margin', row: 'scenarios.{s}.revenue_growth_rates[0]', col: 'scenarios.{s}.operating_margins[0]' },
];

export function DataTablePanel() {
  const ticker = useModelStore((s) => s.activeTicker);

  const [data, setData] = useState<Table2DResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rowVar, setRowVar] = useState<string | null>(null);
  const [colVar, setColVar] = useState<string | null>(null);
  const [rowMin, setRowMin] = useState<string>('');
  const [rowMax, setRowMax] = useState<string>('');
  const [colMin, setColMin] = useState<string>('');
  const [colMax, setColMax] = useState<string>('');
  const [gridSize, setGridSize] = useState(9);
  const [paramDefs, setParamDefs] = useState<SensitivityParameterDef[]>([]);

  useEffect(() => {
    if (!ticker) return;
    api.get<SensitivityParameterDef[]>(`/api/v1/model-builder/${ticker}/sensitivity/parameters`)
      .then(setParamDefs).catch(() => {});
  }, [ticker]);

  const fetchTable = useCallback(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    const body: Record<string, unknown> = { grid_size: gridSize };
    if (rowVar) body.row_variable = rowVar;
    if (colVar) body.col_variable = colVar;
    const rMin = parseFloat(rowMin);
    const rMax = parseFloat(rowMax);
    const cMin = parseFloat(colMin);
    const cMax = parseFloat(colMax);
    if (!isNaN(rMin) && !isNaN(rMax)) { body.row_min = rMin; body.row_max = rMax; }
    if (!isNaN(cMin) && !isNaN(cMax)) { body.col_min = cMin; body.col_max = cMax; }

    api.post<Table2DResult>(`/api/v1/model-builder/${ticker}/sensitivity/table-2d`, body)
      .then((result) => { setData(result); setLoading(false); })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to generate table';
        setError(msg);
        setLoading(false);
      });
  }, [ticker, gridSize, rowVar, colVar, rowMin, rowMax, colMin, colMax]);

  // Fetch table on mount
  useEffect(() => {
    fetchTable();
  }, [fetchTable]);

  if (!ticker) return null;

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <LoadingSpinner />
        <span className={styles.loadingText}>Computing sensitivity table...</span>
      </div>
    );
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  if (!data) return null;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.title}>2D Sensitivity Table</span>
        <div className={styles.meta}>
          <span className={styles.metaItem}>
            Base Price:{' '}
            <span className={styles.metaValue}>
              ${data.base_price.toFixed(2)}
            </span>
          </span>
          <span className={styles.metaItem}>
            Current:{' '}
            <span className={styles.metaValue}>
              ${data.current_price.toFixed(2)}
            </span>
          </span>
          <span className={styles.metaItem}>
            {data.grid_size}x{data.grid_size} grid
          </span>
          <span className={styles.metaItem}>
            {data.computation_time_ms.toFixed(0)}ms
          </span>
        </div>
      </div>

      {/* Variable labels */}
      <div className={styles.variableLabels}>
        <div className={styles.variableTag}>
          <span className={styles.variableAxis}>Row</span>
          <span>{data.row_variable}</span>
        </div>
        <div className={styles.variableTag}>
          <span className={styles.variableAxis}>Col</span>
          <span>{data.col_variable}</span>
        </div>
      </div>

      {/* Controls */}
      <div className={styles.controls}>
        {/* Variable selectors */}
        <div className={styles.controlRow}>
          <label className={styles.controlLabel}>Row:</label>
          <select className={styles.select} value={rowVar ?? ''} onChange={(e) => setRowVar(e.target.value || null)}>
            <option value="">Default (WACC)</option>
            {paramDefs.filter((p) => p.key_path !== colVar).map((p) => (
              <option key={p.key_path} value={p.key_path}>{p.name}</option>
            ))}
          </select>
          <label className={styles.controlLabel}>Col:</label>
          <select className={styles.select} value={colVar ?? ''} onChange={(e) => setColVar(e.target.value || null)}>
            <option value="">Default (Terminal Growth)</option>
            {paramDefs.filter((p) => p.key_path !== rowVar).map((p) => (
              <option key={p.key_path} value={p.key_path}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Range inputs */}
        <div className={styles.controlRow}>
          <label className={styles.controlLabel}>Row Range:</label>
          <input type="number" className={styles.rangeInput} value={rowMin} placeholder="Min" onChange={(e) => setRowMin(e.target.value)} />
          <span className={styles.rangeSeparator}>to</span>
          <input type="number" className={styles.rangeInput} value={rowMax} placeholder="Max" onChange={(e) => setRowMax(e.target.value)} />
          <label className={styles.controlLabel}>Col Range:</label>
          <input type="number" className={styles.rangeInput} value={colMin} placeholder="Min" onChange={(e) => setColMin(e.target.value)} />
          <span className={styles.rangeSeparator}>to</span>
          <input type="number" className={styles.rangeInput} value={colMax} placeholder="Max" onChange={(e) => setColMax(e.target.value)} />
        </div>

        {/* Grid size + Generate */}
        <div className={styles.controlRow}>
          <label className={styles.controlLabel}>Grid:</label>
          <select className={styles.gridSelect} value={gridSize} onChange={(e) => setGridSize(Number(e.target.value))}>
            {[5, 7, 9, 11, 13].map((n) => (
              <option key={n} value={n}>{n}\u00d7{n}</option>
            ))}
          </select>
          <button className={styles.generateBtn} onClick={fetchTable}>Generate Table</button>
        </div>

        {/* Presets */}
        <div className={styles.presetRow}>
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              className={styles.presetBtn}
              onClick={() => {
                setRowVar(preset.row);
                setColVar(preset.col);
                setRowMin(''); setRowMax(''); setColMin(''); setColMax('');
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            {/* Column variable label row */}
            <tr>
              <th className={styles.cornerCell} />
              <th
                className={styles.colHeaderLabel}
                colSpan={data.col_values.length}
              >
                {data.col_variable}
              </th>
            </tr>
            {/* Column header values */}
            <tr>
              <th className={styles.cornerCell} />
              {data.col_values.map((cv, ci) => (
                <th key={ci} className={styles.colHeader}>
                  {formatHeaderValue(cv)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.row_values.map((rv, ri) => (
              <tr key={ri}>
                <td className={styles.rowHeader}>
                  {formatHeaderValue(rv)}
                </td>
                {data.col_values.map((colVal, ci) => {
                  const price = data.price_matrix[ri]?.[ci];
                  const upside = data.upside_matrix[ri]?.[ci];
                  const color = data.color_matrix[ri]?.[ci] ?? 'neutral';
                  const isBase =
                    ri === data.base_row_index && ci === data.base_col_index;
                  const cellColor = colorClass(color);
                  const rowVal = rv;

                  return (
                    <td
                      key={ci}
                      className={[
                        styles.cell,
                        cellColor,
                        isBase ? (styles.cellBase ?? '') : '',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      title={
                        price != null && upside != null
                          ? `${data.row_variable}: ${formatHeaderValue(rowVal)}, ${data.col_variable}: ${formatHeaderValue(colVal)} \u2192 $${price.toFixed(2)} (${upside >= 0 ? '+' : ''}${(upside * 100).toFixed(1)}%)`
                          : undefined
                      }
                    >
                      {price != null ? formatCellValue(price) : '--'}
                      {upside != null && (
                        <span className={styles.cellUpside}>
                          {formatUpside(upside)}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
