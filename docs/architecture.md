# MarketGuard Architecture

## System boundary

MarketGuard ingests or generates marketplace operational records, evaluates seller and
financial rules, persists state transitions, and exposes operational metrics through an API
and dashboard.

## Planned layers

1. Synthetic data and ingestion
2. PostgreSQL persistence
3. Domain services (seller, fulfillment, disputes, commissions, payouts)
4. Validation and anomaly detection
5. FastAPI application layer
6. Operations dashboard

## Design constraints

- PostgreSQL is the system of record.
- Foreign keys enforce entity relationships.
- Lifecycle changes are append-only events where applicable.
- Ground truth is isolated from operational input features.
- Derived financial values are reproducible from source ledger components.
