
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.models import (
    Seller,
    ProductListing,
    Order,
    OrderLine,
    Fulfillment,
    Dispute,
    CommissionRule,
    Payout,
    PayoutLine,
)
from backend.app.services.anomaly_detector import scan_anomalies


@pytest.fixture
def db():
    """Create a fresh, isolated in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def create_base_records(
    db,
    seller_status="ACTIVE",
    commission_amount=Decimal("10.00"),
    net_amount=Decimal("90.00"),
    payout_total=Decimal("90.00"),
    payout_date=None,
):
    """Create the minimum related records shared by the anomaly tests."""

    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    seller = Seller(
        seller_id="SELLER-TEST-001",
        seller_name="Test Seller",
        email="test.seller@example.com",
        status=seller_status,
    )

    listing = ProductListing(
        listing_id="LISTING-TEST-001",
        seller_id="SELLER-TEST-001",
        product_name="Test Product",
        category="Electronics",
        price=Decimal("100.00"),
        stock_quantity=10,
        status="ACTIVE",
    )

    order = Order(
        order_id="ORDER-TEST-001",
        customer_id="CUSTOMER-TEST-001",
        order_date=now,
        total_amount=Decimal("100.00"),
        status="DELIVERED",
    )

    order_line = OrderLine(
        order_line_id="ORDERLINE-TEST-001",
        order_id="ORDER-TEST-001",
        listing_id="LISTING-TEST-001",
        seller_id="SELLER-TEST-001",
        quantity=1,
        unit_price=Decimal("100.00"),
        line_total=Decimal("100.00"),
    )

    payout = Payout(
        payout_id="PAYOUT-TEST-001",
        seller_id="SELLER-TEST-001",
        payout_date=payout_date or now + timedelta(days=10),
        total_amount=payout_total,
        status="PAID",
    )

    payout_line = PayoutLine(
        payout_line_id="PAYOUTLINE-TEST-001",
        payout_id="PAYOUT-TEST-001",
        order_line_id="ORDERLINE-TEST-001",
        gross_amount=Decimal("100.00"),
        commission_amount=commission_amount,
        refund_amount=Decimal("0.00"),
        chargeback_amount=Decimal("0.00"),
        reserve_amount=Decimal("0.00"),
        net_amount=net_amount,
    )

    db.add_all([
        seller,
        listing,
        order,
        order_line,
        payout,
        payout_line,
    ])
    db.flush()

    return {
        "seller": seller,
        "listing": listing,
        "order": order,
        "order_line": order_line,
        "payout": payout,
        "payout_line": payout_line,
        "now": now,
    }


def test_detects_payout_before_delivery_hold(db):
    records = create_base_records(
        db,
        payout_date=datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc),
    )

    fulfillment = Fulfillment(
        fulfillment_id="FULFILLMENT-TEST-001",
        order_line_id=records["order_line"].order_line_id,
        seller_id=records["seller"].seller_id,
        status="DELIVERED",
        delivered_at=records["now"],
    )

    db.add(fulfillment)
    db.commit()

    anomalies = scan_anomalies(db)

    assert any(
        item["anomaly_type"] == "PAYOUT_BEFORE_DELIVERY"
        for item in anomalies
    )


def test_detects_duplicate_commission(db):
    records = create_base_records(
        db,
        commission_amount=Decimal("20.00"),
        net_amount=Decimal("80.00"),
        payout_total=Decimal("80.00"),
    )

    rule = CommissionRule(
        commission_rule_id="RULE-TEST-001",
        seller_id=records["seller"].seller_id,
        commission_percentage=Decimal("10.00"),
        effective_from=datetime(
            2025, 12, 1, tzinfo=timezone.utc
        ),
        effective_to=None,
    )

    db.add(rule)
    db.commit()

    anomalies = scan_anomalies(db)

    assert any(
        item["anomaly_type"] == "DUPLICATE_COMMISSION"
        for item in anomalies
    )


def test_detects_suspended_seller_active_listing(db):
    create_base_records(db, seller_status="SUSPENDED")
    db.commit()

    anomalies = scan_anomalies(db)

    assert any(
        item["anomaly_type"] == "SUSPENDED_SELLER_ACTIVE_LISTING"
        for item in anomalies
    )


def test_detects_lost_dispute_not_deducted(db):
    records = create_base_records(db)

    dispute = Dispute(
        dispute_id="DISPUTE-TEST-001",
        order_line_id=records["order_line"].order_line_id,
        seller_id=records["seller"].seller_id,
        dispute_type="REFUND",
        amount=Decimal("30.00"),
        status="LOST",
        opened_at=records["now"],
        resolved_at=records["now"] + timedelta(days=2),
    )

    db.add(dispute)
    db.commit()

    anomalies = scan_anomalies(db)

    assert any(
        item["anomaly_type"] == "LOST_DISPUTE_NOT_DEDUCTED"
        for item in anomalies
    )


def test_detects_payout_header_mismatch(db):
    create_base_records(
        db,
        net_amount=Decimal("90.00"),
        payout_total=Decimal("95.00"),
    )
    db.commit()

    anomalies = scan_anomalies(db)

    assert any(
        item["anomaly_type"] == "PAYOUT_HEADER_MISMATCH"
        for item in anomalies
    )
