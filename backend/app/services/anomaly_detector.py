from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from backend.app.models import (
    CommissionRule,
    Dispute,
    Fulfillment,
    Order,
    OrderLine,
    Payout,
    PayoutLine,
    ProductListing,
    Seller,
)


# ------------------------------------------------------------
# MONEY HELPER
# ------------------------------------------------------------

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal) -> Decimal:
    """Round monetary values to two decimal places."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


# ------------------------------------------------------------
# ANOMALY RESULT HELPER
# ------------------------------------------------------------

def create_anomaly(
    anomaly_type: str,
    severity: str,
    title: str,
    description: str,
    records: dict,
    expected: dict,
    observed: dict,
    recommendation: str,
) -> dict:
    """Create a consistent anomaly result."""

       

    record_key = (
        records.get("listing_id")
        or records.get("payout_line_id")
        or records.get("dispute_id")
        or records.get("payout_id")
        or records.get("order_line_id")
        or "UNKNOWN"
    )

    return {
        "anomaly_id": f"{anomaly_type}-{record_key}",
        "anomaly_type": anomaly_type,
        "severity": severity,
        "title": title,
        "description": description,
        "records": records,
        "expected": expected,
        "observed": observed,
        "recommendation": recommendation,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


# ------------------------------------------------------------
# MAIN ANOMALY DETECTOR
# ------------------------------------------------------------

def scan_anomalies(db: Session) -> list[dict]:
    """
    Scan operational PostgreSQL data for five MarketGuard
    marketplace anomalies.

    Evaluation-only ground-truth fixtures are deliberately
    not read by this function.
    """

    anomalies = []

    # ========================================================
    # ANOM-001: PAYOUT BEFORE SEVEN-DAY DELIVERY HOLD
    # ========================================================

    payout_records = (
        db.query(PayoutLine, Payout, Fulfillment)
        .join(Payout, PayoutLine.payout_id == Payout.payout_id)
        .join(
            Fulfillment,
            PayoutLine.order_line_id == Fulfillment.order_line_id,
        )
        .filter(
            Fulfillment.status == "DELIVERED",
            Fulfillment.delivered_at.isnot(None),
            Payout.payout_date.isnot(None),
        )
        .all()
    )

    for payout_line, payout, fulfillment in payout_records:

        eligible_after = fulfillment.delivered_at + timedelta(days=7)

        if payout.payout_date < eligible_after:

            anomalies.append(
                create_anomaly(
                    anomaly_type="PAYOUT_BEFORE_DELIVERY",
                    severity="CRITICAL",
                    title="Payout processed before delivery hold expired",
                    description=(
                        "A payout was recorded before the seven-day "
                        "post-delivery holding period expired."
                    ),
                    records={
                        "payout_id": payout.payout_id,
                        "payout_line_id": payout_line.payout_line_id,
                        "order_line_id": payout_line.order_line_id,
                        "fulfillment_id": fulfillment.fulfillment_id,
                    },
                    expected={
                        "eligible_after": eligible_after.isoformat(),
                    },
                    observed={
                        "payout_date": payout.payout_date.isoformat(),
                        "payout_status": payout.status,
                    },
                    recommendation=(
                        "Verify the payout transaction and enforce the "
                        "seven-day delivery hold before releasing funds."
                    ),
                )
            )

    # ========================================================
    # ANOM-002: COMMISSION AMOUNT HIGHER THAN EXPECTED
    # ========================================================

    commission_records = (
        db.query(PayoutLine, OrderLine, Order)
        .join(
            OrderLine,
            PayoutLine.order_line_id == OrderLine.order_line_id,
        )
        .join(Order, OrderLine.order_id == Order.order_id)
        .all()
    )

    commission_rules_cache = {}

    for payout_line, order_line, order in commission_records:

        seller_id = order_line.seller_id

        if seller_id not in commission_rules_cache:
            commission_rules_cache[seller_id] = (
                db.query(CommissionRule)
                .filter(CommissionRule.seller_id == seller_id)
                .all()
            )

        applicable_rule = None

        for rule in commission_rules_cache[seller_id]:

            if (
                order.order_date >= rule.effective_from
                and (
                    rule.effective_to is None
                    or order.order_date < rule.effective_to
                )
            ):
                applicable_rule = rule
                break

        if applicable_rule is None:
            continue

        expected_commission = money(
            payout_line.gross_amount
            * applicable_rule.commission_percentage
            / Decimal("100")
        )

        observed_commission = money(payout_line.commission_amount)

        # A higher-than-expected commission can indicate
        # duplicate commission application.
        if observed_commission > expected_commission + CENT:

            anomalies.append(
                create_anomaly(
                    anomaly_type="DUPLICATE_COMMISSION",
                    severity="HIGH",
                    title="Commission amount exceeds expected value",
                    description=(
                        "The recorded commission is greater than the "
                        "commission calculated using the applicable "
                        "seller commission rule."
                    ),
                    records={
                        "payout_id": payout_line.payout_id,
                        "payout_line_id": payout_line.payout_line_id,
                        "order_line_id": order_line.order_line_id,
                        "seller_id": seller_id,
                        "commission_rule_id": (
                            applicable_rule.commission_rule_id
                        ),
                    },
                    expected={
                        "commission_percentage": str(
                            applicable_rule.commission_percentage
                        ),
                        "commission_amount": str(expected_commission),
                    },
                    observed={
                        "commission_amount": str(observed_commission),
                        "gross_amount": str(payout_line.gross_amount),
                    },
                    recommendation=(
                        "Review the commission calculation and payout "
                        "ledger. Check whether commission was applied "
                        "more than once."
                    ),
                )
            )

    # ========================================================
    # ANOM-003: SUSPENDED SELLER WITH ACTIVE LISTING
    # ========================================================

    suspended_listings = (
        db.query(Seller, ProductListing)
        .join(
            ProductListing,
            Seller.seller_id == ProductListing.seller_id,
        )
        .filter(
            Seller.status == "SUSPENDED",
            ProductListing.status == "ACTIVE",
        )
        .all()
    )

    for seller, listing in suspended_listings:

        anomalies.append(
            create_anomaly(
                anomaly_type="SUSPENDED_SELLER_ACTIVE_LISTING",
                severity="HIGH",
                title="Suspended seller has an active product listing",
                description=(
                    "A seller whose account is suspended still has "
                    "a product listing marked as active."
                ),
                records={
                    "seller_id": seller.seller_id,
                    "listing_id": listing.listing_id,
                },
                expected={
                    "seller_status": "SUSPENDED",
                    "listing_status": "INACTIVE",
                },
                observed={
                    "seller_status": seller.status,
                    "listing_status": listing.status,
                    "product_name": listing.product_name,
                },
                recommendation=(
                    "Deactivate the listing and review seller "
                    "suspension enforcement."
                ),
            )
        )

    # ========================================================
    # ANOM-004: LOST DISPUTE NOT FULLY DEDUCTED
    # ========================================================

    lost_dispute_records = (
        db.query(Dispute, PayoutLine)
        .join(
            PayoutLine,
            Dispute.order_line_id == PayoutLine.order_line_id,
        )
        .filter(
            Dispute.status == "LOST",
            Dispute.dispute_type.in_(["REFUND", "CHARGEBACK"]),
        )
        .all()
    )

    for dispute, payout_line in lost_dispute_records:

        remaining_balance = money(
            max(
                payout_line.gross_amount - payout_line.commission_amount,
                ZERO,
            )
        )

        expected_deduction = money(
            min(dispute.amount, remaining_balance)
        )

        if dispute.dispute_type == "REFUND":
            observed_deduction = money(payout_line.refund_amount)
        else:
            observed_deduction = money(payout_line.chargeback_amount)

        if observed_deduction + CENT < expected_deduction:

            anomalies.append(
                create_anomaly(
                    anomaly_type="LOST_DISPUTE_NOT_DEDUCTED",
                    severity="CRITICAL",
                    title="Lost dispute deduction is missing or incomplete",
                    description=(
                        "A lost refund or chargeback dispute was not "
                        "fully reflected in its associated payout line."
                    ),
                    records={
                        "dispute_id": dispute.dispute_id,
                        "payout_id": payout_line.payout_id,
                        "payout_line_id": payout_line.payout_line_id,
                        "order_line_id": dispute.order_line_id,
                        "dispute_type": dispute.dispute_type,
                    },
                    expected={
                        "dispute_status": "LOST",
                        "deduction_amount": str(expected_deduction),
                    },
                    observed={
                        "deduction_amount": str(observed_deduction),
                    },
                    recommendation=(
                        "Reconcile the dispute with the payout ledger "
                        "and apply the missing refund or chargeback "
                        "deduction."
                    ),
                )
            )

    # ========================================================
    # ANOM-005: PAYOUT HEADER DOES NOT MATCH PAYOUT LINES
    # ========================================================

    payouts = db.query(Payout).all()

    for payout in payouts:

        payout_lines = (
            db.query(PayoutLine)
            .filter(PayoutLine.payout_id == payout.payout_id)
            .all()
        )

        if not payout_lines:
            continue

        calculated_total = money(
            sum(
                (line.net_amount for line in payout_lines),
                ZERO,
            )
        )

        header_total = money(payout.total_amount)

        if abs(header_total - calculated_total) > CENT:

            anomalies.append(
                create_anomaly(
                    anomaly_type="PAYOUT_HEADER_MISMATCH",
                    severity="HIGH",
                    title="Payout header does not match payout lines",
                    description=(
                        "The payout header amount differs from the "
                        "sum of its individual payout line net amounts."
                    ),
                    records={
                        "payout_id": payout.payout_id,
                        "payout_line_ids": [
                            line.payout_line_id for line in payout_lines
                        ],
                    },
                    expected={
                        "header_amount": str(calculated_total),
                    },
                    observed={
                        "header_amount": str(header_total),
                    },
                    recommendation=(
                        "Reconcile the payout header against all "
                        "associated payout lines before settlement."
                    ),
                )
            )

    return anomalies