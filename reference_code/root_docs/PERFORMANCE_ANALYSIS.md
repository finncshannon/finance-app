# Performance Analysis: Refresh Bottleneck Investigation

## RESOLVED - Bottleneck Found and Fixed

### Root Cause: Inefficient `clear_other_models` Function

The `_clear_data_values()` function was making individual COM calls for every cell in the used range:
- Each `.cells(row, col)` = 1 COM call
- Each `.formula` read = 1 COM call
- Each `.value` read = 1 COM call
- Each `.value = None` write = 1 COM call

For a sheet with 50 rows × 30 columns = 1,500 cells × 4 calls = **6,000 COM calls per sheet**.
With 3 sheets to clear = **18,000+ COM calls** at ~0.3ms each = **5-8 seconds wasted**.

### The Fix (Applied)

Optimized `_clear_data_values()` to use batch operations:
- 2 COM calls to read all values and formulas (batch read)
- Process in Python memory
- Only write to cells that need clearing

### Performance Improvement

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| JNJ clear (129 cells) | 7.64s | 1.11s | **6.9x faster** |
| AAPL clear (35 cells) | 3.01s | 0.43s | **7.0x faster** |
| MSFT clear (0 cells) | 2.75s | 0.11s | **25x faster** |
| **Average total refresh** | **6.69s** | **2.46s** | **2.7x faster** |

---

## Current Timing Breakdown (After Fix)

| Component | Time |
|-----------|------|
| Yahoo Finance API extraction | 0.4-0.85s |
| Model auto-detection | 0.001s |
| Excel writes (named ranges) | 0.6-1.5s |
| Clear other models | 0.1-1.1s |
| **Python Total** | **~2.5s** |

---

## Previous Hypothesis: Excel Recalculation

### Evidence from VBA Code (`VBA Module.txt`)

```vba
' Line 108: Calculation disabled at start
Application.Calculation = xlCalculationManual

' ... Python work happens here (~1.8s) ...

' Line 184: Calculation re-enabled - TRIGGERS FULL RECALC
Application.Calculation = xlCalculationAutomatic
```

### Why Recalculation Takes So Long

The MasterValuation workbook has:
- **901 named ranges** across all sheets
- **34 worksheets** (DCF, DDM, RevBased, Comps, Dashboards, etc.)
- **~26,000 cells** scanned
- **Complex cross-sheet formula dependencies**
- **8 valuation scenarios** (each with full formula chains)
- **Volatile functions** (NOW(), INDIRECT(), OFFSET())

When `xlCalculationAutomatic` is set, Excel recalculates the ENTIRE workbook, including:
1. All 8 scenarios in each model
2. Dashboard summary formulas
3. Cross-sheet references
4. Conditional formatting dependencies
5. Chart data sources

---

## Optimization Recommendations

### Option 1: Targeted Recalculation (Best ROI)
Instead of triggering full workbook recalc, calculate only affected sheets:

```vba
' Instead of:
Application.Calculation = xlCalculationAutomatic

' Use:
Application.Calculation = xlCalculationManual
Worksheets("Home").Calculate
Worksheets(selectedModel & "_Yahoo_Data").Calculate
Worksheets(selectedModel & "_Dashboard").Calculate
' Only recalc what changed
```

**Expected improvement**: 50-70% reduction (from 58s to ~15-20s)

### Option 2: Batch Cell Writes with Delayed Recalc
Already partially implemented with `excel_writer_batch.py`:
- Collects all writes in memory
- Flushes in single operation
- Reduces recalc triggers during write phase

**Status**: Implemented but needs workbook-specific recalc optimization

### Option 3: Formula Audit
Review formulas for performance killers:
- `INDIRECT()` - forces recalculation on every change
- `OFFSET()` - volatile, recalculates constantly
- `NOW()`, `TODAY()` - forces recalc on any change
- Array formulas spanning large ranges
- Circular references (even if intentional)

**Action**: Run `benchmark_recalc.py` with correct workbook open to identify specific formula overhead

### Option 4: Calculation Chain Optimization
- Move static data to values-only sheets
- Use helper columns instead of complex nested formulas
- Pre-calculate constants

### Option 5: Screen Updating Already Optimized
VBA already sets:
```vba
Application.ScreenUpdating = False  ' Line 107
```
This prevents visual updates but doesn't affect calculation.

---

## Testing Instructions

To measure actual recalculation time on MasterValuation:

1. Close other Excel workbooks
2. Open `MasterValuation_SAFE_FIXED.xlsm` only
3. Run: `python benchmark_recalc.py`
4. Note the "RECALCULATION TIME" value

---

## Quick Win: VBA Modification

Modify the RefreshData macro to use targeted recalculation:

```vba
' Replace line 184:
' Application.Calculation = xlCalculationAutomatic

' With:
Application.Calculation = xlCalculationManual

' Calculate only the sheets that matter
On Error Resume Next
Worksheets("Home").Calculate
Worksheets(selectedModel & "_Yahoo_Data").Calculate
Worksheets(selectedModel & "_Dashboard").Calculate
On Error GoTo ErrorHandler

' Keep manual mode until user navigates
' Or set a timer to restore automatic later
```

This should reduce the 60-second refresh to under 10 seconds for most operations.

---

## Files Related to This Investigation

- `benchmark_recalc.py` - Measures recalculation time
- `benchmark_refresh.py` - Full pipeline timing
- `benchmark_api_only.py` - API timing isolation
- `benchmark_writes.py` - Excel write timing
- `VBA Module.txt` - VBA source showing calculation mode handling
