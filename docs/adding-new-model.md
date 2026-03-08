# Adding a New Valuation Model

Checklist for adding a new valuation engine to the Finance App.

## 1. Create the Engine Class

Create `backend/engines/your_engine.py`:

```python
from engines.base_model import BaseValuationModel
from services.assumption_engine.models import AssumptionSet

class YourEngine(BaseValuationModel):
    model_type = "your_type"       # unique key, snake_case
    display_name = "Your Model"    # display label

    @staticmethod
    def run(assumption_set, data, current_price, **kwargs):
        # Your valuation logic here
        return YourResult(...)

    @staticmethod
    def get_required_assumptions():
        return ["model_assumptions.your_type.key1", ...]

    @staticmethod
    def validate_assumptions(assumption_set):
        errors = []
        # Validate required fields exist
        return errors
```

## 2. Define Pydantic Output Models

Add result models to `backend/engines/models.py`:

```python
class YourResult(BaseModel):
    ticker: str
    current_price: float
    model_type: str = "your_type"
    # ... your output fields
```

## 3. Add Assumption Types

In `backend/services/assumption_engine/models.py`:

1. Create a `YourAssumptions` Pydantic model
2. Add it to `ModelAssumptions.your_type: YourAssumptions | None = None`
3. Add a mapper in `model_mappers.py` to populate from financial data

## 4. Register the Engine

In `backend/engines/__init__.py`:

```python
from .your_engine import YourEngine
engine_registry.register(YourEngine)
```

## 5. Add Detection Scoring

In `backend/services/model_detection_service.py`, add scoring logic for your model type in the `_compute_scores()` method. Return a 0-100 score based on company characteristics.

## 6. Add Router Endpoints

In `backend/routers/models_router.py`:

1. Add your engine to `ENGINE_MAP`
2. Add a `POST /{ticker}/run/your_type` endpoint (follow existing pattern)

## 7. Create Frontend View

1. Create `frontend/src/pages/ModelBuilder/Models/YourView.tsx` + `.module.css`
2. Add TypeScript types to `frontend/src/types/models.ts`
3. Add the case to `ModelTab.tsx` switch statement

## 8. Add Sensitivity Parameters (Optional)

If your model should support sensitivity analysis:

1. Add parameter definitions in `backend/services/sensitivity/parameter_defs.py`
2. Ensure your engine works with the slider/tornado/MC override system

## File Reference

| Purpose | Location |
|---------|----------|
| Engine base class | `backend/engines/base_model.py` |
| Engine registry | `backend/engines/registry.py` |
| Output models | `backend/engines/models.py` |
| Assumption models | `backend/services/assumption_engine/models.py` |
| Model detection | `backend/services/model_detection_service.py` |
| API router | `backend/routers/models_router.py` |
| Frontend types | `frontend/src/types/models.ts` |
| Frontend views | `frontend/src/pages/ModelBuilder/Models/` |
