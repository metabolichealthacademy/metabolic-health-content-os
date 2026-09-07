# Metabolic Health Content OS

Private, evidence-oriented content operations foundation for Metabolic Health Academy.

## Task 1 foundation

- Python 3.12 package using a `src/` layout
- FastAPI application with versioned routes
- `GET /api/v1/health` health check
- Environment-based configuration with safe development defaults
- Pytest test suite with coverage enforcement
- Ruff linting and GitHub Actions continuous integration
- Five-stage agent pipeline with a deterministic orchestrator
- Safety revision routing and mandatory human approval
- SQL persistence with optimistic locking and append-only application audit events

## V1 workflow architecture

The workflow runs in a fixed order:

1. Research intake
2. Evidence structure validation
3. Content drafting
4. Safety review
5. Production packaging
6. Human approval or rejection

The current agents are deterministic foundations. They do not retrieve live evidence, assess
scientific validity, call an AI model, or publish content.

Workflow state now persists in a SQL database. SQLite is the safe local default; PostgreSQL is
supported by installing `.[postgres]` and setting `DATABASE_URL`. Alembic owns production schema
migrations.

```bash
alembic upgrade head
```

The application exposes no audit-event update or delete operation. Human decisions record an
`actor_id`, time, transition, and reason when rejected. V1 must not store patient-identifiable
information. Retention and deletion policy enforcement will be added with authentication before
production use.

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

Workflow endpoints are available under `/api/v1/workflows`:

- `POST /api/v1/workflows`
- `GET /api/v1/workflows/{id}`
- `POST /api/v1/workflows/{id}/advance`
- `POST /api/v1/workflows/{id}/approve`
- `POST /api/v1/workflows/{id}/reject`

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
│   ├── agents/
│   ├── api/
│   ├── config.py
│   ├── models/
│   ├── orchestration/
│   └── main.py
├── tests/
│   ├── test_config.py
│   └── test_health.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

This foundation contains no patient data, clinical decision logic, medical RAG, authentication,
production secrets, external model calls, or publishing integration. Database credentials belong
only in environment configuration and must never be committed.
