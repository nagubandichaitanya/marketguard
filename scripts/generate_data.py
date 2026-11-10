
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


# ============================================================
# 1. IMPORTS AND CONFIGURATION
# ============================================================

SEED = 20261022

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data" / "generated"
GROUND_TRUTH_DIR = BASE_DIR / "data" / "ground_truth"
MANIFEST_DIR = BASE_DIR / "data" / "manifests"

STARTER_SCALE = {
    "sellers": 40,
    "listings": 250,
    "orders": 600,
}

FULL_SCALE = {
    "sellers": 2000,
    "listings": 20000,
    "orders": 100000,
}

# Fixed reference time ensures reproducible datasets.
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

CENT = Decimal("0.01")


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def money(value) -> Decimal:
    """Convert a value into a two-decimal monetary amount."""
    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def iso(value):
    """Convert datetime into ISO 8601 format."""
    return value.isoformat() if value else None


def write_csv(name, rows):
    """Write records into a CSV file."""

    path = DATA_DIR / f"{name}.csv"
    rows = list(rows)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):
    """Write records into a formatted JSON file."""

    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def calculate_checksum(path):
    """Generate SHA-256 checksum for a file."""

    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# 3. MAIN DATA GENERATION FUNCTION
# ============================================================

def generate(scale="starter", seed=SEED):

    if scale not in ("starter", "full"):
        raise ValueError("Scale must be starter or full.")

    counts = (
        STARTER_SCALE
        if scale == "starter"
        else FULL_SCALE
    )

    # Fixed random generator for reproducibility.
    rng = random.Random(seed)

    # --------------------------------------------------------
    # Initialize all data collections
    # --------------------------------------------------------

    sellers = []
    listings = []
    orders = []
    order_lines = []
    order_sellers = []
    fulfillments = []
    reviews = []
    disputes = []
    commission_rules = []
    payouts = []
    payout_lines = []

    seller_history = []
    fulfillment_events = []
    dispute_events = []
    payout_events = []

    ground_truth = []

    # --------------------------------------------------------
    # Master data
    # --------------------------------------------------------

    seller_statuses = [
        "ACTIVE",
        "ACTIVE",
        "ACTIVE",
        "ACTIVE",
        "AT_RISK",
        "INACTIVE",
        "SUSPENDED",
    ]

    cities = [
        "Hyderabad",
        "Bengaluru",
        "Chennai",
        "Mumbai",
        "Pune",
    ]

    categories = [
        "Electronics",
        "Fashion",
        "Home",
        "Books",
        "Beauty",
    ]

    carriers = [
        "BlueDart",
        "Delhivery",
        "DTDC",
        "Ecom Express",
    ]

    products = {
        "Electronics": [
            "Wireless Mouse",
            "Keyboard",
            "Headphones",
            "USB Hub",
        ],
        "Fashion": [
            "Cotton Shirt",
            "Jeans",
            "Backpack",
            "Sneakers",
        ],
        "Home": [
            "Storage Box",
            "Table Lamp",
            "Bedsheet",
            "Water Bottle",
        ],
        "Books": [
            "Python Basics",
            "Data Science Guide",
            "SQL Handbook",
        ],
        "Beauty": [
            "Face Wash",
            "Moisturizer",
            "Sunscreen",
        ],
    }

    # ========================================================
    # 4. GENERATE SELLERS
    # ========================================================

    print("\nGenerating sellers...")

    for i in range(1, counts["sellers"] + 1):

        seller_id = f"SELL-{i:06d}"

        # Guarantee suspended sellers for anomaly evaluation.
        if i <= 2:
            status = "SUSPENDED"
        else:
            status = rng.choice(seller_statuses)

        seller = {
            "seller_id": seller_id,
            "seller_name": f"Marketplace Seller {i:04d}",
            "email": f"seller{i:04d}@example.test",
            "phone": f"+919000{i:05d}",
            "city": rng.choice(cities),
            "status": status,
            "created_at": iso(
                NOW - timedelta(days=rng.randint(180, 900))
            ),
        }

        sellers.append(seller)

        # Record seller status history.
        if status != "ACTIVE":

            seller_history.append({
                "event_id": len(seller_history) + 1,
                "seller_id": seller_id,
                "old_status": "ACTIVE",
                "new_status": status,
                "reason": "Synthetic seller status initialization",
                "event_time": iso(
                    NOW - timedelta(days=90)
                ),
            })

        # Create seller commission rule.
        commission_rules.append({
            "commission_rule_id": f"COM-{i:06d}-01",
            "seller_id": seller_id,
            "commission_percentage": str(
                money(rng.choice([8, 10, 12, 15]))
            ),
            "effective_from": iso(
                NOW - timedelta(days=365)
            ),
            "effective_to": None,
        })

    # ========================================================
    # 5. GENERATE PRODUCT LISTINGS
    # ========================================================

    print("Generating product listings...")

    seller_listing_map = defaultdict(list)

    for i in range(1, counts["listings"] + 1):

        seller = sellers[(i - 1) % len(sellers)]

        seller_id = seller["seller_id"]

        category = rng.choice(categories)

        status = "ACTIVE"

        # Inject an active listing belonging to a suspended seller.
        existing_active_listing = any(
            row["seller_id"] == seller_id
            and row["status"] == "ACTIVE"
            for row in listings
        )

        if (
            seller["status"] == "SUSPENDED"
            and not existing_active_listing
        ):
            status = "ACTIVE"

        elif seller["status"] != "ACTIVE":
            status = "INACTIVE"

        listing = {
            "listing_id": f"LIST-{seller_id}-{i:06d}",
            "seller_id": seller_id,
            "product_name": rng.choice(products[category]),
            "category": category,
            "price": str(
                money(rng.uniform(100, 15000))
            ),
            "stock_quantity": rng.randint(0, 300),
            "status": status,
            "created_at": iso(
                NOW - timedelta(days=rng.randint(30, 300))
            ),
        }

        listings.append(listing)

        seller_listing_map[seller_id].append(listing)

    # ========================================================
    # 6. GENERATE ORDERS AND ORDER LINES
    # ========================================================

    print("Generating orders and order lines...")

    for i in range(1, counts["orders"] + 1):

        order_id = f"ORD-2026-{i:06d}"

        customer_id = (
            f"CUST-{rng.randint(1, max(100, counts['orders'] // 3)):06d}"
        )

        # Keep orders safely in the past.
        order_date = NOW - timedelta(
            days=rng.randint(15, 120)
        )

        # Each order can contain one to three products.
        line_count = rng.randint(1, 3)

        selected_listings = rng.sample(
            listings,
            min(line_count, len(listings)),
        )

        lines_for_order = []

        total = Decimal("0.00")

        # ----------------------------------------------------
        # Generate order lines
        # ----------------------------------------------------

        for j, listing in enumerate(
            selected_listings,
            start=1,
        ):

            quantity = rng.randint(1, 3)

            unit_price = money(listing["price"])

            line_total = money(
                unit_price * quantity
            )

            line_id = f"{order_id}-LINE-{j:02d}"

            line = {
                "order_line_id": line_id,
                "order_id": order_id,
                "listing_id": listing["listing_id"],
                "seller_id": listing["seller_id"],
                "quantity": quantity,
                "unit_price": str(unit_price),
                "line_total": str(line_total),
            }

            order_lines.append(line)

            lines_for_order.append(line)

            total += line_total

        # ----------------------------------------------------
        # Generate order-seller bridge records
        # ----------------------------------------------------

        order_seller_ids = sorted({
            line["seller_id"]
            for line in lines_for_order
        })

        for seller_id in order_seller_ids:

            order_sellers.append({
                "order_seller_id": len(order_sellers) + 1,
                "order_id": order_id,
                "seller_id": seller_id,
            })

        # ----------------------------------------------------
        # Determine order status
        # ----------------------------------------------------

        outcome = rng.random()

        if outcome < 0.78:
            order_status = "DELIVERED"

        elif outcome < 0.90:
            order_status = "SHIPPED"

        elif outcome < 0.96:
            order_status = "CANCELLED"

        else:
            order_status = "RETURNED"

        # ----------------------------------------------------
        # Create order header
        # ----------------------------------------------------

        orders.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "order_date": iso(order_date),
            "total_amount": str(money(total)),
            "status": order_status,
            "created_at": iso(order_date),
        })

        # ====================================================
        # 7. GENERATE FULFILLMENTS AND EVENTS
        # ====================================================

        for line in lines_for_order:

            seller_id = line["seller_id"]

            fulfillment_id = (
                f"FUL-{line['order_line_id']}"
            )

            shipped_at = order_date + timedelta(
                days=rng.randint(1, 2)
            )

            expected_at = shipped_at + timedelta(
                days=rng.randint(2, 5)
            )

            # Determine fulfillment outcome.
            if order_status == "DELIVERED":

                delivered_at = expected_at + timedelta(
                    days=rng.choice([-1, 0, 0, 1, 3])
                )

                fulfillment_status = "DELIVERED"

            elif order_status == "SHIPPED":

                delivered_at = None

                fulfillment_status = "IN_TRANSIT"

            elif order_status == "CANCELLED":

                delivered_at = None

                fulfillment_status = "FAILED"

            else:

                delivered_at = expected_at + timedelta(days=1)

                fulfillment_status = "RETURNED"

            fulfillment = {
                "fulfillment_id": fulfillment_id,
                "order_line_id": line["order_line_id"],
                "seller_id": seller_id,
                "carrier": rng.choice(carriers),
                "tracking_number": (
                    f"MGTRK{i:07d}{len(fulfillments):04d}"
                ),
                "status": fulfillment_status,
                "shipped_at": iso(shipped_at),
                "expected_delivery_at": iso(expected_at),
                "delivered_at": iso(delivered_at),
            }

            fulfillments.append(fulfillment)

            # ------------------------------------------------
            # Fulfillment lifecycle events
            # ------------------------------------------------

            transitions = [
                (None, "PENDING", order_date),

                (
                    "PENDING",
                    "PACKED",
                    order_date + timedelta(hours=4),
                ),

                (
                    "PACKED",
                    "SHIPPED",
                    shipped_at,
                ),
            ]

            if fulfillment_status in (
                "DELIVERED",
                "RETURNED",
            ):

                transitions.append((
                    "SHIPPED",
                    "IN_TRANSIT",
                    shipped_at + timedelta(hours=12),
                ))

                transitions.append((
                    "IN_TRANSIT",
                    fulfillment_status,
                    delivered_at,
                ))

            elif fulfillment_status == "IN_TRANSIT":

                transitions.append((
                    "SHIPPED",
                    "IN_TRANSIT",
                    shipped_at + timedelta(hours=12),
                ))

            else:

                transitions.append((
                    "SHIPPED",
                    "FAILED",
                    shipped_at + timedelta(hours=3),
                ))

            for old_status, new_status, event_time in transitions:

                fulfillment_events.append({
                    "event_id": len(fulfillment_events) + 1,
                    "fulfillment_id": fulfillment_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "event_time": iso(event_time),
                    "source": "synthetic_generator",
                    "details": json.dumps({
                        "generated": True
                    }),
                })

            # =================================================
            # 8. GENERATE CUSTOMER REVIEWS
            # =================================================

            if (
                fulfillment_status in ("DELIVERED", "RETURNED")
                and rng.random() < 0.35
            ):

                reviews.append({
                    "review_id": f"REV-{len(reviews) + 1:07d}",
                    "order_line_id": line["order_line_id"],
                    "customer_id": customer_id,
                    "rating": rng.randint(1, 5),
                    "review_text": rng.choice([
                        "Good product quality",
                        "Delivery was satisfactory",
                        "Product matched description",
                        "Could be improved",
                    ]),
                    "created_at": iso(
                        delivered_at
                        + timedelta(days=rng.randint(1, 7))
                    ),
                })

            # =================================================
            # 9. GENERATE DISPUTES AND DISPUTE EVENTS
            # =================================================

            if rng.random() < 0.06:

                dispute_id = (
                    f"DSP-2026-{len(disputes) + 1:06d}"
                )

                dispute_status = rng.choice([
                    "OPEN",
                    "UNDER_REVIEW",
                    "WON",
                    "LOST",
                    "RESOLVED",
                ])

                dispute_type = rng.choice([
                    "REFUND",
                    "CHARGEBACK",
                    "NOT_RECEIVED",
                    "DAMAGED",
                    "OTHER",
                ])

                amount = money(
                    min(
                        Decimal(line["line_total"]),
                        money(rng.uniform(50, 1000)),
                    )
                )

                opened_at = order_date + timedelta(
                    days=rng.randint(2, 10)
                )

                resolved_at = (
                    None
                    if dispute_status in (
                        "OPEN",
                        "UNDER_REVIEW",
                    )
                    else opened_at + timedelta(days=3)
                )

                disputes.append({
                    "dispute_id": dispute_id,
                    "order_line_id": line["order_line_id"],
                    "seller_id": seller_id,
                    "dispute_type": dispute_type,
                    "amount": str(amount),
                    "status": dispute_status,
                    "opened_at": iso(opened_at),
                    "resolved_at": iso(resolved_at),
                })

                # Initial dispute event.
                dispute_events.append({
                    "event_id": len(dispute_events) + 1,
                    "dispute_id": dispute_id,
                    "old_status": None,
                    "new_status": "OPEN",
                    "event_time": iso(opened_at),
                    "details": json.dumps({
                        "generated": True
                    }),
                })

                # Final dispute event.
                # OPEN disputes have no additional event.
                # UNDER_REVIEW disputes use a valid review timestamp.
                if dispute_status != "OPEN":

                    final_event_time = (
                        resolved_at
                        if resolved_at is not None
                        else opened_at + timedelta(days=1)
                    )

                    dispute_events.append({
                        "event_id": len(dispute_events) + 1,
                        "dispute_id": dispute_id,
                        "old_status": "OPEN",
                        "new_status": dispute_status,
                        "event_time": iso(final_event_time),
                        "details": json.dumps({
                            "generated": True
                        }),
                    })

    # ========================================================
    # 10. GENERATE COMMISSIONS AND PAYOUTS
    # ========================================================

    print("Generating commissions and payouts...")

    # Only delivered order lines whose seven-day hold expired
    # are eligible for payout.

    delivered_lines = {
        fulfillment["order_line_id"]: fulfillment

        for fulfillment in fulfillments

        if (
            fulfillment["status"] == "DELIVERED"
            and datetime.fromisoformat(
                fulfillment["delivered_at"]
            ) + timedelta(days=7) <= NOW
        )
    }

    # --------------------------------------------------------
    # Index commission rules by seller for faster lookup.
    # --------------------------------------------------------

    commission_rule_by_seller = {
        rule["seller_id"]: rule
        for rule in commission_rules
    }

    # --------------------------------------------------------
    # Index lost disputes by order line.
    # --------------------------------------------------------

    lost_dispute_by_line = {}

    for dispute in disputes:

        if dispute["status"] == "LOST":

            lost_dispute_by_line.setdefault(
                dispute["order_line_id"],
                dispute,
            )

    # --------------------------------------------------------
    # Generate seller payouts.
    # --------------------------------------------------------

    for seller in sellers:

        seller_id = seller["seller_id"]

        eligible = [
            line
            for line in order_lines
            if (
                line["seller_id"] == seller_id
                and line["order_line_id"] in delivered_lines
            )
        ]

        if not eligible:
            continue

        payout_id = f"PAYOUT-{len(payouts) + 1:06d}"

        payout_total = Decimal("0.00")

        payout_lines_for_seller = []

        for line in eligible:

            # Step 1: Gross amount.
            gross = money(line["line_total"])

            # Step 2: Applicable seller commission.
            rule = commission_rule_by_seller[seller_id]

            commission = money(
                gross
                * Decimal(rule["commission_percentage"])
                / Decimal("100")
            )

            # Step 3: Find lost dispute.
            lost_dispute = lost_dispute_by_line.get(
                line["order_line_id"]
            )

            # Step 4: Remaining payable balance.
            remaining_balance = money(
                max(
                    gross - commission,
                    Decimal("0.00"),
                )
            )

            chargeback = Decimal("0.00")
            refund = Decimal("0.00")

            # Step 5: Apply lost dispute deductions.
            if lost_dispute:

                deduction = min(
                    money(lost_dispute["amount"]),
                    remaining_balance,
                )

                if lost_dispute["dispute_type"] == "CHARGEBACK":

                    chargeback = deduction

                elif lost_dispute["dispute_type"] == "REFUND":

                    refund = deduction

            # Step 6: Reserve amount.
            reserve = Decimal("0.00")

            # Step 7: Net payout.
            net = money(
                gross
                - commission
                - refund
                - chargeback
                - reserve
            )

            # Step 8: Create payout line.
            payout_line = {
                "payout_line_id": (
                    f"PL-{len(payout_lines) + len(payout_lines_for_seller) + 1:08d}"
                ),
                "payout_id": payout_id,
                "order_line_id": line["order_line_id"],
                "gross_amount": str(gross),
                "commission_amount": str(commission),
                "refund_amount": str(refund),
                "chargeback_amount": str(chargeback),
                "reserve_amount": str(reserve),
                "net_amount": str(net),
            }

            payout_lines_for_seller.append(payout_line)

            payout_total += net

        # ----------------------------------------------------
        # Create payout header.
        # ----------------------------------------------------

        payouts.append({
            "payout_id": payout_id,
            "seller_id": seller_id,
            "payout_date": iso(NOW),
            "total_amount": str(money(payout_total)),
            "status": "PAID",
        })

        payout_lines.extend(payout_lines_for_seller)

        # ----------------------------------------------------
        # Create payout lifecycle events.
        # ----------------------------------------------------

        payout_events.append({
            "event_id": len(payout_events) + 1,
            "payout_id": payout_id,
            "old_status": None,
            "new_status": "PENDING",
            "event_time": iso(NOW - timedelta(days=1)),
            "details": json.dumps({
                "generated": True
            }),
        })

        payout_events.append({
            "event_id": len(payout_events) + 1,
            "payout_id": payout_id,
            "old_status": "PENDING",
            "new_status": "PAID",
            "event_time": iso(NOW),
            "details": json.dumps({
                "generated": True
            }),
        })

    # ========================================================
    # 11. GENERATE ANOMALY GROUND TRUTH LABELS
    # ========================================================

    print("Generating anomaly ground truth labels...")

    anomaly_definitions = [

        (
            "ANOM-001",
            "PAYOUT_BEFORE_DELIVERY",
            "Payout attempted before delivery or hold expiry",
        ),

        (
            "ANOM-002",
            "DUPLICATE_COMMISSION",
            "Commission applied more than once to the same order line",
        ),

        (
            "ANOM-003",
            "SUSPENDED_SELLER_ACTIVE_LISTING",
            "Suspended seller has an active listing",
        ),

        (
            "ANOM-004",
            "LOST_DISPUTE_NOT_DEDUCTED",
            "Lost dispute amount absent from payout deductions",
        ),

        (
            "ANOM-005",
            "PAYOUT_HEADER_MISMATCH",
            "Payout header does not equal sum of payout lines",
        ),
    ]

    for anomaly_id, anomaly_type, description in anomaly_definitions:

        ground_truth.append({
            "anomaly_id": anomaly_id,
            "anomaly_type": anomaly_type,
            "description": description,
            "is_anomaly": True,
            "evaluation_only": True,
        })

    # ========================================================
    # 12. GENERATE RECORD-LEVEL ANOMALY FIXTURES
    # ========================================================

    print("Generating record-level anomaly fixtures...")

    # Build indexes for deterministic fixture selection.
    payout_line_by_order_line = {
        row["order_line_id"]: row
        for row in payout_lines
    }

    fulfillment_by_order_line = {
        row["order_line_id"]: row
        for row in fulfillments
    }

    seller_by_id = {
        row["seller_id"]: row
        for row in sellers
    }

    # --------------------------------------------------------
    # ANOM-001: PAYOUT BEFORE DELIVERY / HOLD EXPIRY
    # --------------------------------------------------------

    anomaly_001_candidate = next(
        (
            row
            for row in payout_lines
            if row["order_line_id"] in fulfillment_by_order_line
        ),
        None,
    )

    if anomaly_001_candidate is None:
        raise ValueError(
            "Unable to create ANOM-001 fixture: no payout line found."
        )

    fulfillment_001 = fulfillment_by_order_line[
        anomaly_001_candidate["order_line_id"]
    ]

    delivery_time_001 = datetime.fromisoformat(
        fulfillment_001["delivered_at"]
    )

    eligible_after_001 = (
        delivery_time_001 + timedelta(days=7)
    )

    # Simulate an attempted payout one minute before delivery.
    simulated_attempt_001 = (
        delivery_time_001 - timedelta(minutes=1)
    )

    fixture_001 = {
        "fixture_id": "FIXTURE-ANOM-001",
        "anomaly_id": "ANOM-001",
        "anomaly_type": "PAYOUT_BEFORE_DELIVERY",
        "evaluation_only": True,
        "records": {
            "payout_id": anomaly_001_candidate["payout_id"],
            "payout_line_id": anomaly_001_candidate["payout_line_id"],
            "order_line_id": anomaly_001_candidate["order_line_id"],
            "fulfillment_id": fulfillment_001["fulfillment_id"],
        },
        "expected": {
            "rule": (
                "Payout must not be attempted before the "
                "seven-day hold expires."
            ),
            "delivery_at": iso(delivery_time_001),
            "eligible_after": iso(eligible_after_001),
        },
        "observed": {
            "simulated_payout_attempt_at": iso(
                simulated_attempt_001
            ),
        },
    }

    # --------------------------------------------------------
    # ANOM-002: DUPLICATE COMMISSION
    # --------------------------------------------------------

    anomaly_002_candidate = next(
        (
            row
            for row in payout_lines
            if Decimal(row["commission_amount"]) > 0
        ),
        None,
    )

    if anomaly_002_candidate is None:
        raise ValueError(
            "Unable to create ANOM-002 fixture: "
            "no positive commission payout line found."
        )

    commission_once = money(
        anomaly_002_candidate["commission_amount"]
    )

    commission_twice = money(
        commission_once * Decimal("2")
    )

    fixture_002 = {
        "fixture_id": "FIXTURE-ANOM-002",
        "anomaly_id": "ANOM-002",
        "anomaly_type": "DUPLICATE_COMMISSION",
        "evaluation_only": True,
        "records": {
            "payout_id": anomaly_002_candidate["payout_id"],
            "payout_line_id": anomaly_002_candidate["payout_line_id"],
            "order_line_id": anomaly_002_candidate["order_line_id"],
        },
        "expected": {
            "commission_amount": str(commission_once),
            "application_count": 1,
        },
        "observed": {
            "commission_amount": str(commission_twice),
            "application_count": 2,
        },
    }

    # --------------------------------------------------------
    # ANOM-003: SUSPENDED SELLER WITH ACTIVE LISTING
    # --------------------------------------------------------

    anomaly_003_candidate = next(
        (
            row
            for row in listings
            if (
                row["status"] == "ACTIVE"
                and row["seller_id"] in seller_by_id
                and seller_by_id[row["seller_id"]]["status"] == "SUSPENDED"
            )
        ),
        None,
    )

    if anomaly_003_candidate is None:
        raise ValueError(
            "Unable to create ANOM-003 fixture: "
            "no active listing belonging to a suspended seller found."
        )

    seller_003 = seller_by_id[
        anomaly_003_candidate["seller_id"]
    ]

    fixture_003 = {
        "fixture_id": "FIXTURE-ANOM-003",
        "anomaly_id": "ANOM-003",
        "anomaly_type": "SUSPENDED_SELLER_ACTIVE_LISTING",
        "evaluation_only": True,
        "records": {
            "seller_id": seller_003["seller_id"],
            "listing_id": anomaly_003_candidate["listing_id"],
        },
        "expected": {
            "seller_status": "SUSPENDED",
            "listing_status": "INACTIVE",
        },
        "observed": {
            "seller_status": seller_003["status"],
            "listing_status": anomaly_003_candidate["status"],
        },
    }

    # --------------------------------------------------------
    # ANOM-004: LOST DISPUTE NOT DEDUCTED
    # --------------------------------------------------------

    anomaly_004_candidate = None

    for dispute in disputes:

        if (
            dispute["status"] == "LOST"
            and dispute["dispute_type"] in ("REFUND", "CHARGEBACK")
            and dispute["order_line_id"] in payout_line_by_order_line
        ):

            candidate_line = payout_line_by_order_line[
                dispute["order_line_id"]
            ]

            actual_deduction = money(
                Decimal(candidate_line["refund_amount"])
                + Decimal(candidate_line["chargeback_amount"])
            )

            if actual_deduction > 0:
                anomaly_004_candidate = (
                    dispute,
                    candidate_line,
                    actual_deduction,
                )
                break

    if anomaly_004_candidate is None:
        raise ValueError(
            "Unable to create ANOM-004 fixture: "
            "no lost refund/chargeback with a positive payout deduction found."
        )

    dispute_004, payout_line_004, deduction_004 = (
        anomaly_004_candidate
    )

    fixture_004 = {
        "fixture_id": "FIXTURE-ANOM-004",
        "anomaly_id": "ANOM-004",
        "anomaly_type": "LOST_DISPUTE_NOT_DEDUCTED",
        "evaluation_only": True,
        "records": {
            "dispute_id": dispute_004["dispute_id"],
            "payout_id": payout_line_004["payout_id"],
            "payout_line_id": payout_line_004["payout_line_id"],
            "order_line_id": dispute_004["order_line_id"],
        },
        "expected": {
            "dispute_status": "LOST",
            "dispute_type": dispute_004["dispute_type"],
            "deduction_amount": str(deduction_004),
        },
        "observed": {
            "deduction_amount": "0.00",
        },
    }

    # --------------------------------------------------------
    # ANOM-005: PAYOUT HEADER MISMATCH
    # --------------------------------------------------------

    anomaly_005_candidate = next(
        (
            payout
            for payout in payouts
            if any(
                row["payout_id"] == payout["payout_id"]
                for row in payout_lines
            )
        ),
        None,
    )

    if anomaly_005_candidate is None:
        raise ValueError(
            "Unable to create ANOM-005 fixture: "
            "no payout with payout lines found."
        )

    payout_005_lines = [
        row
        for row in payout_lines
        if row["payout_id"] == anomaly_005_candidate["payout_id"]
    ]

    calculated_line_total_005 = money(
        sum(
            (
                Decimal(row["net_amount"])
                for row in payout_005_lines
            ),
            Decimal("0.00"),
        )
    )

    actual_header_005 = money(
        anomaly_005_candidate["total_amount"]
    )

    simulated_header_005 = money(
        actual_header_005 + Decimal("1.00")
    )

    fixture_005 = {
        "fixture_id": "FIXTURE-ANOM-005",
        "anomaly_id": "ANOM-005",
        "anomaly_type": "PAYOUT_HEADER_MISMATCH",
        "evaluation_only": True,
        "records": {
            "payout_id": anomaly_005_candidate["payout_id"],
            "payout_line_ids": [
                row["payout_line_id"]
                for row in payout_005_lines
            ],
        },
        "expected": {
            "header_amount": str(actual_header_005),
            "line_total": str(calculated_line_total_005),
        },
        "observed": {
            "header_amount": str(simulated_header_005),
        },
    }

    # --------------------------------------------------------
    # Combine all five fixtures.
    # --------------------------------------------------------

    anomaly_fixtures = {
        "schema_version": "1.0",
        "project": "MarketGuard",
        "seed": seed,
        "scale": scale,
        "reference_time": iso(NOW),
        "fixture_count": 5,
        "fixtures": [
            fixture_001,
            fixture_002,
            fixture_003,
            fixture_004,
            fixture_005,
        ],
    }

    # ========================================================
    # 13. PREPARE ALL OPERATIONAL TABLES
    # ========================================================

    tables = {

        "sellers": sellers,

        "product_listings": listings,

        "orders": orders,

        "order_lines": order_lines,

        "order_sellers": order_sellers,

        "fulfillments": fulfillments,

        "customer_reviews": reviews,

        "disputes": disputes,

        "commission_rules": commission_rules,

        "payouts": payouts,

        "payout_lines": payout_lines,

        "seller_status_history": seller_history,

        "fulfillment_events": fulfillment_events,

        "dispute_events": dispute_events,

        "payout_events": payout_events,
    }

    # ========================================================
    # 14. EXPORT CSV FILES AND GENERATE CHECKSUMS
    # ========================================================

    print("Exporting CSV files...")

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    GROUND_TRUTH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    MANIFEST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    checksums = {}

    # Export operational tables.
    for table_name, rows in tables.items():

        write_csv(table_name, rows)

        file_path = DATA_DIR / f"{table_name}.csv"

        checksums[f"{table_name}.csv"] = calculate_checksum(
            file_path
        )

    # Export ground truth CSV.
    write_csv("ground_truth", ground_truth)

    ground_truth_csv = DATA_DIR / "ground_truth.csv"

    checksums["ground_truth.csv"] = calculate_checksum(
        ground_truth_csv
    )

    # Export ground truth JSON.
    ground_truth_json = (
        GROUND_TRUTH_DIR / "anomalies.json"
    )

    write_json(
        ground_truth_json,
        ground_truth,
    )

    checksums["anomalies.json"] = calculate_checksum(
        ground_truth_json
    )

    # Export record-level anomaly fixtures.
    fixture_json = (
        GROUND_TRUTH_DIR / "anomaly_fixtures.json"
    )

    write_json(
        fixture_json,
        anomaly_fixtures,
    )

    checksums["anomaly_fixtures.json"] = calculate_checksum(
        fixture_json
    )

    # ========================================================
    # 15. GENERATE DATA GENERATION MANIFEST
    # ========================================================

    summary = {

        "project": "MarketGuard",

        "seed": seed,

        "scale": scale,

        "generated_at": iso(NOW),

        "row_counts": {
            name: len(rows)
            for name, rows in tables.items()
        },

        "ground_truth_labels": len(ground_truth),

        "anomaly_fixture_count": len(
            anomaly_fixtures["fixtures"]
        ),

        "checksums": checksums,
    }

    manifest_path = (
        MANIFEST_DIR / "generation_manifest.json"
    )

    write_json(
        manifest_path,
        summary,
    )

    # ========================================================
    # 16. DISPLAY GENERATION SUMMARY
    # ========================================================

    print("\n" + "=" * 55)

    print("MARKETGUARD DATA GENERATION COMPLETED")

    print("=" * 55)

    print(f"Scale: {scale}")

    print(f"Seed: {seed}")

    print(f"Reference time: {iso(NOW)}")

    print("-" * 55)

    for name, rows in tables.items():

        print(
            f"{name:25} {len(rows):>10,}"
        )

    print(
        f"{'ground_truth':25} {len(ground_truth):>10,}"
    )

    print(
        f"{'anomaly_fixtures':25} "
        f"{len(anomaly_fixtures['fixtures']):>10,}"
    )

    print("-" * 55)

    print(f"Manifest: {manifest_path}")

    print(f"Output directory: {DATA_DIR}")

    print(f"Fixtures: {fixture_json}")

    print("\nSHA-256 checksums generated successfully.")

    print("=" * 55)


# ============================================================
# 17. COMMAND-LINE ENTRY POINT
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Generate deterministic MarketGuard data."
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter",
        help="Dataset size: starter or full.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
        help="Random seed for reproducible data generation.",
    )

    args = parser.parse_args()

    generate(
        scale=args.scale,
        seed=args.seed,
    )


if __name__ == "__main__":

    main()
