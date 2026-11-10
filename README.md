# MarketGuard

Marketplace Seller Operations, Compliance & Payout Intelligence Platform.

MarketGuard is being developed as a hackathon project to monitor seller service levels,
order fulfillment, disputes, commissions, payout eligibility, and financial anomalies.

## Current status

This repository is the **initial development scaffold**. It includes the project structure,
configuration templates, a FastAPI health endpoint, initial documentation, and test
placeholders. Business engines, full database models, synthetic data generation, dashboard,
and anomaly workflows will be implemented and tested incrementally.

## Technology

- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- psycopg 3
- Pandas / NumPy
- Pytest
- HTML, CSS, JavaScript
- Cursor IDE

## Project structure

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
├── data/
│   ├── generated/
│   ├── ground_truth/
│   └── manifests/
├── docs/
├── frontend/
├── scripts/
├── .env.example
├── .gitignore
└── requirements.txt
```

## Initial setup (Windows PowerShell)

1. Open this folder in Cursor.
2. Open Cursor's integrated terminal: **Terminal → New Terminal**.
3. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and update the PostgreSQL credentials:

   ```powershell
   Copy-Item .env.example .env
   ```

6. Start the API from the repository root:

   ```powershell
   uvicorn backend.app.main:app --reload
   ```

7. Open:
   - API health: http://127.0.0.1:8000/health
   - Swagger UI: http://127.0.0.1:8000/docs

The database connection is not activated until we configure PostgreSQL in the next
development checkpoint.

## Synthetic data target

Full-scale configuration will target:

- 2,000 sellers
- 20,000 product listings
- 100,000 orders
- 10,000 disputes

The generator will use seed `20261022`, support starter/full scales with the same
generation logic, export ground truth separately, and produce reproducibility checksums.

## Required anomaly scenarios

1. Payout before delivery / hold release
2. Commission applied twice
3. Suspended seller continues listing
4. Dispute not deducted
5. Payout total does not equal payout lines

## Development principles

- Generate valid parent/master records before dependent records.
- Use immutable, deterministic IDs and foreign keys.
- Preserve lifecycle history as append-only events.
- Calculate derived values from source records and documented rules.
- Keep ground truth separate from input data.
- Validate primary keys, foreign keys, enums, date ordering, arithmetic, lifecycle
  transitions, duplicate operations, and reproducibility.
- Never use real customer personal data in the synthetic dataset.

## GitHub

Create a **public** GitHub repository named `marketguard` when we reach the Git checkpoint.
Do not commit `.env`, credentials, virtual environments, or generated large datasets.
