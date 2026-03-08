import React, { useState, useCallback, useMemo } from 'react';
import styles from './DataTable.module.css';

export interface Column {
  key: string;
  label: string;
  align?: 'left' | 'center' | 'right';
  sortable?: boolean;
  format?: (value: unknown, row: Record<string, unknown>) => React.ReactNode;
}

type SortDirection = 'asc' | 'desc';

interface SortState {
  key: string;
  direction: SortDirection;
}

interface DataTableProps {
  columns: Column[];
  data: Record<string, unknown>[];
  onSort?: (key: string, direction: SortDirection) => void;
  className?: string;
}

export function DataTable({ columns, data, onSort, className }: DataTableProps) {
  const [sortState, setSortState] = useState<SortState | null>(null);

  const handleSort = useCallback(
    (key: string) => {
      const col = columns.find((c) => c.key === key);
      if (!col?.sortable) return;

      let direction: SortDirection = 'asc';
      if (sortState?.key === key && sortState.direction === 'asc') {
        direction = 'desc';
      }

      setSortState({ key, direction });
      onSort?.(key, direction);
    },
    [columns, sortState, onSort],
  );

  const sortedData = useMemo(() => {
    if (!sortState || onSort) return data;

    const { key, direction } = sortState;
    return [...data].sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];

      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      let cmp = 0;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        cmp = aVal - bVal;
      } else {
        cmp = String(aVal).localeCompare(String(bVal));
      }

      return direction === 'desc' ? -cmp : cmp;
    });
  }, [data, sortState, onSort]);

  const getAlignClass = (align?: string, isFirst?: boolean) => {
    if (isFirst) return styles.tdLabel;
    if (align === 'left') return styles.tdLeft;
    if (align === 'center') return styles.tdCenter;
    return '';
  };

  const getHeaderAlignClass = (align?: string, isFirst?: boolean) => {
    if (isFirst || align === 'left') return styles.thLeft;
    if (align === 'center') return styles.thCenter;
    return '';
  };

  const renderSortIndicator = (key: string) => {
    if (sortState?.key !== key) return null;
    return (
      <span className={styles.sortIndicator}>
        {sortState.direction === 'asc' ? '\u25B2' : '\u25BC'}
      </span>
    );
  };

  const wrapperClasses = [styles.wrapper, className ?? ''].filter(Boolean).join(' ');

  return (
    <div className={wrapperClasses}>
      <table className={styles.table}>
        <thead className={styles.thead}>
          <tr>
            {columns.map((col, i) => (
              <th
                key={col.key}
                className={[
                  styles.th,
                  getHeaderAlignClass(col.align, i === 0),
                  col.sortable ? styles.sortable : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onClick={() => col.sortable && handleSort(col.key)}
              >
                {col.label}
                {col.sortable && renderSortIndicator(col.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.length === 0 ? (
            <tr>
              <td className={styles.empty} colSpan={columns.length}>
                No data
              </td>
            </tr>
          ) : (
            sortedData.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className={[
                  styles.row,
                  rowIdx % 2 === 0 ? styles.rowOdd : styles.rowEven,
                ].join(' ')}
              >
                {columns.map((col, colIdx) => {
                  const raw = row[col.key];
                  const displayed = col.format ? col.format(raw, row) : (raw as React.ReactNode);
                  return (
                    <td
                      key={col.key}
                      className={[styles.td, getAlignClass(col.align, colIdx === 0)]
                        .filter(Boolean)
                        .join(' ')}
                    >
                      {displayed}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
