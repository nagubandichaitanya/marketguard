# Business Rules

Exact thresholds and policy parameters will be documented and configurable. The following
five negative scenarios are mandatory acceptance cases:

1. Payout attempted before delivery or hold release.
2. Commission applied more than once to the same eligible basis.
3. Suspended seller continues listing.
4. Dispute/chargeback amount is omitted from settlement deductions.
5. Payout header total does not reconcile to its payout lines.

Payout calculations must be derived from order-line value, effective-dated commission
rules, refunds, chargebacks, and reserve movements. A payout must not be eligible until
delivery and the configured hold window are satisfied.
