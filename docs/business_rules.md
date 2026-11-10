# MarketGuard Business Rules

## 1. Purpose

This document defines the business rules used by MarketGuard to monitor marketplace seller operations, fulfillment compliance, disputes, commissions, and payouts.

The rules identify operational and financial inconsistencies using records stored in PostgreSQL.

The anomaly detection implementation is located at:

`backend/app/services/anomaly_detector.py`

MarketGuard currently implements five mandatory anomaly detection rules.

## 2. Financial and Operational Principles

The following principles guide the business rules:

1. Seller compliance must be maintained throughout marketplace operations.
2. Suspended sellers should not have active product listings.
3. Seller payouts must respect delivery and the applicable payment hold period.
4. Commission calculations must follow the effective-dated commission rules.
5. Refunds and chargebacks must be reflected in payout deductions.
6. Payout headers must reconcile with their associated payout lines.
7. Financial calculations must use decimal-based monetary values.
8. Anomaly findings must identify the affected operational records and explain the expected and observed values.

## 3. Business Rule 1: Payout Before Delivery Hold

**Rule ID:** MG-001

**Anomaly type:** `PAYOUT_BEFORE_DELIVERY`

**Purpose:**

Prevent seller payouts from being processed before an order line satisfies the delivery hold requirement.

### Business condition

A payout must not be made before the associated order line has been delivered and the seven-day delivery hold period has expired.

### Detection logic

The detector evaluates the relationship between:

- Payout
- Payout line
- Fulfillment
- Order line

It checks records with available payout and delivery timestamps.

The eligibility timestamp is calculated as:

```text
Eligible After = Delivered At + 7 Days
```

An anomaly is identified when:

```text
Payout Date < Eligible After
```

### Example

| Field | Value |
|---|---|
| Delivered at | 12 September, 12:00 |
| Hold period | 7 days |
| Eligible after | 19 September, 12:00 |
| Payout attempted | 12 September, 11:59 |

**Expected:** Payout should not occur before 19 September, 12:00.

**Observed:** Payout date is earlier than the eligibility timestamp.

**Recommended action:**

- Hold the affected payout.
- Verify the fulfillment delivery timestamp.
- Recalculate the payout eligibility date.
- Release the payout only after the hold requirement is satisfied.

## 4. Business Rule 2: Duplicate Commission

**Rule ID:** MG-002

**Anomaly type:** `DUPLICATE_COMMISSION`

**Purpose:**

Identify commission deductions that exceed the expected commission for an eligible order-line basis.

### Business condition

A seller commission must be calculated using the applicable commission percentage for the order date.

Commission must not be over-applied to the same eligible financial basis.

### Detection logic

The detector evaluates:

- Payout line
- Order line
- Order date
- Seller commission rules

The applicable commission rule is selected using the seller and effective date.

Expected commission:

```text
Expected Commission =
    Eligible Commission Basis × Commission Percentage / 100
```

The detector compares the recorded commission against the expected amount.

An anomaly is identified when:

```text
Observed Commission > Expected Commission + 0.01
```

The one-cent allowance accounts for monetary rounding.

### Example

| Field | Value |
|---|---:|
| Expected commission | 1,163.88 |
| Observed commission | 2,327.76 |
| Difference | 1,163.88 |

**Expected:** Commission should be 1,163.88.

**Observed:** Commission recorded is 2,327.76.

**Recommended action:**

- Review the applicable commission rule.
- Verify the eligible order-line amount.
- Investigate repeated commission deductions.
- Correct the affected payout calculation.

## 5. Business Rule 3: Suspended Seller Active Listing

**Rule ID:** MG-003

**Anomaly type:** `SUSPENDED_SELLER_ACTIVE_LISTING`

**Purpose:**

Prevent suspended sellers from continuing to offer products through active marketplace listings.

### Business condition

When a seller is suspended, their active product listings should not remain available for marketplace transactions.

### Detection logic

The detector joins:

- `sellers`
- `product_listings`

It checks the following condition:

```text
Seller Status = SUSPENDED
AND
Listing Status = ACTIVE
```

When both conditions are true, the listing is flagged.

### Example

| Field | Value |
|---|---|
| Seller ID | SELL-000001 |
| Seller status | SUSPENDED |
| Listing ID | LIST-SELL-000001-000001 |
| Listing status | ACTIVE |

**Expected:** The listing should be inactive.

**Observed:** The listing remains active while the seller is suspended.

**Recommended action:**

- Deactivate the affected listing.
- Review the seller suspension status.
- Investigate why the listing remained active.
- Verify that other listings belonging to the seller are also compliant.

## 6. Business Rule 4: Lost Dispute Not Deducted

**Rule ID:** MG-004

**Anomaly type:** `LOST_DISPUTE_NOT_DEDUCTED`

**Purpose:**

Ensure that lost refund and chargeback disputes are reflected in seller settlement deductions.

### Business condition

When a dispute is lost, the applicable refund or chargeback amount must be accounted for in the associated payout line.

### Detection logic

The detector evaluates:

- Dispute
- Payout line
- Order line
- Dispute status and type
- Existing refund or chargeback deductions

The rule applies to disputes with:

```text
Dispute Status = LOST
Dispute Type = REFUND or CHARGEBACK
```

The expected deduction is calculated using:

```text
Expected Deduction =
    Minimum(
        Dispute Amount,
        Gross Amount - Commission Amount
    )
```

The expected deduction is compared with the corresponding recorded refund or chargeback amount.

An anomaly is identified when the recorded deduction is lower than the expected deduction.

### Example

| Field | Value |
|---|---:|
| Dispute status | LOST |
| Dispute type | REFUND |
| Dispute amount | 358.56 |
| Expected deduction | 358.56 |
| Observed refund deduction | 0.00 |

**Expected:** Refund deduction of 358.56.

**Observed:** No refund deduction is recorded.

**Recommended action:**

- Verify the dispute resolution.
- Review the associated payout line.
- Apply the missing refund or chargeback deduction.
- Recalculate the seller's net payout.

## 7. Business Rule 5: Payout Header Mismatch

**Rule ID:** MG-005

**Anomaly type:** `PAYOUT_HEADER_MISMATCH`

**Purpose:**

Ensure that the payout header amount reconciles with the financial totals of its associated payout lines.

### Business condition

The total payout amount must equal the sum of all associated payout-line net amounts.

### Detection logic

The detector evaluates:

- Payout header
- Associated payout lines
- Payout-line net amounts

The expected payout header is calculated as:

```text
Expected Payout Total =
    SUM(Payout Line Net Amounts)
```

The calculated amount is compared with:

```text
Observed Payout Total =
    payouts.total_amount
```

A mismatch is flagged when the two amounts differ.

### Example

| Field | Value |
|---|---:|
| Expected payout total | 333,352.02 |
| Observed payout total | 333,353.02 |
| Difference | 1.00 |

**Expected:** 333,352.02.

**Observed:** 333,353.02.

**Recommended action:**

- Recalculate the associated payout lines.
- Verify commission, refund, chargeback, and reserve deductions.
- Reconcile the payout header.
- Investigate any unexplained difference.

## 8. Payout Calculation Policy

Payout-line net amounts are derived from the following financial components:

```text
Net Payout =
    Gross Amount
    - Commission Amount
    - Refund Amount
    - Chargeback Amount
    - Reserve Amount
```

### Component definitions

| Component | Meaning |
|---|---|
| Gross amount | Eligible order-line financial amount |
| Commission amount | Marketplace commission deduction |
| Refund amount | Refund deduction |
| Chargeback amount | Chargeback deduction |
| Reserve amount | Amount withheld as a reserve |
| Net amount | Amount remaining after deductions |

The database enforces the payout-line arithmetic through a check constraint.

Commission calculations use effective-dated commission rules.

The current payout-before-delivery rule uses a seven-day hold after delivery.

**Implementation note:** The seven-day hold is currently defined in the anomaly detection service. It is not yet a configurable database or application setting.

## 9. Anomaly Output and Traceability

Each detected anomaly provides structured information, including:

- Anomaly identifier
- Anomaly type
- Severity
- Title and description
- Related operational record identifiers
- Expected values
- Observed values
- Recommended action
- Detection timestamp

The anomaly detection API exposes the findings through:

```text
POST /api/v1/anomalies/scan
GET  /api/v1/anomalies/summary
```

The dashboard presents anomaly counts, severity information, categories, and investigation records.

## 10. Ground Truth and Acceptance Testing

MarketGuard maintains five evaluation-only anomaly fixtures separately from operational data.

Location:

`data/ground_truth/anomaly_fixtures.json`

| Fixture ID | Anomaly Type |
|---|---|
| ANOM-001 | PAYOUT_BEFORE_DELIVERY |
| ANOM-002 | DUPLICATE_COMMISSION |
| ANOM-003 | SUSPENDED_SELLER_ACTIVE_LISTING |
| ANOM-004 | LOST_DISPUTE_NOT_DEDUCTED |
| ANOM-005 | PAYOUT_HEADER_MISMATCH |

These fixtures contain expected and observed values and references to relevant records.

They are used by the data validation and evaluation process. They are not loaded into the operational database or read directly by the anomaly detector.

Automated rule tests are maintained in:

`backend/tests/test_anomaly_detector.py`

Each of the five detection rules has an isolated test scenario.

## 11. Current Implementation Scope and Limitations

- All five anomaly detection rules are implemented.
- All five rules have isolated automated test coverage.
- The operational starter dataset currently produces seven suspended-seller active-listing anomalies.
- The other four rules do not currently produce findings in the generated operational dataset.
- Ground-truth fixtures are separate from operational records.
- The payout hold period is currently seven days.
- Severity values are assigned by the detection implementation.
- Recommendations are returned with detected anomaly records.

This document describes the current implementation. Any future changes to business policy, detection thresholds, financial calculations, or severity assignments must be reflected in both the implementation and this document.