
import argparse
import csv
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import DateTime, Integer, Numeric, JSON, String, Text, func, select

from backend.app.database import Base, engine
from backend.app import models


DATA_DIR = Path("data/generated")

# Parent tables must be loaded before dependent tables.
LOAD_ORDER = [
    "sellers",
    "product_listings",
    "orders",
    "order_lines",
    "order_sellers",
    "fulfillments",
    "customer_reviews",
    "disputes",
    "commission_rules",
    "payouts",
    "payout_lines",
    "seller_status_history",
    "fulfillment_events",
    "dispute_events",
    "payout_events",
]


def convert_value(value, column):
    """Convert CSV strings into Python values matching SQLAlchemy types."""

    if value is None or value.strip() == "":
        if not column.nullable:
            raise ValueError(
                f"Required column '{column.name}' is empty."
            )
        return None

    value = value.strip()
    column_type = column.type

    if isinstance(column_type, DateTime):
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    if isinstance(column_type, Numeric):
        return Decimal(value)

    if isinstance(column_type, Integer):
        return int(value)

    if isinstance(column_type, JSON):
        return json.loads(value)

    if isinstance(column_type, (String, Text)):
        return value

    return value


def read_csv_records(table_name, table):
    """Read and validate a CSV file against its database table."""

    csv_path = DATA_DIR / f"{table_name}.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Missing CSV file: {csv_path}"
        )

    records = []

    with csv_path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:

        reader = csv.DictReader(file)

        headers = [
            header.strip()
            for header in (reader.fieldnames or [])
        ]

        expected_columns = set(table.columns.keys())

        if set(headers) != expected_columns:
            raise ValueError(
                f"Column mismatch in {csv_path.name}\n"
                f"Expected: {sorted(expected_columns)}\n"
                f"Found: {sorted(headers)}"
            )

        for row_number, row in enumerate(reader, start=2):
            normalized_row = {
                (key or "").strip(): value
                for key, value in row.items()
            }

            record = {}

            for column in table.columns:
                try:
                    record[column.name] = convert_value(
                        normalized_row.get(column.name),
                        column
                    )
                except Exception as exc:
                    raise ValueError(
                        f"{csv_path.name}, row {row_number}, "
                        f"column {column.name}: {exc}"
                    ) from exc

            records.append(record)

    return records


def load_data(replace=False):
    print("\n======================================")
    print("       MARKETGUARD DATA LOADER")
    print("======================================")

    tables = Base.metadata.tables

    if set(LOAD_ORDER) != set(tables.keys()):
        raise ValueError(
            "LOAD_ORDER does not match registered database tables."
        )

    # Read and validate all CSVs before modifying the database.
    print("\nReading and validating CSV files...")

    all_records = {}

    for table_name in LOAD_ORDER:
        table = tables[table_name]
        records = read_csv_records(table_name, table)
        all_records[table_name] = records

        print(f"  {table_name}: {len(records)} records")

    # Check whether the database already contains records.
    with engine.connect() as connection:
        existing_counts = {}

        for table_name in LOAD_ORDER:
            table = tables[table_name]

            count = connection.execute(
                select(func.count()).select_from(table)
            ).scalar_one()

            existing_counts[table_name] = count

    populated_tables = {
        name: count
        for name, count in existing_counts.items()
        if count > 0
    }

    if populated_tables and not replace:
        raise RuntimeError(
            "Database already contains records.\n"
            "Use --replace only if you intend to replace "
            "the existing generated dataset."
        )

    print("\nStarting database transaction...")

    # All changes commit together or roll back together.
    with engine.begin() as connection:

        if replace:
            print("Removing existing records...")

            table_names = ", ".join(
                f'"{tables[name].name}"'
                for name in LOAD_ORDER
            )

            connection.exec_driver_sql(
                f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"
            )

            print("Existing records removed successfully.")

        print("\nInserting records...")

        for table_name in LOAD_ORDER:
            table = tables[table_name]
            records = all_records[table_name]

            # Insert in batches to keep memory usage controlled.
            for start in range(0, len(records), 1000):
                batch = records[start:start + 1000]

                if batch:
                    connection.execute(
                        table.insert(),
                        batch
                    )

            print(
                f"  Loaded {table_name}: {len(records)} records"
            )

        print("\nVerifying database row counts...")

        for table_name in LOAD_ORDER:
            table = tables[table_name]

            actual_count = connection.execute(
                select(func.count()).select_from(table)
            ).scalar_one()

            expected_count = len(all_records[table_name])

            if actual_count != expected_count:
                raise RuntimeError(
                    f"Row count mismatch for {table_name}: "
                    f"expected {expected_count}, "
                    f"found {actual_count}"
                )

            print(
                f"  PASS {table_name}: {actual_count}"
            )

    print("\n======================================")
    print("DATABASE LOADING COMPLETED")
    print("All row counts verified successfully.")
    print("Ground-truth fixtures were not loaded.")
    print("======================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load MarketGuard generated CSV data into PostgreSQL."
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing records in the operational tables."
    )

    args = parser.parse_args()

    load_data(replace=args.replace)
