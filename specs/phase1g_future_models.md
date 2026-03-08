# Phase 1G — Future Models & Plugin Architecture
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 1A-1F (all model specs)

---

## Overview

Beyond the four core models (DCF, DDM, Comps, Revenue-Based), the app is
designed to support additional valuation models through a consistent
plugin architecture. Two future models are planned: LBO and NAV.

This document defines the plugin contract that ALL models must implement,
plus scoping for the two future models.

---

## Part 1: Model Plugin Architecture

### 1.1 Model Interface Contract

Every valuation model — current and future — must implement this interface:

```python
class BaseValuationModel:
    """
    Contract that every model plugin must fulfill.
    The Model Builder, Assumption Engine, and UI all depend on
    this interface being consistent.
    """

    # ── Identity ──────────────────────────────────────────────
    model_type: str           # "dcf", "ddm", "comps", "revenue_based", "lbo", "nav"
    display_name: str         # "Discounted Cash Flow", "Net Asset Value", etc.
    short_name: str           # "DCF", "NAV", etc.
    description: str          # One-line description for UI tooltips

    # ── Applicability ─────────────────────────────────────────
    def score_applicability(self, data: CompanyDataPackage) -> ModelScore:
        """
        Given a company's data, return a 0-100 score indicating how
        applicable this model is, plus reasoning.

        Returns:
          ModelScore {
            score: int (0-100)
            applicable: bool (score > threshold)
            reasoning: str
            required_data: list[str]    # what data this model needs
            missing_data: list[str]     # what's missing for this company
          }
        """

    # ── Assumptions ───────────────────────────────────────────
    def generate_assumptions(self, data: CompanyDataPackage) -> AssumptionSet:
        """
        Auto-generate all assumptions needed for this model.
        Each assumption includes value, confidence, and reasoning.

        Returns:
          AssumptionSet {
            assumptions: dict[str, Assumption]
            overall_confidence: int (0-100)
            data_quality: int (0-100)
          }

        Where Assumption {
            key: str
            display_name: str
            value: float
            unit: str ("percent", "ratio", "currency", "years", "count")
            confidence: int (0-100)
            reasoning: str
            reasoning_detailed: str
            is_overridable: bool
            min_value: float
            max_value: float
            step: float        # slider increment
            category: str      # grouping in Assumptions tab
          }
        """

    def get_assumption_schema(self) -> list[AssumptionDefinition]:
        """
        Return the full schema of assumptions this model uses.
        Used by the UI to build the Assumptions tab layout.
        """

    # ── Calculation ───────────────────────────────────────────
    def calculate(self, assumptions: AssumptionSet) -> ModelOutput:
        """
        Run the full model calculation given a set of assumptions.
        This is the core math.

        Returns:
          ModelOutput {
            intrinsic_value: float
            intrinsic_value_per_share: float
            scenarios: list[ScenarioResult]
            projection_table: ProjectionTable
            waterfall_data: WaterfallData
            sensitivity_variables: list[str]
            calculation_steps: list[CalculationStep]  # audit trail
            metadata: dict
          }
        """

    def calculate_sensitivity(self,
        assumptions: AssumptionSet,
        variables: list[str],
        ranges: dict[str, tuple[float, float]]
    ) -> SensitivityOutput:
        """
        Run sensitivity analysis on specified variables.
        Returns tornado, tables, and optionally Monte Carlo data.
        """

    # ── Display ───────────────────────────────────────────────
    def get_sub_tabs(self) -> list[SubTabDefinition]:
        """
        Return the sub-tab configuration for this model.
        Allows each model to define its own tab structure while
        keeping consistent patterns.

        Returns list of:
          SubTabDefinition {
            key: str
            display_name: str
            required: bool     # false = can be hidden
            order: int
          }
        """

    def get_waterfall_config(self) -> WaterfallConfig:
        """
        Define the waterfall chart structure for this model.
        Each model has different building blocks in its waterfall.
        """

    # ── Export ─────────────────────────────────────────────────
    def to_excel(self, output: ModelOutput) -> ExcelData:
        """
        Format model output for Excel export.
        Returns structured data that the export service renders.
        """

    def to_pdf(self, output: ModelOutput) -> PDFData:
        """
        Format model output for PDF export.
        """
```

### 1.2 Model Registration

New models register with the system through a registry:

```python
# backend/engines/registry.py

MODEL_REGISTRY = {
    "dcf": DCFEngine,
    "ddm": DDMEngine,
    "comps": CompsEngine,
    "revenue_based": RevenueEngine,
    # Future:
    # "lbo": LBOEngine,
    # "nav": NAVEngine,
}

def get_model(model_type: str) -> BaseValuationModel:
    return MODEL_REGISTRY[model_type]()

def get_all_models() -> list[BaseValuationModel]:
    return [cls() for cls in MODEL_REGISTRY.values()]

def score_all_models(data: CompanyDataPackage) -> list[ModelScore]:
    return [model.score_applicability(data) for model in get_all_models()]
```

### 1.3 Adding a New Model — Checklist

To add a new valuation model to the app:

**Backend:**
- [ ] Create `engines/new_engine.py` implementing `BaseValuationModel`
- [ ] Add assumption definitions to `assumption_engine.py` (model-specific section)
- [ ] Add Pydantic models for model-specific data in `models/valuation.py`
- [ ] Register in `engines/registry.py`
- [ ] Add database table for model-specific assumptions (migration script)
- [ ] Add applicability scoring logic to detector engine

**Frontend:**
- [ ] Create model-specific tab components in `modules/model-builder/tabs/`
- [ ] Add model-specific chart components if needed
- [ ] Register sub-tab configuration in Model Builder router
- [ ] Add model type to TypeScript types

**No changes needed to:**
- API endpoints (generic model endpoints handle all types)
- Overview/comparison panel (reads from standard ModelOutput)
- Sensitivity sub-module (reads from standard sensitivity variables)
- Export system (calls model's to_excel/to_pdf methods)
- Version history (works on any model type)

This is the power of the plugin architecture — new models slot in
without modifying existing code.

---

## Part 2: LBO Model (Future — Planned)

### 2.1 What It Is

Leveraged Buyout model — used by private equity firms to evaluate
an acquisition financed primarily with debt. Answers: "What return
would a PE firm get buying this company at the current price?"

### 2.2 When It Applies

- Company has stable, predictable cash flows
- Company has low existing leverage (room to add debt)
- Company is being evaluated as a PE target
- EBITDA margins are healthy and defensible
- Company is in a mature industry

Auto-detection signals:
- EV/EBITDA < 12x (reasonable acquisition multiple)
- Net Debt/EBITDA < 2x (room for leverage)
- FCF yield > 5% (cash generation supports debt service)
- Revenue growth < 15% (PE prefers stability over hyper-growth)

### 2.3 Key Inputs

```
Purchase price (EV or per share)
Financing structure:
  - Senior debt (amount, interest rate, term)
  - Subordinated debt (amount, interest rate, term)
  - Equity contribution
  - Debt/EBITDA target at entry
Revenue and EBITDA projections (5 years, from assumption engine)
Debt paydown schedule (mandatory amortization + cash sweep)
Exit assumptions:
  - Exit year (typically Year 5)
  - Exit multiple (EV/EBITDA at exit)
Management options / rollover equity (optional)
Transaction fees and expenses
```

### 2.4 Key Outputs

```
Entry metrics:
  - Purchase EV and equity check
  - Entry EV/EBITDA multiple
  - Debt/Equity split
  - Leverage ratios at entry

Projection table (5 years):
  - Revenue, EBITDA, FCF
  - Debt balance each year
  - Interest expense
  - Leverage ratio each year (should decline)

Exit analysis:
  - Exit EV (EBITDA × exit multiple)
  - Net debt at exit
  - Equity value at exit
  - Money-on-Money (MoM) return
  - Internal Rate of Return (IRR) — THE key metric

Sensitivity:
  - IRR sensitivity to entry multiple × exit multiple
  - IRR sensitivity to EBITDA growth × leverage
```

### 2.5 Sub-Tab Structure

```
LBO Model Sub-Tabs:
  Overview | Historical Data | Deal Structure | Projections | Returns Analysis | Sensitivity | History
```

- **Deal Structure:** Entry price, financing mix, debt terms — unique to LBO
- **Projections:** Revenue/EBITDA/FCF + debt paydown schedule
- **Returns Analysis:** IRR, MoM, equity value bridge — unique to LBO

### 2.6 Priority

Medium. LBO is valuable for evaluating PE-style investments and understanding
floor valuations (what a PE buyer would pay). Not needed for MVP but should
be one of the first post-launch additions.

---

## Part 3: NAV Model (Future — Planned)

### 3.1 What It Is

Net Asset Value model — values a company based on the fair market value
of its underlying assets minus liabilities. Standard approach for:
- REITs (real estate portfolios)
- Banks and financial institutions (loan books, securities portfolios)
- Holding companies / conglomerates
- Natural resource companies (proven reserves)
- Closed-end funds

### 3.2 When It Applies

- Company's value is primarily driven by assets, not earnings growth
- Balance sheet is more informative than income statement
- Company type: REIT, bank, insurance, holding company, resource company

Auto-detection signals:
- GICS sector: Real Estate, Financials
- Industry keywords in business description: "REIT", "trust", "bank",
  "insurance", "holding", "fund"
- Tangible book value is a significant portion of market cap
- P/B ratio is a primary valuation metric for the sector

### 3.3 Key Inputs

```
Asset categories (varies by company type):

REIT:
  - Property portfolio (value per property or segment)
  - Cap rate assumptions per property type
  - NOI (Net Operating Income) per property/segment
  - Development pipeline value
  - Mortgage/debt against properties

Bank:
  - Loan portfolio (book value, credit quality adjustments)
  - Securities portfolio (mark to market)
  - Deposits (funding value)
  - Regulatory capital ratios
  - Provision for loan losses

Holding Company:
  - Value of each subsidiary/investment
  - Public holdings at market value
  - Private holdings at estimated value
  - Holding company discount (typically 10-25%)

Resource Company:
  - Proven reserves (quantity)
  - Commodity price assumption
  - Extraction cost per unit
  - Reserve life
```

### 3.4 Key Outputs

```
Asset-by-asset value table:
  Asset | Book Value | Fair Value | Adjustment | Notes

Summary:
  Total Asset Fair Value
  Less: Total Liabilities (at fair value)
  Less: Preferred Equity (if any)
  = Net Asset Value
  ÷ Shares Outstanding
  = NAV per Share

Premium/Discount to NAV:
  Current Price vs NAV per share
  Historical P/NAV range (chart)
```

### 3.5 Sub-Tab Structure

```
NAV Model Sub-Tabs:
  Overview | Historical Data | Asset Analysis | NAV Calculation | Premium/Discount | Sensitivity | History
```

- **Asset Analysis:** Breakdown of assets by category with fair value estimates — unique to NAV
- **NAV Calculation:** Step-by-step NAV build from assets to per-share value
- **Premium/Discount:** Historical P/NAV chart, current positioning

### 3.6 Priority

Medium-Low. NAV is important for specific sectors (REITs, banks) but not
universally applicable. Should be built after LBO. The existing models
(especially Comps with P/B multiples) provide adequate coverage for these
sectors in the interim.

---

## Part 4: Architecture Validation

### 4.1 Confirming the Plugin Pattern Works

Every current model (DCF, DDM, Comps, Revenue-Based) already follows
the BaseValuationModel contract described in Part 1. The future models
(LBO, NAV) have been scoped to confirm they can also implement this
contract without requiring changes to the base interface.

Key validation points:
- ✅ All models produce an intrinsic value (per share)
- ✅ All models support scenarios (Bear/Base/Bull)
- ✅ All models have waterfall-style output (different building blocks)
- ✅ All models define sensitivity variables
- ✅ All models use the assumption engine for auto-generation
- ✅ All models support version history
- ✅ All models export to Excel/PDF
- ✅ Sub-tab structure varies per model (as designed in Phase 0D)

The only model that's structurally different is Comps (relative valuation
vs. intrinsic), but it still produces an implied value per share and
scenario ranges, so it fits the same output contract.

### 4.2 Model Interaction Matrix

How models relate to each other for cross-validation:

```
              DCF    DDM    Comps   RevBased   LBO    NAV
DCF            —     Cross  Cross   Cross      Floor   —
DDM          Cross    —     Cross    —          —      —
Comps        Cross  Cross    —      Cross       —     Cross
RevBased     Cross   —     Cross     —          —      —
LBO          Floor   —      —        —          —      —
NAV           —      —     Cross     —          —      —

Cross = Models can cross-check each other
Floor = LBO provides a "floor" valuation (what a buyer would pay)
— = Models don't meaningfully interact
```

---

*End of Phase 1G specification.*
