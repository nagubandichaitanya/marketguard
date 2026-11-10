
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


# ============================================================
# 1. SELLER
# ============================================================

class Seller(Base):
    __tablename__ = "sellers"

    seller_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    seller_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'AT_RISK', 'SUSPENDED', 'INACTIVE')",
            name="ck_seller_status",
        ),
    )


# ============================================================
# 2. PRODUCT LISTING
# ============================================================

class ProductListing(Base):
    __tablename__ = "product_listings"

    listing_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    seller_id: Mapped[str] = mapped_column(
        ForeignKey("sellers.seller_id"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_listing_price"),
        CheckConstraint("stock_quantity >= 0", name="ck_listing_stock"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED', 'OUT_OF_STOCK')",
            name="ck_listing_status",
        ),
        UniqueConstraint(
            "listing_id",
            "seller_id",
            name="uq_listing_seller",
        ),
        Index("ix_listing_seller_id", "seller_id"),
    )


# ============================================================
# 3. ORDER
# ============================================================

class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(30), nullable=False)
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(25), default="PLACED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_order_total"),
        CheckConstraint(
            "status IN ('PLACED', 'CONFIRMED', 'PROCESSING', "
            "'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED')",
            name="ck_order_status",
        ),
    )


# ============================================================
# 4. ORDER LINE
# ============================================================

class OrderLine(Base):
    __tablename__ = "order_lines"

    order_line_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"), nullable=False
    )
    listing_id: Mapped[str] = mapped_column(
        String(40), nullable=False
    )

    seller_id: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_line_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_order_line_unit_price"),
        CheckConstraint("line_total >= 0", name="ck_order_line_total"),
        CheckConstraint(
            "line_total = quantity * unit_price",
            name="ck_order_line_arithmetic",
        ),
        ForeignKeyConstraint(
            ["listing_id", "seller_id"],
            ["product_listings.listing_id", "product_listings.seller_id"],
            name="fk_order_line_listing_seller",
        ),
        Index("ix_order_line_order_id", "order_id"),
        Index("ix_order_line_seller_id", "seller_id"),
    )


# ============================================================
# 5. ORDER-SELLER BRIDGE
# Supports one order containing products from multiple sellers.
# ============================================================

class OrderSeller(Base):
    __tablename__ = "order_sellers"

    order_seller_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"), nullable=False
    )
    seller_id: Mapped[str] = mapped_column(
        ForeignKey("sellers.seller_id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("order_id", "seller_id", name="uq_order_seller"),
    )


# ============================================================
# 6. FULFILLMENT
# One fulfillment record per order line in this initial design.
# ============================================================

class Fulfillment(Base):
    __tablename__ = "fulfillments"

    fulfillment_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    order_line_id: Mapped[str] = mapped_column(
        ForeignKey("order_lines.order_line_id"), unique=True, nullable=False
    )
    seller_id: Mapped[str] = mapped_column(
        ForeignKey("sellers.seller_id"), nullable=False
    )
    carrier: Mapped[str | None] = mapped_column(String(100))
    tracking_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(25), default="PENDING", nullable=False)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_delivery_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PACKED', 'SHIPPED', "
            "'IN_TRANSIT', 'DELIVERED', 'FAILED', 'RETURNED')",
            name="ck_fulfillment_status",
        ),
    )


# ============================================================
# 7. CUSTOMER REVIEW
# ============================================================

class CustomerReview(Base):
    __tablename__ = "customer_reviews"

    review_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    order_line_id: Mapped[str] = mapped_column(
        ForeignKey("order_lines.order_line_id"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(String(30), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating"),
        UniqueConstraint(
            "order_line_id", "customer_id", name="uq_review_customer_order_line"
        ),
    )


# ============================================================
# 8. DISPUTE
# ============================================================

class Dispute(Base):
    __tablename__ = "disputes"

    dispute_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    order_line_id: Mapped[str] = mapped_column(
        ForeignKey("order_lines.order_line_id"), nullable=False
    )
    seller_id: Mapped[str] = mapped_column(
        ForeignKey("sellers.seller_id"), nullable=False
    )
    dispute_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(25), default="OPEN", nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_dispute_amount"),
        CheckConstraint(
            "dispute_type IN ('REFUND', 'CHARGEBACK', 'NOT_RECEIVED', "
            "'DAMAGED', 'OTHER')",
            name="ck_dispute_type",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'UNDER_REVIEW', 'WON', 'LOST', 'RESOLVED')",
            name="ck_dispute_status",
        ),
    )


# ============================================================
# 9. COMMISSION RULE
# Effective-dated commission configuration.
# ============================================================

class CommissionRule(Base):
    __tablename__ = "commission_rules"

    commission_rule_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    seller_id: Mapped[str] = mapped_column(
        ForeignKey("sellers.seller_id"), nullable=False
    )
    commission_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "commission_percentage BETWEEN 0 AND 100",
            name="ck_commission_percentage",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_commission_dates",
        ),
        Index("ix_commission_seller_effective", "seller_id", "effective_from"),
    )


# ============================================================
# 10. PAYOUT
# ============================================================

class Payout(Base):
    __tablename__ = "payouts"

    payout_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    seller_id: Mapped[str] = mapped_column(
        ForeignKey("sellers.seller_id"), nullable=False
    )
    payout_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_payout_total"),
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'PAID', 'FAILED', 'CANCELLED')",
            name="ck_payout_status",
        ),
    )


# ============================================================
# 11. PAYOUT LINE
# ============================================================

class PayoutLine(Base):
    __tablename__ = "payout_lines"

    payout_line_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    payout_id: Mapped[str] = mapped_column(
        ForeignKey("payouts.payout_id"), nullable=False
    )
    order_line_id: Mapped[str] = mapped_column(
        ForeignKey("order_lines.order_line_id"), nullable=False
    )
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    chargeback_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    reserve_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "payout_id", "order_line_id", name="uq_payout_order_line"
        ),
        CheckConstraint("gross_amount >= 0", name="ck_payout_line_gross"),
        CheckConstraint("commission_amount >= 0", name="ck_payout_line_commission"),
        CheckConstraint("refund_amount >= 0", name="ck_payout_line_refund"),
        CheckConstraint("chargeback_amount >= 0", name="ck_payout_line_chargeback"),
        CheckConstraint("reserve_amount >= 0", name="ck_payout_line_reserve"),
        CheckConstraint(
            "net_amount = gross_amount - commission_amount "
            "- refund_amount - chargeback_amount - reserve_amount",
            name="ck_payout_line_net_arithmetic",
        ),
    )


# ============================================================
# 12. SELLER STATUS HISTORY
# ============================================================

class SellerStatusHistory(Base):
    __tablename__ = "seller_status_history"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[str] = mapped_column(
        ForeignKey("sellers.seller_id"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ============================================================
# 13. FULFILLMENT EVENT HISTORY
# ============================================================

class FulfillmentEvent(Base):
    __tablename__ = "fulfillment_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fulfillment_id: Mapped[str] = mapped_column(
        ForeignKey("fulfillments.fulfillment_id"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(25))
    new_status: Mapped[str] = mapped_column(String(25), nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[dict | None] = mapped_column(JSON)


# ============================================================
# 14. DISPUTE EVENT HISTORY
# ============================================================

class DisputeEvent(Base):
    __tablename__ = "dispute_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dispute_id: Mapped[str] = mapped_column(
        ForeignKey("disputes.dispute_id"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(25))
    new_status: Mapped[str] = mapped_column(String(25), nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    details: Mapped[dict | None] = mapped_column(JSON)


# ============================================================
# 15. PAYOUT EVENT HISTORY
# ============================================================

class PayoutEvent(Base):
    __tablename__ = "payout_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payout_id: Mapped[str] = mapped_column(
        ForeignKey("payouts.payout_id"), nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    details: Mapped[dict | None] = mapped_column(JSON)
