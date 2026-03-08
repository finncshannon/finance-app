import type { FinancialRow } from '../types';

export interface LineItemDef {
  key: string;
  label: string;
  isBold?: boolean;
  isComputed?: boolean;
  indent?: number;
  format?: 'millions' | 'pct' | 'perShare' | 'ratio';
  computeFn?: (row: FinancialRow, prevRow?: FinancialRow) => number | null;
}

export const INCOME_STATEMENT: LineItemDef[] = [
  { key: 'revenue', label: 'Revenue', format: 'millions' },
  { key: 'revenue_growth', label: 'YoY Growth', isComputed: true, format: 'pct', indent: 1 },
  { key: 'cost_of_revenue', label: 'Cost of Revenue', format: 'millions', indent: 1 },
  { key: 'gross_profit', label: 'GROSS PROFIT', format: 'millions', isBold: true },
  { key: 'gross_margin', label: 'Gross Margin', isComputed: true, format: 'pct', indent: 1 },
  { key: 'rd_expense', label: 'Research & Development', format: 'millions', indent: 1 },
  { key: 'sga_expense', label: 'Selling, General & Administrative', format: 'millions', indent: 1 },
  { key: 'operating_expense', label: 'Total Operating Expenses', format: 'millions' },
  { key: 'ebit', label: 'OPERATING INCOME', format: 'millions', isBold: true },
  { key: 'operating_margin', label: 'Operating Margin', isComputed: true, format: 'pct', indent: 1 },
  { key: 'interest_expense', label: 'Interest Expense', format: 'millions', indent: 1 },
  { key: 'tax_provision', label: 'Income Tax Expense', format: 'millions', indent: 1 },
  { key: 'net_income', label: 'NET INCOME', format: 'millions', isBold: true },
  { key: 'net_margin', label: 'Net Margin', isComputed: true, format: 'pct', indent: 1 },
  { key: 'ebitda', label: 'EBITDA', format: 'millions' },
  {
    key: 'ebitda_margin',
    label: 'EBITDA Margin',
    isComputed: true,
    format: 'pct',
    indent: 1,
    computeFn: (row) => {
      const rev = row.revenue as number | null;
      const eb = row.ebitda as number | null;
      if (rev == null || eb == null || rev === 0) return null;
      return eb / rev;
    },
  },
  { key: 'eps_basic', label: 'EPS (Basic)', format: 'perShare' },
  { key: 'eps_diluted', label: 'EPS (Diluted)', format: 'perShare' },
  { key: 'shares_outstanding', label: 'Shares Outstanding', format: 'millions' },
];

export const BALANCE_SHEET: LineItemDef[] = [
  { key: 'cash_and_equivalents', label: 'Cash & Equivalents', format: 'millions' },
  { key: 'current_assets', label: 'Total Current Assets', format: 'millions' },
  { key: 'total_assets', label: 'TOTAL ASSETS', format: 'millions', isBold: true },
  { key: 'current_liabilities', label: 'Total Current Liabilities', format: 'millions' },
  { key: 'long_term_debt', label: 'Long-Term Debt', format: 'millions', indent: 1 },
  { key: 'total_liabilities', label: 'TOTAL LIABILITIES', format: 'millions', isBold: true },
  { key: 'stockholders_equity', label: 'STOCKHOLDERS EQUITY', format: 'millions', isBold: true },
  {
    key: 'working_capital',
    label: 'Working Capital',
    isComputed: true,
    format: 'millions',
    computeFn: (row) => {
      const ca = row.current_assets as number | null;
      const cl = row.current_liabilities as number | null;
      if (ca == null || cl == null) return null;
      return ca - cl;
    },
  },
  {
    key: 'current_ratio',
    label: 'Current Ratio',
    isComputed: true,
    format: 'ratio',
    computeFn: (row) => {
      const ca = row.current_assets as number | null;
      const cl = row.current_liabilities as number | null;
      if (ca == null || cl == null || cl === 0) return null;
      return ca / cl;
    },
  },
  { key: 'debt_to_equity', label: 'Debt / Equity', isComputed: true, format: 'ratio' },
  {
    key: 'net_debt',
    label: 'Net Debt',
    isComputed: true,
    format: 'millions',
    computeFn: (row) => {
      const debt = (row.total_debt ?? row.long_term_debt) as number | null;
      const cash = row.cash_and_equivalents as number | null;
      if (debt == null || cash == null) return null;
      return debt - cash;
    },
  },
];

export const CASH_FLOW_STATEMENT: LineItemDef[] = [
  { key: 'operating_cash_flow', label: 'Cash from Operations', format: 'millions' },
  { key: 'capital_expenditure', label: 'Capital Expenditure', format: 'millions', indent: 1 },
  { key: 'free_cash_flow', label: 'FREE CASH FLOW', format: 'millions', isBold: true },
  {
    key: 'fcf_margin',
    label: 'FCF Margin',
    isComputed: true,
    format: 'pct',
    indent: 1,
    computeFn: (row) => {
      const rev = row.revenue as number | null;
      const fcf = row.free_cash_flow as number | null;
      if (rev == null || fcf == null || rev === 0) return null;
      return fcf / rev;
    },
  },
  { key: 'depreciation_amortization', label: 'Depreciation & Amortization', format: 'millions', indent: 1 },
  { key: 'investing_cash_flow', label: 'Cash from Investing', format: 'millions' },
  { key: 'financing_cash_flow', label: 'Cash from Financing', format: 'millions' },
  { key: 'dividends_paid', label: 'Dividends Paid', format: 'millions', indent: 1 },
  { key: 'payout_ratio', label: 'Payout Ratio', isComputed: true, format: 'pct', indent: 1 },
];
