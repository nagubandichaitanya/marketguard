# MarketGuard

**Marketplace Seller Operations, Compliance & Payout Intelligence Platform**

MarketGuard is a data-driven marketplace operations and compliance platform built with Python, FastAPI, PostgreSQL, SQLAlchemy, and JavaScript.

It monitors seller operations, product listings, order fulfillment, disputes, commissions, and payouts. Its rule-based anomaly detection engine identifies operational and financial inconsistencies and presents actionable findings through an interactive dashboard.

## Project Status

The starter implementation is functional and includes:

- PostgreSQL database with 15 operational tables.
- Deterministic synthetic data generation.
- Data validation and integrity checks.
- Database loading with transaction and row-count verification.
- Five rule-based anomaly detection scenarios.
- REST API for anomaly scanning and summaries.
- Interactive web dashboard.
- Automated tests for anomaly detection and API health.

**Current starter dataset:** 11,678 operational records.

**Current dashboard result:** 7 detected anomalies, all classified as high severity and associated with suspended sellers having active listings.

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
git clone <YOUR_PUBLIC_GITHUB_REPOSITORY_URL>
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
DATA_SCALE=starter
```

**Security:** Never commit `.env` or expose database credentials publicly.

### 5. Create the PostgreSQL database

Create the database using PostgreSQL:

```powershell
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE marketguard_db;"
```

If the database already exists, do not execute this command again.

### 6. Initialize database tables

From the project root:

```powershell
python -c "from backend.app.database import Base, engine; import backend.app.models; Base.metadata.create_all(bind=engine); print('Database tables created successfully')"
```

### 7. Generate synthetic data

Generate the starter dataset with a fixed seed:

```powershell
python -m scripts.generate_data --scale starter --seed 20261022
```

The generator creates operational CSV files, separate ground-truth fixtures, and a generation manifest with reproducibility checksums.

### 8. Validate generated data

```powershell
python -m scripts.validate_data
```

The validation process checks data integrity, relationships, arithmetic rules, lifecycle constraints, and anomaly fixture coverage.

A warning about active listings belonging to suspended sellers is expected in the starter evaluation dataset.

### 9. Load data into PostgreSQL

```powershell
python -m scripts.load_data
```

The loader checks CSV schemas, converts data types, inserts records in dependency order, and verifies database row counts.

Do not rerun the loader against an already populated database without understanding the `--replace` option.

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

MarketGuard implements five rule-based anomaly scenarios.

| ID | Anomaly | Detection objective |
|---|---|---|
| ANOM-001 | Payout Before Delivery | Identify payouts made before the delivery hold period expires. |
| ANOM-002 | Duplicate Commission | Identify commission amounts exceeding the expected effective-dated commission. |
| ANOM-003 | Suspended Seller Active Listing | Identify active product listings belonging to suspended sellers. |
| ANOM-004 | Lost Dispute Not Deducted | Identify lost refund or chargeback disputes that are not reflected in payout deductions. |
| ANOM-005 | Payout Header Mismatch | Identify differences between payout header totals and calculated payout-line totals. |

The detector evaluates operational database records. Evaluation-only ground-truth fixtures are maintained separately and are not used as detector input.

## API Endpoints

### 1. Health Check

`GET /health`

Checks whether the application is running.

### 2. Run Anomaly Scan

`POST /api/v1/anomalies/scan`

Executes all implemented anomaly detection rules and returns:

- Total anomalies.
- Severity counts.
- Anomaly categories.
- Affected record identifiers.
- Expected and observed values.
- Recommended actions.
- Detection timestamps.

### 3. Anomaly Summary

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

Run the complete automated test suite:

```powershell
python -m pytest -v
```

The current test suite contains six passing tests:

- Payout-before-delivery detection.
- Duplicate-commission detection.
- Suspended-seller active-listing detection.
- Lost-dispute deduction detection.
- Payout-header mismatch detection.
- FastAPI health endpoint.

The anomaly tests use an isolated SQLite test database and do not modify the PostgreSQL operational dataset.

## Data Integrity and Reproducibility

The project follows these principles:

- Generate parent records before dependent records.
- Maintain deterministic identifiers and foreign-key relationships.
- Preserve lifecycle history through event records.
- Keep evaluation ground truth separate from operational input data.
- Validate primary keys, foreign keys, enums, timestamps, and financial calculations.
- Use deterministic seeds for repeatable synthetic datasets.
- Generate checksums for reproducibility verification.
- Avoid real customer personal information in synthetic data.

## Current Validation Results

- Operational tables: 15
- Operational database records: 11,678
- Ground-truth anomaly scenarios: 5
- Automated tests: 6 passed
- Current detected anomalies: 7
- Current detected anomaly category: Suspended seller active listing
- Validation status: PASS

These results describe the current starter dataset and implementation.

## Future Improvements

- Add more advanced anomaly detection and risk scoring.
- Introduce seller performance analytics.
- Add payout reconciliation workflows.
- Improve dashboard visualizations and drill-down reporting.
- Expand testing and support larger datasets.
- Add authentication and role-based access control.

## License

Add an appropriate license before distributing the project publicly.