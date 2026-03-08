const MODEL_NAMES: Record<string, string> = {
  dcf: 'DCF',
  ddm: 'DDM',
  comps: 'Comps',
  revenue_based: 'Revenue-Based',
  Composite: 'Composite',
};

const AGREEMENT_LEVELS: Record<string, string> = {
  STRONG: 'Strong Agreement',
  MODERATE: 'Moderate Agreement',
  WEAK: 'Weak Agreement',
  SIGNIFICANT_DISAGREEMENT: 'Significant Disagreement',
  'N/A': 'N/A',
};

const DDM_STAGES: Record<string, string> = {
  high_growth: 'High Growth',
  transition: 'Transition',
  terminal: 'Terminal',
};

const EVENT_TYPES: Record<string, string> = {
  earnings: 'Earnings',
  ex_dividend: 'Ex-Dividend',
  dividend: 'Dividend',
  filing: 'Filing',
};

const ALERT_TYPES: Record<string, string> = {
  price_above: 'Price Above',
  price_below: 'Price Below',
  pct_change: '% Change',
  intrinsic_cross: 'Intrinsic Cross',
};

const TX_TYPES: Record<string, string> = {
  BUY: 'Buy',
  SELL: 'Sell',
  DIVIDEND: 'Dividend',
  DRIP: 'DRIP',
  SPLIT: 'Split',
  ADJUSTMENT: 'Adjustment',
};

function titleCase(str: string): string {
  return str
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function displayModelName(key: string): string {
  return MODEL_NAMES[key] ?? titleCase(key);
}

export function displayAgreementLevel(level: string): string {
  return AGREEMENT_LEVELS[level] ?? titleCase(level);
}

export function displayStageName(stage: string): string {
  return DDM_STAGES[stage] ?? titleCase(stage);
}

export function displayEventType(type: string): string {
  return EVENT_TYPES[type] ?? titleCase(type);
}

export function displayAlertType(type: string): string {
  return ALERT_TYPES[type] ?? titleCase(type);
}

export function displayTransactionType(type: string): string {
  return TX_TYPES[type] ?? type;
}

export function displayLabel(key: string): string {
  return MODEL_NAMES[key]
    ?? AGREEMENT_LEVELS[key]
    ?? DDM_STAGES[key]
    ?? EVENT_TYPES[key]
    ?? ALERT_TYPES[key]
    ?? TX_TYPES[key]
    ?? titleCase(key);
}
