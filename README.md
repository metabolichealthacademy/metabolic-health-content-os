# Metabolic Health Content OS

Private, evidence-oriented content operations foundation for Metabolic Health Academy.

## Task 1 foundation

- Python 3.12 package using a `src/` layout
- FastAPI application with versioned routes
- `GET /api/v1/health` health check
- Environment-based configuration with safe development defaults
- Pytest test suite with coverage enforcement
- Ruff linting and GitHub Actions continuous integration

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

Do not place credentials in `.env.example` or commit a local `.env` file. Production secrets must be configured in the deployment platform or GitHub Actions secrets.

## Run the API

```bash
uvicorn content_os.main:app --reload
```

Verify it in another terminal:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{"status":"ok","service":"Metabolic Health Content OS","version":"0.1.0","environment":"development"}
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs` outside production.

## Quality checks

```bash
ruff check .
pytest
```

The test suite requires at least 90% code coverage.

## Git workflow

1. Branch from `main` with `feature/<short-name>`, `fix/<short-name>`, or `docs/<short-name>`.
2. Keep commits focused and use an imperative summary, such as `Add API health endpoint`.
3. Run Ruff and pytest locally.
4. Push the branch and open a pull request into `main`.
5. Require the CI check and review before merge; never commit secrets or push directly to `main`.

## Current structure

```text
.
├── .github/workflows/ci.yml
├── src/content_os/
│   ├── api/health.py
│   ├── config.py
│   └── main.py
├── tests/
│   ├── test_config.py
│   └── test_health.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

This foundation contains no patient data, clinical decision logic, medical RAG, authentication, or production secrets.
