
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"
REPORT_DIR = BASE_DIR / "reports"
REPORT_PATH = REPORT_DIR / "validation_report.json"

REFERENCE_TIME = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
CENT = Decimal("0.01")

EXPECTED_COLUMNS = {
    "sellers": [
        "seller_id", "seller_name", "email", "phone", "city",
        "status", "created_at",
    ],
    "product_listings": [
        "listing_id", "seller_id", "product_name", "category",
        "price", "stock_quantity", "status", "created_at",
    ],
    "orders": [
        "order_id", "customer_id", "order_date", "total_amount",
        "status", "created_at",
    ],
    "order_lines": [
        "order_line_id", "order_id", "listing_id", "seller_id",
        "quantity", "unit_price", "line_total",
    ],
    "order_sellers": ["order_seller_id", "order_id", "seller_id"],
    "fulfillments": [
        "fulfillment_id", "order_line_id", "seller_id", "carrier",
        "tracking_number", "status", "shipped_at",
        "expected_delivery_at", "delivered_at",
    ],
    "customer_reviews": [
        "review_id", "order_line_id", "customer_id", "rating",
        "review_text", "created_at",
    ],
    "disputes": [
        "dispute_id", "order_line_id", "seller_id", "dispute_type",
        "amount", "status", "opened_at", "resolved_at",
    ],
    "commission_rules": [
        "commission_rule_id", "seller_id", "commission_percentage",
        "effective_from", "effective_to",
    ],
    "payouts": [
        "payout_id", "seller_id", "payout_date", "total_amount", "status",
    ],
    "payout_lines": [
        "payout_line_id", "payout_id", "order_line_id", "gross_amount",
        "commission_amount", "refund_amount", "chargeback_amount",
        "reserve_amount", "net_amount",
    ],
    "seller_status_history": [
        "event_id", "seller_id", "old_status", "new_status",
        "reason", "event_time",
    ],
    "fulfillment_events": [
        "event_id", "fulfillment_id", "old_status", "new_status",
        "event_time", "source", "details",
    ],
    "dispute_events": [
        "event_id", "dispute_id", "old_status", "new_status",
        "event_time", "details",
    ],
    "payout_events": [
        "event_id", "payout_id", "old_status", "new_status",
        "event_time", "details",
    ],
}

ALLOWED_STATUSES = {
    "sellers": {"ACTIVE", "AT_RISK", "SUSPENDED", "INACTIVE"},
    "product_listings": {"ACTIVE", "INACTIVE", "SUSPENDED", "OUT_OF_STOCK"},
    "orders": {
        "PLACED", "CONFIRMED", "PROCESSING", "SHIPPED",
        "DELIVERED", "CANCELLED", "RETURNED",
    },
    "fulfillments": {
        "PENDING", "PACKED", "SHIPPED", "IN_TRANSIT",
        "DELIVERED", "FAILED", "RETURNED",
    },
    "disputes": {"OPEN", "UNDER_REVIEW", "WON", "LOST", "RESOLVED"},
    "payouts": {"PENDING", "PROCESSING", "PAID", "FAILED", "CANCELLED"},
}

errors = []
warnings = []
checks = Counter()


def error(message):
    errors.append(message)


def warning(message):
    warnings.append(message)


def money(value):
    return Decimal(str(value)).quantize(CENT)


def parse_date(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_table(name):
    path = DATA_DIR / f"{name}.csv"

    if not path.exists():
        error(f"{name}: CSV file is missing.")
        return []

    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []

        missing = set(EXPECTED_COLUMNS[name]) - set(columns)
        if missing:
            error(f"{name}: Missing columns: {sorted(missing)}")
            return []

        rows = list(reader)

    checks[f"{name}_rows"] = len(rows)
    return rows


def check_unique(rows, field, table):
    values = [row[field] for row in rows]
    duplicates = [value for value, count in Counter(values).items() if count > 1]

    if duplicates:
        error(f"{table}: Duplicate {field} values: {duplicates[:5]}")
    checks[f"{table}_{field}_unique"] += 1


def check_fk(rows, field, parent_ids, table):
    invalid = [
        row[field] for row in rows
        if row[field] not in parent_ids
    ]

    if invalid:
        error(
            f"{table}: {len(invalid)} invalid {field} references. "
            f"Examples: {invalid[:5]}"
        )

    checks[f"{table}_{field}_foreign_key"] += 1


def validate():
    global errors, warnings
    errors = []
    warnings = []

    if not DATA_DIR.exists():
        error(f"Generated data directory not found: {DATA_DIR}")
        return

    tables = {
        name: load_table(name)
        for name in EXPECTED_COLUMNS
    }

    sellers = tables["sellers"]
    listings = tables["product_listings"]
    orders = tables["orders"]
    lines = tables["order_lines"]
    order_sellers = tables["order_sellers"]
    fulfillments = tables["fulfillments"]
    reviews = tables["customer_reviews"]
    disputes = tables["disputes"]
    commissions = tables["commission_rules"]
    payouts = tables["payouts"]
    payout_lines = tables["payout_lines"]
    seller_history = tables["seller_status_history"]
    fulfillment_events = tables["fulfillment_events"]
    dispute_events = tables["dispute_events"]
    payout_events = tables["payout_events"]

    # 1. Primary keys and unique fields
    primary_keys = {
        "sellers": ("seller_id",),
        "product_listings": ("listing_id",),
        "orders": ("order_id",),
        "order_lines": ("order_line_id",),
        "order_sellers": ("order_seller_id",),
        "fulfillments": ("fulfillment_id", "order_line_id", "tracking_number"),
        "customer_reviews": ("review_id",),
        "disputes": ("dispute_id",),
        "commission_rules": ("commission_rule_id",),
        "payouts": ("payout_id",),
        "payout_lines": ("payout_line_id",),
        "seller_status_history": ("event_id",),
        "fulfillment_events": ("event_id",),
        "dispute_events": ("event_id",),
        "payout_events": ("event_id",),
    }

    for table_name, fields in primary_keys.items():
        for field in fields:
            check_unique(tables[table_name], field, table_name)

    # Additional unique constraints
    check_unique(sellers, "email", "sellers")
    check_unique(disputes, "dispute_id", "disputes")

    # 2. Build parent ID sets and lookup dictionaries
    seller_ids = {r["seller_id"] for r in sellers}
    listing_ids = {r["listing_id"] for r in listings}
    order_ids = {r["order_id"] for r in orders}
    line_ids = {r["order_line_id"] for r in lines}
    fulfillment_ids = {r["fulfillment_id"] for r in fulfillments}
    dispute_ids = {r["dispute_id"] for r in disputes}
    payout_ids = {r["payout_id"] for r in payouts}

    seller_by_id = {r["seller_id"]: r for r in sellers}
    listing_by_id = {r["listing_id"]: r for r in listings}
    order_by_id = {r["order_id"]: r for r in orders}
    line_by_id = {r["order_line_id"]: r for r in lines}
    fulfillment_by_line = {r["order_line_id"]: r for r in fulfillments}
    fulfillment_by_id = {r["fulfillment_id"]: r for r in fulfillments}
    payout_by_id = {r["payout_id"]: r for r in payouts}

    # 3. Foreign key checks
    fk_checks = [
        (listings, "seller_id", seller_ids, "product_listings"),
        (lines, "order_id", order_ids, "order_lines"),
        (lines, "listing_id", listing_ids, "order_lines"),
        (lines, "seller_id", seller_ids, "order_lines"),
        (order_sellers, "order_id", order_ids, "order_sellers"),
        (order_sellers, "seller_id", seller_ids, "order_sellers"),
        (fulfillments, "order_line_id", line_ids, "fulfillments"),
        (fulfillments, "seller_id", seller_ids, "fulfillments"),
        (reviews, "order_line_id", line_ids, "customer_reviews"),
        (disputes, "order_line_id", line_ids, "disputes"),
        (disputes, "seller_id", seller_ids, "disputes"),
        (commissions, "seller_id", seller_ids, "commission_rules"),
        (payouts, "seller_id", seller_ids, "payouts"),
        (payout_lines, "payout_id", payout_ids, "payout_lines"),
        (payout_lines, "order_line_id", line_ids, "payout_lines"),
        (seller_history, "seller_id", seller_ids, "seller_status_history"),
        (fulfillment_events, "fulfillment_id", fulfillment_ids, "fulfillment_events"),
        (dispute_events, "dispute_id", dispute_ids, "dispute_events"),
        (payout_events, "payout_id", payout_ids, "payout_events"),
    ]

    for rows, field, parent_ids, table in fk_checks:
        check_fk(rows, field, parent_ids, table)

    # 4. Enum and basic field validation
    status_tables = [
        ("sellers", sellers),
        ("product_listings", listings),
        ("orders", orders),
        ("fulfillments", fulfillments),
        ("disputes", disputes),
        ("payouts", payouts),
    ]

    for table_name, rows in status_tables:
        allowed = ALLOWED_STATUSES[table_name]
        for row in rows:
            if row["status"] not in allowed:
                error(
                    f"{table_name}: Invalid status "
                    f"{row['status']} in record {row}"
                )

    for row in reviews:
        if not 1 <= int(row["rating"]) <= 5:
            error(f"customer_reviews: Invalid rating in {row['review_id']}")

    for row in lines:
        if int(row["quantity"]) <= 0:
            error(f"order_lines: Invalid quantity in {row['order_line_id']}")
        if money(row["unit_price"]) <= 0:
            error(f"order_lines: Invalid unit price in {row['order_line_id']}")
        if money(row["line_total"]) != money(
            Decimal(row["quantity"]) * money(row["unit_price"])
        ):
            error(f"order_lines: Arithmetic mismatch in {row['order_line_id']}")

    # 5. Cross-table seller/listing/order relationships
    for line in lines:
        listing = listing_by_id.get(line["listing_id"])
        if listing and listing["seller_id"] != line["seller_id"]:
            error(
                f"order_lines: Seller does not own listing "
                f"{line['listing_id']} for {line['order_line_id']}"
            )

    # Intentional anomaly: suspended sellers with active listings.
    suspended_ids = {
        r["seller_id"] for r in sellers if r["status"] == "SUSPENDED"
    }
    suspended_active_listings = [
        r for r in listings
        if r["seller_id"] in suspended_ids and r["status"] == "ACTIVE"
    ]

    if suspended_active_listings:
        warning(
            f"Expected evaluation anomaly: {len(suspended_active_listings)} "
            "active listings belong to suspended sellers."
        )

    # Verify OrderSeller bridge against actual order lines.
    expected_pairs = {
        (r["order_id"], r["seller_id"]) for r in lines
    }
    actual_pairs = {
        (r["order_id"], r["seller_id"]) for r in order_sellers
    }

    if expected_pairs != actual_pairs:
        error(
            "order_sellers: Bridge records do not exactly match "
            "the order/seller pairs in order_lines."
        )

    # Verify order totals.
    totals_by_order = defaultdict(Decimal)
    for line in lines:
        totals_by_order[line["order_id"]] += money(line["line_total"])

    for order in orders:
        calculated = money(totals_by_order[order["order_id"]])
        recorded = money(order["total_amount"])
        if calculated != recorded:
            error(f"orders: Total mismatch for {order['order_id']}")

    # Verify fulfillment ownership and one fulfillment per order line.
    for fulfillment in fulfillments:
        line = line_by_id.get(fulfillment["order_line_id"])
        if line and line["seller_id"] != fulfillment["seller_id"]:
            error(
                f"fulfillments: Seller mismatch for "
                f"{fulfillment['fulfillment_id']}"
            )

    if set(fulfillment_by_line) != line_ids:
        error("fulfillments: Every order line must have exactly one fulfillment.")

    # Verify order status against its fulfillment statuses.
    expected_fulfillment_status = {
        "DELIVERED": "DELIVERED",
        "SHIPPED": "IN_TRANSIT",
        "CANCELLED": "FAILED",
        "RETURNED": "RETURNED",
    }

    # Build an order-to-fulfillments index for efficient validation.
    fulfillments_by_order = defaultdict(list)

    for fulfillment in fulfillments:
        line = line_by_id.get(fulfillment["order_line_id"])

        if line:
            fulfillments_by_order[line["order_id"]].append(fulfillment)

    # Verify order status against its fulfillment statuses.
    for order in orders:
        expected = expected_fulfillment_status.get(order["status"])

        if expected is None:
            continue

        for fulfillment in fulfillments_by_order.get(order["order_id"], []):
            if fulfillment["status"] != expected:
                error(
                    f"orders/fulfillments: Status mismatch for "
                    f"{order['order_id']} and {fulfillment['fulfillment_id']}"
                )

    # 6. Timestamp and event-history validation
    for fulfillment in fulfillments:
        shipped = parse_date(fulfillment["shipped_at"])
        expected = parse_date(fulfillment["expected_delivery_at"])
        delivered = parse_date(fulfillment["delivered_at"])

        if shipped and expected and expected < shipped:
            error(f"fulfillments: Expected delivery precedes shipment: {fulfillment['fulfillment_id']}")

        if delivered and shipped and delivered < shipped:
            error(f"fulfillments: Delivery precedes shipment: {fulfillment['fulfillment_id']}")

        if fulfillment["status"] in ("DELIVERED", "RETURNED") and not delivered:
            error(f"fulfillments: Missing delivery timestamp: {fulfillment['fulfillment_id']}")

        if fulfillment["status"] not in ("DELIVERED", "RETURNED") and delivered:
            error(f"fulfillments: Unexpected delivery timestamp: {fulfillment['fulfillment_id']}")

    events_by_fulfillment = defaultdict(list)
    for event in fulfillment_events:
        events_by_fulfillment[event["fulfillment_id"]].append(event)

    for fulfillment_id, events in events_by_fulfillment.items():
        events.sort(key=lambda r: parse_date(r["event_time"]))
        previous_time = None
        previous_status = None

        for event in events:
            event_time = parse_date(event["event_time"])

            if previous_time and event_time < previous_time:
                error(f"fulfillment_events: Event chronology error for {fulfillment_id}")

            if previous_status is not None and event["old_status"] != previous_status:
                error(f"fulfillment_events: Broken status chain for {fulfillment_id}")

            previous_time = event_time
            previous_status = event["new_status"]

        fulfillment = fulfillment_by_id.get(fulfillment_id)
        if fulfillment and previous_status != fulfillment["status"]:
            error(f"fulfillment_events: Final event status mismatch for {fulfillment_id}")

    # Review dates and customer relationship.
    for review in reviews:
        created = parse_date(review["created_at"])
        if created > REFERENCE_TIME:
            error(f"customer_reviews: Future review timestamp {review['review_id']}")

        line = line_by_id.get(review["order_line_id"])
        if line:
            order = order_by_id.get(line["order_id"])
            if order and review["customer_id"] != order["customer_id"]:
                error(f"customer_reviews: Customer mismatch for {review['review_id']}")

        fulfillment = fulfillment_by_line.get(review["order_line_id"])
        if fulfillment and fulfillment["delivered_at"]:
            if created < parse_date(fulfillment["delivered_at"]):
                error(f"customer_reviews: Review precedes delivery for {review['review_id']}")

    # 7. Disputes
    for dispute in disputes:
        line = line_by_id.get(dispute["order_line_id"])
        if line and dispute["seller_id"] != line["seller_id"]:
            error(f"disputes: Seller mismatch for {dispute['dispute_id']}")

        if line and money(dispute["amount"]) > money(line["line_total"]):
            error(f"disputes: Amount exceeds order line value for {dispute['dispute_id']}")

        opened = parse_date(dispute["opened_at"])
        resolved = parse_date(dispute["resolved_at"])
        if resolved and resolved < opened:
            error(f"disputes: Resolution precedes opening for {dispute['dispute_id']}")

    # 8. Commission rules
    for rule in commissions:
        percentage = Decimal(rule["commission_percentage"])
        if percentage < 0 or percentage > 100:
            error(f"commission_rules: Invalid percentage in {rule['commission_rule_id']}")

        start = parse_date(rule["effective_from"])
        end = parse_date(rule["effective_to"])
        if end and end < start:
            error(f"commission_rules: Invalid effective dates in {rule['commission_rule_id']}")

    # 9. Payout line arithmetic, ownership and eligibility
    payout_lines_by_payout = defaultdict(list)
    payout_lines_by_order_line = defaultdict(list)

    for payout_line in payout_lines:
        payout_lines_by_payout[payout_line["payout_id"]].append(payout_line)
        payout_lines_by_order_line[payout_line["order_line_id"]].append(payout_line)

        gross = money(payout_line["gross_amount"])
        commission = money(payout_line["commission_amount"])
        refund = money(payout_line["refund_amount"])
        chargeback = money(payout_line["chargeback_amount"])
        reserve = money(payout_line["reserve_amount"])
        net = money(payout_line["net_amount"])

        calculated_net = money(gross - commission - refund - chargeback - reserve)

        if calculated_net != net:
            error(f"payout_lines: Net arithmetic mismatch in {payout_line['payout_line_id']}")

        if min(gross, commission, refund, chargeback, reserve, net) < 0:
            error(f"payout_lines: Negative amount in {payout_line['payout_line_id']}")

        line = line_by_id.get(payout_line["order_line_id"])
        payout = payout_by_id.get(payout_line["payout_id"])

        if line and payout:
            if money(payout_line["gross_amount"]) != money(line["line_total"]):
                error(f"payout_lines: Gross amount mismatch in {payout_line['payout_line_id']}")

            if line["seller_id"] != payout["seller_id"]:
                error(f"payout_lines: Seller ownership mismatch in {payout_line['payout_line_id']}")

        if line:
            fulfillment = fulfillment_by_line.get(line["order_line_id"])
            if not fulfillment or fulfillment["status"] != "DELIVERED":
                error(f"payout_lines: Ineligible fulfillment in {payout_line['payout_line_id']}")
            elif not fulfillment["delivered_at"]:
                error(f"payout_lines: Missing delivery date in {payout_line['payout_line_id']}")
            else:
                hold_expiry = parse_date(fulfillment["delivered_at"])
                from datetime import timedelta
                if hold_expiry + timedelta(days=7) > REFERENCE_TIME:
                    error(f"payout_lines: Seven-day hold not expired in {payout_line['payout_line_id']}")

    for order_line_id, records in payout_lines_by_order_line.items():
        if len(records) > 1:
            error(f"payout_lines: Duplicate payout for order line {order_line_id}")

    for payout in payouts:
        lines_for_payout = payout_lines_by_payout[payout["payout_id"]]
        calculated_total = money(
            sum((money(r["net_amount"]) for r in lines_for_payout), Decimal("0.00"))
        )

        if calculated_total != money(payout["total_amount"]):
            error(f"payouts: Header/line reconciliation mismatch for {payout['payout_id']}")

        if payout["status"] == "PAID" and not payout["payout_date"]:
            error(f"payouts: Paid payout missing payout date: {payout['payout_id']}")

    # 10. Seller status history
    history_by_seller = defaultdict(list)
    for event in seller_history:
        history_by_seller[event["seller_id"]].append(event)

    for seller in sellers:
        if seller["status"] != "ACTIVE" and seller["seller_id"] not in history_by_seller:
            error(f"seller_status_history: Missing status event for {seller['seller_id']}")

        events = history_by_seller[seller["seller_id"]]
        if events and events[-1]["new_status"] != seller["status"]:
            error(f"seller_status_history: Final status mismatch for {seller['seller_id']}")



    # 11. Ground truth coverage and record-level fixture validation
    ground_truth_path = DATA_DIR / "ground_truth.csv"

    if not ground_truth_path.exists():
        error("ground_truth.csv is missing.")
        ground_truth = []
    else:
        with ground_truth_path.open("r", newline="", encoding="utf-8") as file:
            ground_truth = list(csv.DictReader(file))

    expected_anomalies = {
        "PAYOUT_BEFORE_DELIVERY",
        "DUPLICATE_COMMISSION",
        "SUSPENDED_SELLER_ACTIVE_LISTING",
        "LOST_DISPUTE_NOT_DEDUCTED",
        "PAYOUT_HEADER_MISMATCH",
    }

    actual_anomalies = {r.get("anomaly_type") for r in ground_truth}
    missing_anomalies = expected_anomalies - actual_anomalies

    if missing_anomalies:
        error(f"ground_truth: Missing anomaly labels: {sorted(missing_anomalies)}")

    if len(ground_truth) != len(expected_anomalies):
        error("ground_truth: Expected exactly five scenario labels.")

    # Load concrete evaluation fixtures.
    fixture_path = BASE_DIR / "data" / "ground_truth" / "anomaly_fixtures.json"
    fixture_document = {}
    fixtures = []

    if not fixture_path.exists():
        error("anomaly_fixtures.json is missing.")
    else:
        try:
            fixture_document = json.loads(
                fixture_path.read_text(encoding="utf-8")
            )
            fixtures = fixture_document.get("fixtures", [])

            if not isinstance(fixtures, list):
                error("anomaly_fixtures: 'fixtures' must be a list.")
                fixtures = []

        except (json.JSONDecodeError, OSError) as exc:
            error(f"anomaly_fixtures: Unable to read JSON: {exc}")

    expected_fixture_types = {
        "PAYOUT_BEFORE_DELIVERY",
        "DUPLICATE_COMMISSION",
        "SUSPENDED_SELLER_ACTIVE_LISTING",
        "LOST_DISPUTE_NOT_DEDUCTED",
        "PAYOUT_HEADER_MISMATCH",
    }

    actual_fixture_types = {
        fixture.get("anomaly_type") for fixture in fixtures
        if isinstance(fixture, dict)
    }

    missing_fixture_types = expected_fixture_types - actual_fixture_types
    extra_fixture_types = actual_fixture_types - expected_fixture_types

    if missing_fixture_types:
        error(
            "anomaly_fixtures: Missing fixture types: "
            f"{sorted(missing_fixture_types)}"
        )

    if extra_fixture_types:
        error(
            "anomaly_fixtures: Unexpected fixture types: "
            f"{sorted(extra_fixture_types)}"
        )

    if len(fixtures) != 5:
        error("anomaly_fixtures: Expected exactly five fixtures.")

    if fixture_document.get("fixture_count") != len(fixtures):
        error("anomaly_fixtures: fixture_count metadata does not match.")

    if fixture_document.get("project") != "MarketGuard":
        error("anomaly_fixtures: Invalid project metadata.")

    if fixture_document.get("seed") is None:
        error("anomaly_fixtures: Seed metadata is missing.")

    fixture_ids = [
        fixture.get("fixture_id")
        for fixture in fixtures
        if isinstance(fixture, dict)
    ]

    if len(fixture_ids) != len(set(fixture_ids)):
        error("anomaly_fixtures: Duplicate fixture IDs found.")

    fixture_by_type = {
        fixture.get("anomaly_type"): fixture
        for fixture in fixtures
        if isinstance(fixture, dict)
    }

    # Additional lookup dictionaries for fixture validation.
    dispute_by_id = {
        row["dispute_id"]: row for row in disputes
    }

    payout_line_by_id = {
        row["payout_line_id"]: row for row in payout_lines
    }

    # All five fixtures must be marked as evaluation-only.
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            error("anomaly_fixtures: Invalid fixture entry.")
            continue

        if fixture.get("evaluation_only") is not True:
            error(
                "anomaly_fixtures: Fixture must be evaluation-only: "
                f"{fixture.get('fixture_id')}"
            )

        if not isinstance(fixture.get("records"), dict):
            error(
                "anomaly_fixtures: Missing records object in "
                f"{fixture.get('fixture_id')}"
            )

        if not isinstance(fixture.get("expected"), dict):
            error(
                "anomaly_fixtures: Missing expected object in "
                f"{fixture.get('fixture_id')}"
            )

        if not isinstance(fixture.get("observed"), dict):
            error(
                "anomaly_fixtures: Missing observed object in "
                f"{fixture.get('fixture_id')}"
            )

    # --------------------------------------------------------
    # ANOM-001: Payout attempted before delivery / hold expiry
    # --------------------------------------------------------
    fixture = fixture_by_type.get("PAYOUT_BEFORE_DELIVERY")

    if fixture:
        records = fixture.get("records", {})
        expected = fixture.get("expected", {})
        observed = fixture.get("observed", {})

        payout_line = payout_line_by_id.get(records.get("payout_line_id"))
        fulfillment = next(
            (
                row for row in fulfillments
                if row["fulfillment_id"] == records.get("fulfillment_id")
            ),
            None,
        )
        payout = payout_by_id.get(records.get("payout_id"))

        if not payout_line:
            error("ANOM-001: Referenced payout line does not exist.")

        if not fulfillment:
            error("ANOM-001: Referenced fulfillment does not exist.")

        if not payout:
            error("ANOM-001: Referenced payout does not exist.")

        if payout_line and fulfillment:
            if payout_line["order_line_id"] != records.get("order_line_id"):
                error("ANOM-001: Payout line order-line reference mismatch.")

            if fulfillment["order_line_id"] != records.get("order_line_id"):
                error("ANOM-001: Fulfillment order-line reference mismatch.")

            if payout_line["payout_id"] != records.get("payout_id"):
                error("ANOM-001: Payout line payout reference mismatch.")

        if fulfillment and fulfillment["delivered_at"]:
            delivery_at = parse_date(fulfillment["delivered_at"])
            expected_delivery = parse_date(expected.get("delivery_at"))
            eligible_after = parse_date(expected.get("eligible_after"))
            attempt_at = parse_date(
                observed.get("simulated_payout_attempt_at")
            )

            if expected_delivery != delivery_at:
                error("ANOM-001: Expected delivery date does not match CSV.")

            if eligible_after != delivery_at + timedelta(days=7):
                error("ANOM-001: Seven-day eligibility date is incorrect.")

            if not attempt_at or attempt_at >= delivery_at:
                error("ANOM-001: Simulated payout attempt is not before delivery.")

            if attempt_at and attempt_at >= eligible_after:
                error("ANOM-001: Simulated attempt does not violate the hold period.")

    # --------------------------------------------------------
    # ANOM-002: Duplicate commission application
    # --------------------------------------------------------
    fixture = fixture_by_type.get("DUPLICATE_COMMISSION")

    if fixture:
        records = fixture.get("records", {})
        expected = fixture.get("expected", {})
        observed = fixture.get("observed", {})

        payout_line = payout_line_by_id.get(records.get("payout_line_id"))

        if not payout_line:
            error("ANOM-002: Referenced payout line does not exist.")
        else:
            if payout_line["payout_id"] != records.get("payout_id"):
                error("ANOM-002: Payout reference mismatch.")

            if payout_line["order_line_id"] != records.get("order_line_id"):
                error("ANOM-002: Order-line reference mismatch.")

            expected_commission = money(expected.get("commission_amount", "0"))
            actual_commission = money(payout_line["commission_amount"])
            observed_commission = money(observed.get("commission_amount", "0"))

            if actual_commission != expected_commission:
                error("ANOM-002: Expected commission does not match source CSV.")

            if observed_commission != money(expected_commission * 2):
                error("ANOM-002: Observed commission is not exactly double.")

            if expected.get("application_count") != 1:
                error("ANOM-002: Expected application count must be one.")

            if observed.get("application_count") != 2:
                error("ANOM-002: Observed application count must be two.")

    # --------------------------------------------------------
    # ANOM-003: Suspended seller with active listing
    # --------------------------------------------------------
    fixture = fixture_by_type.get("SUSPENDED_SELLER_ACTIVE_LISTING")

    if fixture:
        records = fixture.get("records", {})
        expected = fixture.get("expected", {})
        observed = fixture.get("observed", {})

        seller = seller_by_id.get(records.get("seller_id"))
        listing = listing_by_id.get(records.get("listing_id"))

        if not seller:
            error("ANOM-003: Referenced seller does not exist.")

        if not listing:
            error("ANOM-003: Referenced listing does not exist.")

        if seller and listing:
            if listing["seller_id"] != seller["seller_id"]:
                error("ANOM-003: Listing does not belong to referenced seller.")

            if seller["status"] != expected.get("seller_status"):
                error("ANOM-003: Actual seller status differs from expected.")

            if listing["status"] != observed.get("listing_status"):
                error("ANOM-003: Observed listing status differs from CSV.")

            if seller["status"] != observed.get("seller_status"):
                error("ANOM-003: Observed seller status differs from CSV.")

            if expected.get("listing_status") != "INACTIVE":
                error("ANOM-003: Expected listing status must be INACTIVE.")

            if observed.get("listing_status") != "ACTIVE":
                error("ANOM-003: Observed listing status must be ACTIVE.")

    # --------------------------------------------------------
    # ANOM-004: Lost dispute deduction missing
    # --------------------------------------------------------
    fixture = fixture_by_type.get("LOST_DISPUTE_NOT_DEDUCTED")

    if fixture:
        records = fixture.get("records", {})
        expected = fixture.get("expected", {})
        observed = fixture.get("observed", {})

        dispute = dispute_by_id.get(records.get("dispute_id"))
        payout_line = payout_line_by_id.get(records.get("payout_line_id"))

        if not dispute:
            error("ANOM-004: Referenced dispute does not exist.")

        if not payout_line:
            error("ANOM-004: Referenced payout line does not exist.")

        if dispute and payout_line:
            if dispute["order_line_id"] != records.get("order_line_id"):
                error("ANOM-004: Dispute order-line reference mismatch.")

            if payout_line["order_line_id"] != records.get("order_line_id"):
                error("ANOM-004: Payout-line order-line reference mismatch.")

            if payout_line["payout_id"] != records.get("payout_id"):
                error("ANOM-004: Payout reference mismatch.")

            if dispute["status"] != expected.get("dispute_status"):
                error("ANOM-004: Dispute status does not match expected.")

            if dispute["dispute_type"] != expected.get("dispute_type"):
                error("ANOM-004: Dispute type does not match expected.")

            actual_deduction = money(
                payout_line["refund_amount"]
            ) + money(payout_line["chargeback_amount"])

            expected_deduction = money(expected.get("deduction_amount", "0"))
            observed_deduction = money(observed.get("deduction_amount", "0"))

            if actual_deduction != expected_deduction:
                error("ANOM-004: Expected deduction does not match source payout line.")

            if expected_deduction <= 0:
                error("ANOM-004: Expected deduction must be positive.")

            if observed_deduction != Decimal("0.00"):
                error("ANOM-004: Observed missing deduction must be zero.")

    # --------------------------------------------------------
    # ANOM-005: Payout header / line total mismatch
    # --------------------------------------------------------
    fixture = fixture_by_type.get("PAYOUT_HEADER_MISMATCH")

    if fixture:
        records = fixture.get("records", {})
        expected = fixture.get("expected", {})
        observed = fixture.get("observed", {})

        payout = payout_by_id.get(records.get("payout_id"))
        referenced_line_ids = records.get("payout_line_ids", [])

        if not payout:
            error("ANOM-005: Referenced payout does not exist.")

        if not referenced_line_ids:
            error("ANOM-005: No payout line IDs supplied.")

        referenced_lines = []

        for payout_line_id in referenced_line_ids:
            payout_line = payout_line_by_id.get(payout_line_id)

            if not payout_line:
                error(f"ANOM-005: Payout line {payout_line_id} does not exist.")
                continue

            if payout_line["payout_id"] != records.get("payout_id"):
                error(
                    f"ANOM-005: Payout line {payout_line_id} "
                    "belongs to another payout."
                )

            referenced_lines.append(payout_line)

        if payout:
            actual_header = money(payout["total_amount"])
            expected_header = money(expected.get("header_amount", "0"))
            observed_header = money(observed.get("header_amount", "0"))

            if actual_header != expected_header:
                error("ANOM-005: Expected header does not match source payout.")

            if observed_header == expected_header:
                error("ANOM-005: Observed header must differ from expected.")

        calculated_line_total = money(
            sum(
                (money(row["net_amount"]) for row in referenced_lines),
                Decimal("0.00"),
            )
        )

        expected_line_total = money(expected.get("line_total", "0"))

        if calculated_line_total != expected_line_total:
            error("ANOM-005: Expected line total does not match referenced lines.")

        if expected_header != expected_line_total:
            error("ANOM-005: Expected header and line total must reconcile.")

    checks["record_level_anomaly_fixtures"] = len(fixtures)


    # 12. Summary and report
    result = {
        "project": "MarketGuard",
        "reference_time": REFERENCE_TIME.isoformat(),
        "status": "PASS" if not errors else "FAIL",
        "checks": dict(checks),
        "row_counts": {
            name: len(rows) for name, rows in tables.items()
        },
        "ground_truth_labels": len(ground_truth),
        "expected_suspended_listing_anomalies": len(suspended_active_listings),
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("\n========== MARKETGUARD VALIDATION ==========")
    print(f"Status: {result['status']}")
    print(f"Errors: {result['error_count']}")
    print(f"Warnings: {result['warning_count']}")
    print(f"Ground-truth labels: {result['ground_truth_labels']}")
    print(
        "Suspended seller active listings: "
        f"{result['expected_suspended_listing_anomalies']}"
    )

    if errors:
        print("\nERRORS:")
        for item in errors[:50]:
            print(f" - {item}")
        if len(errors) > 50:
            print(f" ... and {len(errors) - 50} more errors")

    if warnings:
        print("\nWARNINGS:")
        for item in warnings:
            print(f" - {item}")

    print(f"\nDetailed report: {REPORT_PATH}")


def main():
    validate()


if __name__ == "__main__":
    main()
