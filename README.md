# MarketGuard

**Marketplace Seller Operations, Compliance & Payout Intelligence Platform**

MarketGuard is a data-driven marketplace operations and compliance platform built with Python, FastAPI, PostgreSQL, SQLAlchemy, and JavaScript.

It monitors seller operations, product listings, order fulfillment, disputes, commissions, and payouts. Its rule-based anomaly detection engine identifies operational and financial inconsistencies and presents actionable findings through an interactive dashboard.

## Project Status

MarketGuard has been implemented and tested against a full-scale synthetic marketplace dataset.

The current implementation includes:

- PostgreSQL database with 15 operational tables.
- Deterministic synthetic data generation with starter and full scales.
- Data validation and integrity checks.
- Optimized database loading with transactional replacement and row-count verification.
- Five rule-based anomaly detection scenarios.
- REST API for anomaly scanning and summaries.
- Interactive web dashboard.
- Separate evaluation ground truth and record-level anomaly fixtures.
- Automated tests covering all five anomaly detection rules and API health.
- Reproducibility manifests and SHA-256 checksums.

**Current full-scale dataset:** 1,941,502 operational records across 15 tables.

**Current dashboard result:** 301 detected anomalies, all classified as HIGH severity and associated with suspended sellers having active listings.

The other four anomaly rules are covered by isolated automated tests but do not currently produce findings in the full-scale operational dataset.

**Current data validation:** PASS — zero errors and one expected warning for the 301 intentionally seeded suspended-seller active-listing anomalies.

**Automated tests:** 6 passed.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Database driver | psycopg 3 |
| Data processing | Pandas, NumPy |
| Configuration | Pydantic Settings, python-dotenv |
| Frontend | HTML, CSS, JavaScript |
| API documentation | Swagger UI / OpenAPI |
| Testing | Pytest |
| Development environment | Cursor, Git, GitHub |

## Project Structure

```text
marketguard/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   └── validators/
│   └── tests/
├── database/
│   ├── migrations/
│   ├── schema.sql
│   └── seed.sql
├── data/
│   ├── generated/
│   ├── ground_truth/
│   └── manifests/
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   └── business_rules.md
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
├── reports/
├── scripts/
│   ├── generate_data.py
│   ├── init_db.py
│   ├── load_data.py
│   ├── reproducibility_check.py
│   └── validate_data.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.11 or later
- PostgreSQL
- Git
- Windows PowerShell or a compatible terminal

## Installation and Setup

### 1. Clone the repository

```powershell
git clone https://github.com/nagubandichaitanya/marketguard.git
cd marketguard
```

### 2. Create a virtual environment

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your local PostgreSQL credentials:

```env
APP_NAME=MarketGuard
APP_ENV=development
DEBUG=true
API_HOST=127.0.0.1
API_PORT=8000

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=marketguard_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOUR_POSTGRES_PASSWORD

DATA_SEED=20261022
DATA_SCALE=full
```

**Security:** Never commit `.env` or expose database credentials publicly.

### 5. Create the PostgreSQL database

```powershell
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE marketguard_db;"
```

If the database already exists, do not execute this command again.

### 6. Initialize database tables

Run from the project root:

```powershell
python -c "from backend.app.database import Base, engine; import backend.app.models; Base.metadata.create_all(bind=engine); print('Database tables created successfully')"
```

### 7. Generate synthetic data

**Starter dataset:**

```powershell
python -m scripts.generate_data --scale starter --seed 20261022
```

**Full-scale challenge dataset:**

```powershell
python -m scripts.generate_data --scale full --seed 20261022
```

The full-scale configuration generates:

| Entity | Records |
|---|---:|
| Sellers | 2,000 |
| Product listings | 20,000 |
| Orders | 100,000 |
| Order lines | 200,122 |
| Order sellers | 200,059 |
| Fulfillments | 200,122 |
| Customer reviews | 57,034 |
| Disputes | 11,983 |
| Commission rules | 2,000 |
| Payouts | 2,000 |
| Payout lines | 155,407 |
| Seller status history | 841 |
| Fulfillment events | 964,401 |
| Dispute events | 21,533 |
| Payout events | 4,000 |
| **Total operational records** | **1,941,502** |

The generator also creates five ground-truth labels and five record-level evaluation fixtures. These are maintained separately from operational data.

Generated data includes operational CSV files, evaluation fixtures, a generation manifest, and SHA-256 checksums.

### 8. Validate generated data

```powershell
python -m scripts.validate_data
```

The validation process checks:

- Record counts and primary-key uniqueness.
- Foreign-key relationships.
- Data integrity and arithmetic rules.
- Lifecycle constraints and timestamps.
- Ground-truth and evaluation fixture coverage.

A warning about active listings belonging to suspended sellers is expected because these anomalies are intentionally seeded for evaluation.

### 9. Load data into PostgreSQL

For an empty database:

```powershell
python -m scripts.load_data
```

To replace existing operational records with the newly generated dataset:

```powershell
python -m scripts.load_data --replace
```

The loader checks CSV schemas, converts data types, inserts records in dependency order, and verifies database row counts.

Database replacement uses a transaction, so a failed load does not leave a partially replaced dataset.

**Important:** The loader does not load evaluation-only ground-truth fixtures into operational tables. Use `--replace` only when you intentionally want to replace the existing operational dataset.

## Running the Application

Start the FastAPI application:

```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open these URLs:

| Resource | URL |
|---|---|
| MarketGuard Dashboard | http://127.0.0.1:8000/ |
| API Health | http://127.0.0.1:8000/health |
| Swagger UI | http://127.0.0.1:8000/docs |
| OpenAPI Schema | http://127.0.0.1:8000/openapi.json |

## Anomaly Detection Engine

MarketGuard implements five rule-based anomaly detection scenarios.

| ID | Anomaly | Detection objective |
|---|---|---|
| ANOM-001 | Payout Before Delivery | Identify payouts made before the delivery hold period expires. |
| ANOM-002 | Duplicate Commission | Identify commission amounts exceeding the expected effective-dated commission. |
| ANOM-003 | Suspended Seller Active Listing | Identify active product listings belonging to suspended sellers. |
| ANOM-004 | Lost Dispute Not Deducted | Identify lost refund or chargeback disputes that are not reflected in payout deductions. |
| ANOM-005 | Payout Header Mismatch | Identify differences between payout header totals and calculated payout-line totals. |

The detector evaluates operational database records. Evaluation-only ground-truth fixtures are maintained separately and are not used as detector input.

## API Endpoints

### Health Check

`GET /health`

Checks whether the application is running.

### Run Anomaly Scan

`POST /api/v1/anomalies/scan`

Executes the implemented anomaly detection rules and returns:

- Total anomalies.
- Severity counts.
- Anomaly categories.
- Affected record identifiers.
- Expected and observed values.
- Recommended actions.
- Detection timestamps.

### Anomaly Summary

`GET /api/v1/anomalies/summary`

Returns aggregate anomaly counts by severity and type.

## Dashboard Features

- Live API connection status.
- Anomaly scanning through the dashboard.
- Total anomaly and severity summaries.
- Anomaly category distribution.
- Search by anomaly details and record identifiers.
- Severity filtering.
- Detection recommendations and record-level information.

## Testing

Run the automated test suite:

```powershell
python -m pytest -v
```

The current test suite contains six passing tests:

1. Payout-before-delivery detection.
2. Duplicate-commission detection.
3. Suspended-seller active-listing detection.
4. Lost-dispute deduction detection.
5. Payout-header mismatch detection.
6. FastAPI health endpoint.

The anomaly tests use an isolated SQLite test database and do not modify the PostgreSQL operational dataset.

**Latest test result:** 6 passed.

## Data Integrity and Reproducibility

The project follows these principles:

- Generate parent records before dependent records.
- Maintain deterministic identifiers and foreign-key relationships.
- Preserve lifecycle history through event records.
- Keep evaluation ground truth separate from operational input data.
- Validate primary keys, foreign keys, enums, timestamps, and financial calculations.
- Use deterministic seeds for repeatable synthetic datasets.
- Generate SHA-256 checksums for reproducibility verification.
- Index frequently queried foreign-key relationships.
- Use transactional database loading.
- Avoid real customer personal information in synthetic data.

## Current Validation Results

The following results were verified against the full-scale PostgreSQL dataset.

| Metric | Verified result |
|---|---:|
| Operational database tables | 15 |
| Operational database records | 1,941,502 |
| Ground-truth labels | 5 |
| Record-level evaluation fixtures | 5 |
| Data validation status | PASS |
| Validation errors | 0 |
| Expected validation warnings | 1 |
| Automated tests | 6 passed |
| Detected anomalies | 301 |
| HIGH-severity anomalies | 301 |
| Detected anomaly category | Suspended seller active listing |

The single validation warning is expected: 301 active product listings belong to suspended sellers. These are intentionally seeded evaluation anomalies.

All five anomaly detection rules passed their isolated automated tests. Only the suspended-seller active-listing rule currently produces findings in the full-scale operational dataset.

## Documentation

Additional project documentation:

- `docs/architecture.md` — System architecture, components, and data flow.
- `docs/data_dictionary.md` — Database entities, fields, constraints, and relationships.
- `docs/business_rules.md` — Five anomaly detection rules and financial policies.

## Future Improvements

- Add more advanced anomaly detection and risk scoring.
- Introduce seller performance analytics.
- Add payout reconciliation workflows.
- Improve dashboard visualizations and drill-down reporting.
- Expand testing and support larger datasets.
- Add authentication and role-based access control.

## License

Add an appropriate license before distributing the project publicly.