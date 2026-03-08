# Finance App — Cross-Cutting: Underscore Syntax Cleanup (Global)
## Applies Across All Phases

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Global audit and fix for all `xxx_xxx` raw backend key names leaking into the UI across every module

---

## PROBLEM

Backend Python uses `snake_case` for all field names, model types, status labels, and enum values (e.g., `revenue_based`, `SIGNIFICANT_DISAGREEMENT`, `high_growth`, `ex_dividend`, `price_above`, `total_current_assets`). The frontend has inconsistent handling — some components use `MODEL_LABELS` maps to convert these to display names, others show the raw key with `replace(/_/g, ' ')`, and some don't transform at all.

This results in the UI showing things like:
- "revenue_based" instead of "Revenue-Based"
- "high_growth" instead of "High Growth"
- "ex_dividend" instead of "Ex-Dividend"
- "price_above" instead of "Price Above"
- "SIGNIFICANT_DISAGREEMENT" instead of "Significant Disagreement"
- Various metric names in scanner, ratios, alerts showing raw keys

---

## SOLUTION

### 1. Shared Display Name Utility
Create a single utility file that all components import:

**File:** `frontend/src/utils/displayNames.ts`

```typescript
// Model types
const MODEL_NAMES: Record<string, string> = {
  dcf: 'DCF',
  ddm: 'DDM',
  comps: 'Comps',
  revenue_based: 'Revenue-Based',
  Composite: 'Composite',
};

// Agreement levels
const AGREEMENT_LEVELS: Record<string, string> = {
  STRONG: 'Strong Agreement',
  MODERATE: 'Moderate Agreement',
  WEAK: 'Weak Agreement',
  SIGNIFICANT_DISAGREEMENT: 'Significant Disagreement',
  'N/A': 'N/A',
};

// DDM stages
const DDM_STAGES: Record<string, string> = {
  high_growth: 'High Growth',
  transition: 'Transition',
  terminal: 'Terminal',
};

// Event types
const EVENT_TYPES: Record<string, string> = {
  earnings: 'Earnings',
  ex_dividend: 'Ex-Dividend',
  dividend: 'Dividend',
  filing: 'Filing',
};

// Alert types
const ALERT_TYPES: Record<string, string> = {
  price_above: 'Price Above',
  price_below: 'Price Below',
  pct_change: '% Change',
  intrinsic_cross: 'Intrinsic Cross',
};

// Transaction types
const TX_TYPES: Record<string, string> = {
  BUY: 'Buy',
  SELL: 'Sell',
  DIVIDEND: 'Dividend',
  DRIP: 'DRIP',
  SPLIT: 'Split',
  ADJUSTMENT: 'Adjustment',
};

// Generic fallback: replace underscores with spaces, title case
function titleCase(str: string): string {
  return str
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Public API
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

// Catch-all for any snake_case key that needs display formatting
export function displayLabel(key: string): string {
  // Check all known maps first
  return MODEL_NAMES[key]
    ?? AGREEMENT_LEVELS[key]
    ?? DDM_STAGES[key]
    ?? EVENT_TYPES[key]
    ?? ALERT_TYPES[key]
    ?? TX_TYPES[key]
    ?? titleCase(key);
}
```

### 2. Global Audit — Every File That Displays Backend Keys

The PM should instruct every Builder session to use the shared utility. Additionally, one dedicated cleanup pass should audit all display paths. Here are the known locations:

**Model Builder (covered in 8A, 8I):**
- `OverviewTab.tsx` — included_models, excluded_models tags
- `FootballField.tsx` — model_name labels
- `ScenarioTable.tsx` — model_name labels
- `WeightsPanel.tsx` — weight keys, excluded_models
- `AgreementPanel.tsx` — level badge, model names in divergence pairs
- `DCFView.tsx` — scenario labels (already mapped, verify)
- `DDMView.tsx` — stage badges, sustainability metric names
- `CompsView.tsx` — implied value method names (`key.replace(/_/g, '/').toUpperCase()`)
- `RevBasedView.tsx` — status labels, metric names
- `ModelBuilderPage.tsx` — MODEL_TYPE_LABELS (already mapped, verify)

**Dashboard (covered in 7D):**
- `UpcomingEventsWidget.tsx` — event_type display

**Portfolio:**
- `AlertsTab.tsx` — ALERT_TYPE_LABELS (has a map but verify completeness)
- `TransactionsTab.tsx` — transaction_type badges
- `HoldingsTable.tsx` — sector/industry display (may come as snake_case from DB)
- `PositionDetail.tsx` — transaction type badges
- `PerformanceTab.tsx` — period labels, attribution sector names
- `AttributionTable.tsx` — sector names, effect labels

**Scanner:**
- `ResultsTable.tsx` — metric column headers (use MetricDefinition.label, should be clean)
- `FilterRow.tsx` — metric names in filter dropdowns
- `DetailPanel.tsx` — KEY_METRIC_LABELS (has a map, verify)

**Research:**
- `RatiosTab.tsx` — ratio category names, metric names (uses ratioConfig which should have labels)
- `PeersTab.tsx` — metric column headers
- `FilingsTab.tsx` — form_type labels (10-K, 10-Q already clean)
- `ProfileTab.tsx` — event types in upcoming events

**Settings:**
- Various setting keys displayed as labels — verify all use proper display names

### 3. Implementation Rule for All Builder Sessions

**Every Builder prompt from the PM must include this instruction:**

> **Display Name Rule:** All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility (`import { displayModelName, displayLabel } from '@/utils/displayNames'`). Never show raw keys like `revenue_based` or `high_growth` to the user. Never use inline `.replace(/_/g, ' ')` — always use the shared utility for consistency.

This ensures that even sessions that don't explicitly mention the underscore fix still follow the convention.

---

## SESSION HANDLING

This is NOT a separate session. Instead:

1. **Session 8A (Overview)** creates the `displayNames.ts` utility file and migrates Overview components. This is already planned.
2. **Session 8I** migrates all Model tab components. Already planned.
3. **Every subsequent session** must use the utility for any new or modified components. The PM includes the instruction in every Builder prompt.
4. **If a dedicated cleanup pass is needed** after all feature sessions: add a Session 14C (or similar) that audits every component file for raw snake_case display and migrates any stragglers.

---

## DECISIONS MADE

1. Single shared `displayNames.ts` utility — all components import from here
2. Known maps for models, agreement levels, DDM stages, events, alerts, transactions
3. Generic `titleCase` fallback for any unmapped key
4. `displayLabel()` catch-all function checks all maps before falling back
5. Every Builder prompt includes the display name rule
6. Created in session 8A, enforced in all subsequent sessions
7. Optional final audit pass to catch any stragglers

---

*End of Cross-Cutting Underscore Syntax Cleanup Spec*
*Enforced across Phases 7–14 · Prepared March 5, 2026*
