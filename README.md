# 📚 Bookstore API — Python API Testing Framework

[![CI](https://github.com/Djones-qa/api-test-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/Djones-qa/api-test-framework/actions/workflows/ci.yml)
[![Nightly Performance](https://github.com/Djones-qa/api-test-framework/actions/workflows/nightly.yml/badge.svg)](https://github.com/Djones-qa/api-test-framework/actions/workflows/nightly.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![pytest](https://img.shields.io/badge/tested%20with-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A580%25-brightgreen)](https://github.com/Djones-qa/api-test-framework/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/badge/linter-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

A production-grade API testing framework built with **Python + FastAPI**, demonstrating real-world testing patterns across four distinct test categories. Designed as a portfolio project to showcase API design, test engineering, and CI/CD pipeline skills.

---

## 🗂 Project Structure

```
api-test-framework/
├── app/                        # FastAPI application
│   ├── main.py                 # App entry point, health endpoint
│   ├── config.py               # Pydantic settings (env-driven)
│   ├── models.py               # SQLAlchemy ORM models (User, Book)
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── auth.py                 # JWT auth, bcrypt hashing, OAuth2
│   ├── database.py             # SQLAlchemy engine + session factory
│   └── routers/
│       ├── auth.py             # /auth/register, /auth/token, /auth/me
│       └── books.py            # /books CRUD with filtering + pagination
│
├── tests/
│   ├── conftest.py             # Shared fixtures (DB, client, users, books)
│   ├── contract/               # JSON Schema contract tests
│   ├── integration/            # Full request/response integration tests
│   ├── data_driven/            # Parametrized tests + JSON datasets
│   │   └── datasets/           # valid_books.json, invalid_books.json, users.json
│   └── performance/            # p95 response time threshold tests
│
├── .github/workflows/
│   ├── ci.yml                  # Lint → Test matrix → Docker → Gate
│   └── nightly.yml             # Scheduled performance regression check
│
├── Dockerfile                  # Production image (non-root, python:3.12-slim)
├── Dockerfile.test             # Test runner image
├── docker-compose.yml          # API + test services with healthcheck
├── Makefile                    # Developer convenience targets
├── pyproject.toml              # pytest, coverage, ruff, mypy config
├── requirements.txt            # Production dependencies
└── requirements-dev.txt        # Test + lint dependencies
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or 3.12
- `pip`
- Docker (optional, for containerised runs)

### Local setup

```bash
# Clone the repo
git clone https://github.com/Djones-qa/api-test-framework.git
cd api-test-framework

# Install all dependencies and copy the env file
make dev

# Start the API (hot-reload)
make run
```

The API is now live at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

## 🧪 Running the Tests

### By test category

```bash
make test-contract      # JSON Schema contract tests
make test-integration   # Full CRUD + auth integration tests
make test-data          # Parametrized data-driven tests
make test-perf          # p95 response time threshold tests
```

### All tests (excluding performance)

```bash
make test
```

### All tests including performance

```bash
make test-all
```

### With coverage report

```bash
make coverage
# HTML report written to reports/htmlcov/index.html
```

### Full HTML test report

```bash
make report
# Report written to reports/test_report.html
```

---

## 🏗 API Overview

| Method   | Endpoint            | Auth required | Description                        |
|----------|---------------------|---------------|------------------------------------|
| `GET`    | `/health`           | ✗             | Health check (status + DB ping)    |
| `POST`   | `/auth/register`    | ✗             | Register a new user                |
| `POST`   | `/auth/token`       | ✗             | Obtain a JWT access token          |
| `GET`    | `/auth/me`          | ✓             | Return the current user            |
| `GET`    | `/books`            | ✗             | List books (filter + paginate)     |
| `POST`   | `/books`            | ✓             | Create a book                      |
| `GET`    | `/books/{id}`       | ✗             | Get a single book                  |
| `PATCH`  | `/books/{id}`       | ✓             | Partially update a book            |
| `DELETE` | `/books/{id}`       | ✓             | Delete a book                      |

Query parameters for `GET /books`: `page`, `page_size`, `genre`, `author`, `in_stock`

---

## 🔬 Test Strategy

### Contract Tests (`tests/contract/`)

Validate that every API response conforms to a consumer-defined JSON Schema. If a field is renamed, removed, or its type changes, these tests catch it immediately — acting as a safety net between producer and consumer.

```python
BOOK_SCHEMA = {
    "type": "object",
    "required": ["id", "title", "author", "isbn", "price", "in_stock", "created_at"],
    ...
    "additionalProperties": False,   # no surprise fields
}
```

### Integration Tests (`tests/integration/`)

Exercise the full HTTP request → router → DB → response cycle using FastAPI's `TestClient` backed by an in-memory SQLite database. Each test runs inside a transaction that is rolled back on teardown — no state leaks between tests.

Covers: CRUD operations, auth guards, duplicate detection, pagination, filtering, and error responses.

### Data-Driven Tests (`tests/data_driven/`)

Use `pytest.mark.parametrize` with external JSON datasets to run the same assertion logic across many input variations without duplicating test code.

```
datasets/
├── valid_books.json      # Books that must create successfully (201)
├── invalid_books.json    # Books that must be rejected (400 / 422)
└── users.json            # User registrations with expected status codes
```

Also includes inline parametrized cases for price boundaries, pagination limits, and genre filtering.

### Performance Tests (`tests/performance/`)

Assert that individual endpoints respond within defined p95 thresholds. Not a load test — these catch regressions where a code change accidentally makes an endpoint significantly slower.

| Threshold     | Value  | Used for                          |
|---------------|--------|-----------------------------------|
| `FAST`        | 0.5 s  | Simple reads (GET /books, /health)|
| `MEDIUM`      | 1.0 s  | DB writes (POST /books)           |
| `SLOW`        | 2.0 s  | bcrypt operations (POST /token)   |

---

## ⚙️ CI/CD Pipeline

### `ci.yml` — runs on every push to `main`/`develop` and on PRs to `main`

```
lint ──────────────────────────────────────────────────────┐
  ruff check + ruff format --check + mypy                  │
                                                           ▼
test (matrix: Python 3.11, 3.12) ──────────────────► all-checks gate
  contract → integration → data-driven → performance       ▲
  coverage report (3.12 only, ≥80% enforced)               │
  HTML test report + artifact upload                        │
                                                           │
docker ────────────────────────────────────────────────────┘
  docker build + smoke test (curl /health)
```

All three jobs must pass for the `all-checks` gate to succeed. PRs are blocked until the gate is green.

### `nightly.yml` — runs at 02:00 UTC daily (+ manual trigger)

Runs the performance test suite with verbose output and uploads a report with 90-day retention. Catches performance regressions that only appear over time.

---

## 🐳 Docker

```bash
# Start the API in Docker
make docker-up

# Run the full test suite inside Docker
make docker-test

# Stop all services
make docker-down
```

The `test` service in `docker-compose.yml` waits for the `api` service to pass its healthcheck before running, ensuring tests never hit a cold container.

---

## 🛠 Developer Targets

```bash
make help           # List all available targets
make lint           # ruff check
make format         # ruff format (auto-fix)
make typecheck      # mypy
make clean          # Remove .pyc, __pycache__, .db files, reports
```

---

## 🔧 Configuration

All settings are driven by environment variables (see `.env.example`):

| Variable                      | Default                          | Description                  |
|-------------------------------|----------------------------------|------------------------------|
| `DATABASE_URL`                | `sqlite:///./bookstore.db`       | SQLAlchemy connection string |
| `SECRET_KEY`                  | `super-secret-key-change-in-production` | JWT signing key       |
| `ALGORITHM`                   | `HS256`                          | JWT algorithm                |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                             | Token lifetime               |
| `DEBUG`                       | `false`                          | Enable debug mode            |

---

## 📦 Dependencies

**Production** (`requirements.txt`)

| Package              | Version  | Purpose                        |
|----------------------|----------|--------------------------------|
| `fastapi`            | 0.115.5  | Web framework                  |
| `uvicorn[standard]`  | 0.32.1   | ASGI server                    |
| `sqlalchemy`         | 2.0.36   | ORM + query builder            |
| `pydantic`           | 2.10.3   | Data validation + settings     |
| `python-jose`        | 3.3.0    | JWT encoding/decoding          |
| `passlib[bcrypt]`    | 1.7.4    | Password hashing               |
| `python-multipart`   | 0.0.18   | Form data parsing (OAuth2)     |

**Dev / Test** (`requirements-dev.txt`)

| Package        | Version | Purpose                          |
|----------------|---------|----------------------------------|
| `pytest`       | 8.3.4   | Test runner                      |
| `pytest-cov`   | 6.0.0   | Coverage measurement             |
| `pytest-html`  | 4.1.1   | HTML test reports                |
| `httpx`        | 0.28.1  | Async HTTP client (TestClient)   |
| `jsonschema`   | 4.23.0  | Contract test validation         |
| `ruff`         | 0.8.4   | Linter + formatter               |
| `mypy`         | 1.13.0  | Static type checker              |

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
