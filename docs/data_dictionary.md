# Data Dictionary

The detailed field-level dictionary will be completed before schema implementation.
It will define, for every field: SQL/Python type, requiredness, allowed values, units,
uniqueness, validation, and lifecycle semantics.

Required core entities:
Seller, ProductListing, Order, OrderLine, Fulfillment, CustomerReview, Dispute,
CommissionRule, Payout, PayoutLine.

Planned supporting entities:
OrderSeller bridge, SellerStatusHistory, FulfillmentEvent, DisputeEvent, PayoutEvent,
GroundTruthAnomaly, DataGenerationRun.
