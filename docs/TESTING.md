# Testing Guide

## Unit Tests

```bash
pytest backend/tests/
```

## Integration Tests

Requires backend running on localhost:8000.

```bash
pytest backend/tests/integration/ -v
```

To run only integration-marked tests:

```bash
pytest backend/tests/integration/ -v -m integration
```

## Smoke Test

Standalone script -- requires backend running.

```bash
python scripts/smoke_test.py
```

## Prerequisites

- Backend: `cd backend && py -3.12 -m uvicorn main:app --port 8000`
- Some tests need data (run scanner or load a ticker first)
