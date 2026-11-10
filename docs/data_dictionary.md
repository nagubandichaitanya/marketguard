# MarketGuard Data Dictionary

## 1. Overview

This document describes the implemented PostgreSQL database schema for MarketGuard.

The schema contains 15 operational tables covering seller management, product listings, orders, fulfillment, customer reviews, disputes, commissions, payouts, and lifecycle event histories.

The database uses SQLAlchemy ORM models and PostgreSQL data types.

### Conventions

- **PK:** Primary key.
- **FK:** Foreign key.
- **UQ:** Unique constraint.
- **NOT NULL:** Required field.
- **NULL:** Optional field.
- **Numeric(p,s):** Fixed-precision decimal, where p is total precision and s is decimal scale.
- **DateTime(timezone=True):** Timezone-aware timestamp.
- **JSON:** Structured JSON data.

Unless otherwise stated, string identifiers are application-generated identifiers.

## 2. Database Tables

### 2.1 `sellers`

Stores marketplace seller information and current account status.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| seller_id | VARCHAR(20) | Yes | PK; unique seller identifier |
| seller_name | VARCHAR(150) | Yes | Seller display name |
| email | VARCHAR(255) | Yes | UQ; seller email |
| phone | VARCHAR(20) | No | Contact number |
| city | VARCHAR(100) | No | Seller location |
| status | VARCHAR(20) | Yes | Default ACTIVE; allowed: ACTIVE, AT_RISK, SUSPENDED, INACTIVE |
| created_at | TIMESTAMP WITH TIME ZONE | Yes | Server-generated creation timestamp |

**Business constraints:**
- Seller status must be one of the four allowed values.
- Email addresses must be unique.
- Seller records are referenced by listings, orders, disputes, commission rules, payouts, and event history.

### 2.2 `product_listings`

Stores products listed by marketplace sellers.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| listing_id | VARCHAR(40) | Yes | PK |
| seller_id | VARCHAR(20) | Yes | FK → sellers.seller_id |
| product_name | VARCHAR(200) | Yes | Product name |
| category | VARCHAR(100) | Yes | Product category |
| price | NUMERIC(12,2) | Yes | Product selling price; must be >= 0 |
| stock_quantity | INTEGER | Yes | Default 0; must be >= 0 |
| status | VARCHAR(20) | Yes | Default ACTIVE; allowed: ACTIVE, INACTIVE, SUSPENDED, OUT_OF_STOCK |
| created_at | TIMESTAMP WITH TIME ZONE | Yes | Server-generated creation timestamp |

**Constraints:**
- Unique combination: listing_id + seller_id.
- Index: seller_id.
- Price and stock quantity cannot be negative.

### 2.3 `orders`

Stores marketplace customer orders.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| order_id | VARCHAR(30) | Yes | PK |
| customer_id | VARCHAR(30) | Yes | Customer identifier |
| order_date | TIMESTAMP WITH TIME ZONE | Yes | Order placement timestamp |
| total_amount | NUMERIC(14,2) | Yes | Order total; must be >= 0 |
| status | VARCHAR(25) | Yes | Default PLACED |
| created_at | TIMESTAMP WITH TIME ZONE | Yes | Server-generated creation timestamp |

**Allowed order statuses:**

PLACED, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED, RETURNED.

### 2.4 `order_lines`

Stores individual product items belonging to an order.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| order_line_id | VARCHAR(50) | Yes | PK |
| order_id | VARCHAR(30) | Yes | FK → orders.order_id |
| listing_id | VARCHAR(40) | Yes | Part of composite FK to product_listings |
| seller_id | VARCHAR(20) | Yes | Part of composite FK to product_listings |
| quantity | INTEGER | Yes | Ordered quantity; must be > 0 |
| unit_price | NUMERIC(12,2) | Yes | Price per unit; must be >= 0 |
| line_total | NUMERIC(14,2) | Yes | Quantity × unit price; must be >= 0 |

**Constraints:**
- Composite FK: (listing_id, seller_id) → product_listings(listing_id, seller_id).
- FK: order_id → orders.order_id.
- Indexes: order_id and seller_id.
- Arithmetic check: line_total = quantity × unit_price.

The composite foreign key ensures that an order line references a listing belonging to the specified seller.

### 2.5 `order_sellers`

Bridge table supporting orders containing products from multiple sellers.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| order_seller_id | INTEGER | Yes | PK |
| order_id | VARCHAR(30) | Yes | FK → orders.order_id |
| seller_id | VARCHAR(20) | Yes | FK → sellers.seller_id |

**Constraints:**
- Unique combination: order_id + seller_id.
- Prevents duplicate seller associations for the same order.

### 2.6 `fulfillments`

Stores shipment and delivery information for order lines.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| fulfillment_id | VARCHAR(60) | Yes | PK |
| order_line_id | VARCHAR(50) | Yes | FK → order_lines.order_line_id; UQ |
| seller_id | VARCHAR(20) | Yes | FK → sellers.seller_id |
| carrier | VARCHAR(100) | No | Shipping carrier |
| tracking_number | VARCHAR(100) | No | UQ; shipment tracking identifier |
| status | VARCHAR(25) | Yes | Default PENDING |
| shipped_at | TIMESTAMP WITH TIME ZONE | No | Shipment timestamp |
| expected_delivery_at | TIMESTAMP WITH TIME ZONE | No | Expected delivery timestamp |
| delivered_at | TIMESTAMP WITH TIME ZONE | No | Actual delivery timestamp |

**Allowed fulfillment statuses:**

PENDING, PACKED, SHIPPED, IN_TRANSIT, DELIVERED, FAILED, RETURNED.

**Constraints:**
- One fulfillment record per order line in the current design.
- Tracking numbers must be unique when provided.

### 2.7 `customer_reviews`

Stores customer feedback for purchased order lines.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| review_id | VARCHAR(30) | Yes | PK |
| order_line_id | VARCHAR(50) | Yes | FK → order_lines.order_line_id |
| customer_id | VARCHAR(30) | Yes | Customer identifier |
| rating | INTEGER | Yes | Rating between 1 and 5 |
| review_text | TEXT | No | Written customer feedback |
| created_at | TIMESTAMP WITH TIME ZONE | Yes | Server-generated creation timestamp |

**Constraints:**
- Rating must be between 1 and 5.
- Unique combination: order_line_id + customer_id.

### 2.8 `disputes`

Stores refund, chargeback, and other order-related disputes.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| dispute_id | VARCHAR(30) | Yes | PK |
| order_line_id | VARCHAR(50) | Yes | FK → order_lines.order_line_id |
| seller_id | VARCHAR(20) | Yes | FK → sellers.seller_id |
| dispute_type | VARCHAR(30) | Yes | Dispute category |
| amount | NUMERIC(12,2) | Yes | Disputed amount; must be > 0 |
| status | VARCHAR(25) | Yes | Default OPEN |
| opened_at | TIMESTAMP WITH TIME ZONE | Yes | Dispute opening timestamp |
| resolved_at | TIMESTAMP WITH TIME ZONE | No | Resolution timestamp |

**Allowed dispute types:**

REFUND, CHARGEBACK, NOT_RECEIVED, DAMAGED, OTHER.

**Allowed dispute statuses:**

OPEN, UNDER_REVIEW, WON, LOST, RESOLVED.

### 2.9 `commission_rules`

Stores effective-dated seller commission configuration.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| commission_rule_id | VARCHAR(30) | Yes | PK |
| seller_id | VARCHAR(20) | Yes | FK → sellers.seller_id |
| commission_percentage | NUMERIC(5,2) | Yes | Commission percentage between 0 and 100 |
| effective_from | TIMESTAMP WITH TIME ZONE | Yes | Rule start timestamp |
| effective_to | TIMESTAMP WITH TIME ZONE | No | Rule end timestamp; NULL means no specified end |

**Constraints:**
- Commission percentage must be between 0 and 100.
- effective_to must be later than effective_from when provided.
- Index: seller_id + effective_from.

### 2.10 `payouts`

Stores seller payout headers and their current processing status.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| payout_id | VARCHAR(30) | Yes | PK |
| seller_id | VARCHAR(20) | Yes | FK → sellers.seller_id |
| payout_date | TIMESTAMP WITH TIME ZONE | No | Payout processing/payment date |
| total_amount | NUMERIC(14,2) | Yes | Default 0; must be >= 0 |
| status | VARCHAR(20) | Yes | Default PENDING |

**Allowed payout statuses:**

PENDING, PROCESSING, PAID, FAILED, CANCELLED.

### 2.11 `payout_lines`

Stores the financial ledger components associated with individual order lines in a payout.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| payout_line_id | VARCHAR(40) | Yes | PK |
| payout_id | VARCHAR(30) | Yes | FK → payouts.payout_id |
| order_line_id | VARCHAR(50) | Yes | FK → order_lines.order_line_id |
| gross_amount | NUMERIC(12,2) | Yes | Gross eligible order-line amount |
| commission_amount | NUMERIC(12,2) | Yes | Marketplace commission deduction |
| refund_amount | NUMERIC(12,2) | Yes | Default 0; refund deduction |
| chargeback_amount | NUMERIC(12,2) | Yes | Default 0; chargeback deduction |
| reserve_amount | NUMERIC(12,2) | Yes | Default 0; reserve deduction |
| net_amount | NUMERIC(12,2) | Yes | Final payout-line amount |

**Constraints:**
- Unique combination: payout_id + order_line_id.
- All gross and deduction components must be non-negative.
- Net amount must equal:

`net_amount = gross_amount - commission_amount - refund_amount - chargeback_amount - reserve_amount`

**Financial precision:**

All monetary fields use fixed-precision NUMERIC types rather than floating-point types.

### 2.12 `seller_status_history`

Stores seller account status transitions.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| event_id | INTEGER | Yes | PK |
| seller_id | VARCHAR(20) | Yes | FK → sellers.seller_id |
| old_status | VARCHAR(20) | No | Previous seller status |
| new_status | VARCHAR(20) | Yes | New seller status |
| reason | TEXT | No | Reason for status change |
| event_time | TIMESTAMP WITH TIME ZONE | Yes | Server-generated event timestamp |

This table provides a historical record of seller status changes.

### 2.13 `fulfillment_events`

Stores fulfillment lifecycle transitions.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| event_id | INTEGER | Yes | PK |
| fulfillment_id | VARCHAR(60) | Yes | FK → fulfillments.fulfillment_id |
| old_status | VARCHAR(25) | No | Previous fulfillment status |
| new_status | VARCHAR(25) | Yes | New fulfillment status |
| event_time | TIMESTAMP WITH TIME ZONE | Yes | Event timestamp |
| source | VARCHAR(100) | No | Event source |
| details | JSON | No | Additional event metadata |

### 2.14 `dispute_events`

Stores dispute lifecycle transitions.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| event_id | INTEGER | Yes | PK |
| dispute_id | VARCHAR(30) | Yes | FK → disputes.dispute_id |
| old_status | VARCHAR(25) | No | Previous dispute status |
| new_status | VARCHAR(25) | Yes | New dispute status |
| event_time | TIMESTAMP WITH TIME ZONE | Yes | Event timestamp |
| details | JSON | No | Additional event metadata |

### 2.15 `payout_events`

Stores payout processing and status transitions.

| Column | SQL Type | Required | Constraints / Meaning |
|---|---|---|---|
| event_id | INTEGER | Yes | PK |
| payout_id | VARCHAR(30) | Yes | FK → payouts.payout_id |
| old_status | VARCHAR(20) | No | Previous payout status |
| new_status | VARCHAR(20) | Yes | New payout status |
| event_time | TIMESTAMP WITH TIME ZONE | Yes | Event timestamp |
| details | JSON | No | Additional event metadata |

## 3. Entity Relationships

The main database relationships are:

| Parent Table | Child Table | Relationship |
|---|---|---|
| sellers | product_listings | One-to-many |
| sellers | order_sellers | One-to-many |
| orders | order_sellers | One-to-many |
| orders | order_lines | One-to-many |
| product_listings | order_lines | One-to-many through listing_id + seller_id |
| sellers | commission_rules | One-to-many |
| sellers | payouts | One-to-many |
| sellers | disputes | One-to-many |
| sellers | fulfillments | One-to-many |
| order_lines | fulfillments | One-to-one in current schema |
| order_lines | customer_reviews | One-to-many, with a unique customer/order-line combination |
| order_lines | disputes | One-to-many |
| order_lines | payout_lines | One-to-many |
| payouts | payout_lines | One-to-many |
| sellers | seller_status_history | One-to-many |
| fulfillments | fulfillment_events | One-to-many |
| disputes | dispute_events | One-to-many |
| payouts | payout_events | One-to-many |

## 4. Status and Lifecycle Semantics

The current entity tables store the latest known status for sellers, orders, listings, fulfillments, disputes, and payouts.

Separate history tables capture relevant transitions:

- Seller changes → `seller_status_history`
- Fulfillment changes → `fulfillment_events`
- Dispute changes → `dispute_events`
- Payout changes → `payout_events`

The history tables provide an audit trail of recorded transitions. Append-only behavior is an application-level design intention; it is not enforced by a database trigger or immutable-table constraint in the current schema.

## 5. Financial Data Semantics

MarketGuard uses PostgreSQL NUMERIC columns for financial calculations.

### Payout-line calculation

```text
Net Amount =
    Gross Amount
    - Commission Amount
    - Refund Amount
    - Chargeback Amount
    - Reserve Amount
```

The database enforces this arithmetic through a check constraint.

### Commission calculation

Commission rules are associated with sellers and have effective date ranges.

The applicable commission percentage is selected based on the order date and the rule's effective period.

### Payout reconciliation

A payout header total is expected to reconcile with the sum of its associated payout-line net amounts.

This reconciliation is evaluated by the anomaly detection service.

## 6. Indexes and Uniqueness

The explicitly defined indexes and unique constraints include:

| Table | Constraint / Index |
|---|---|
| sellers | PK seller_id; unique email |
| product_listings | PK listing_id; unique listing_id + seller_id; index seller_id |
| orders | PK order_id |
| order_lines | PK order_line_id; index order_id; index seller_id |
| order_sellers | PK order_seller_id; unique order_id + seller_id |
| fulfillments | PK fulfillment_id; unique order_line_id; unique tracking_number |
| customer_reviews | PK review_id; unique order_line_id + customer_id |
| disputes | PK dispute_id |
| commission_rules | PK commission_rule_id; index seller_id + effective_from |
| payouts | PK payout_id |
| payout_lines | PK payout_line_id; unique payout_id + order_line_id |
| seller_status_history | PK event_id |
| fulfillment_events | PK event_id |
| dispute_events | PK event_id |
| payout_events | PK event_id |

## 7. Evaluation and Reproducibility Files

The following are project artifacts, not operational PostgreSQL tables.

### 7.1 Ground Truth Anomaly Fixtures

Location:

`data/ground_truth/anomaly_fixtures.json`

Contains five evaluation scenarios:

1. PAYOUT_BEFORE_DELIVERY
2. DUPLICATE_COMMISSION
3. SUSPENDED_SELLER_ACTIVE_LISTING
4. LOST_DISPUTE_NOT_DEDUCTED
5. PAYOUT_HEADER_MISMATCH

The fixtures contain record references and expected/observed values. They are kept separate from operational data and are not loaded into PostgreSQL by the standard data loader.

### 7.2 Data Generation Manifest

Location:

`data/manifests/generation_manifest.json`

Records dataset-generation metadata, including the random seed, reference time, generated table counts, and file checksums.

### 7.3 Validation Report

Location:

`reports/validation_report.json`

Contains data validation results, table counts, fixture validation information, errors, and warnings.

## 8. Current Schema Scope and Limitations

- The current implementation contains 15 operational database tables.
- Ground-truth fixtures and generation metadata are file-based artifacts.
- The current fulfillment design allows one fulfillment record per order line.
- Status check constraints are explicitly defined on the main entity tables, but not on the event-history status columns.
- Effective-dated commission rules have date checks and an index, but overlapping effective periods are not prevented by a database exclusion constraint.
- The database enforces payout-line arithmetic, while payout-header reconciliation is evaluated by the anomaly detection service.
- Cross-table business policies, such as payout eligibility and seller compliance, are evaluated by application validation and anomaly detection rather than by every individual database constraint.

This document reflects the current implemented SQLAlchemy schema and should be updated whenever the database models change.