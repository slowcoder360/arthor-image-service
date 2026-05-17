# arthor-image-service

FastAPI service for Arthor image generation, asset packs, and inspector tooling.

## Local run

Create a virtual environment, install the package in editable mode with dev extras, then start uvicorn:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```

Slice-scoped tests live under `slices/<id>/tests/`; shared pytest hooks are in `tests/conftest.py`.
