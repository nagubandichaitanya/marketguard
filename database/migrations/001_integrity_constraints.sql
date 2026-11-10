BEGIN;

-- Required as the target key for the composite foreign key.
ALTER TABLE product_listings
ADD CONSTRAINT uq_listing_seller
UNIQUE (listing_id, seller_id);

-- Replace separate listing and seller references with one
-- composite reference that ensures the listing belongs to that seller.
ALTER TABLE order_lines
DROP CONSTRAINT order_lines_listing_id_fkey,
DROP CONSTRAINT order_lines_seller_id_fkey;

ALTER TABLE order_lines
ADD CONSTRAINT fk_order_line_listing_seller
FOREIGN KEY (listing_id, seller_id)
REFERENCES product_listings (listing_id, seller_id);

-- Ensure line totals are mathematically correct.
ALTER TABLE order_lines
ADD CONSTRAINT ck_order_line_arithmetic
CHECK (line_total = quantity * unit_price);

-- Ensure payout line net amounts reconcile with their components.
ALTER TABLE payout_lines
ADD CONSTRAINT ck_payout_line_net_arithmetic
CHECK (
    net_amount = gross_amount
    - commission_amount
    - refund_amount
    - chargeback_amount
    - reserve_amount
);

COMMIT;