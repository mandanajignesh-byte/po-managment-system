-- ============================================================
-- PO Management System – PostgreSQL Schema
-- IV Innovations Pvt Ltd Assignment
-- ============================================================

-- Drop existing tables (safe re-run)
DROP TABLE IF EXISTS po_line_items CASCADE;
DROP TABLE IF EXISTS purchase_orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS vendors CASCADE;
DROP TYPE IF EXISTS postatus;

-- Status ENUM
CREATE TYPE postatus AS ENUM ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'DELIVERED');

-- ─── Vendors ─────────────────────────────────────────────────────────────────
CREATE TABLE vendors (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    contact     VARCHAR(255) NOT NULL,
    email       VARCHAR(255),
    rating      FLOAT DEFAULT 3.0 CHECK (rating BETWEEN 1.0 AND 5.0),
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ─── Products ────────────────────────────────────────────────────────────────
CREATE TABLE products (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    sku          VARCHAR(100) NOT NULL UNIQUE,
    category     VARCHAR(100) DEFAULT 'General',
    unit_price   FLOAT NOT NULL CHECK (unit_price > 0),
    stock_level  INTEGER DEFAULT 0 CHECK (stock_level >= 0),
    description  TEXT,
    created_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_products_sku ON products(sku);

-- ─── Purchase Orders ──────────────────────────────────────────────────────────
CREATE TABLE purchase_orders (
    id            SERIAL PRIMARY KEY,
    reference_no  VARCHAR(50) NOT NULL UNIQUE,
    vendor_id     INTEGER NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
    subtotal      FLOAT NOT NULL DEFAULT 0,
    tax_amount    FLOAT NOT NULL DEFAULT 0,   -- 5% of subtotal
    total_amount  FLOAT NOT NULL DEFAULT 0,   -- subtotal + tax_amount
    status        postatus NOT NULL DEFAULT 'DRAFT',
    notes         TEXT,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_po_vendor ON purchase_orders(vendor_id);
CREATE INDEX idx_po_status  ON purchase_orders(status);

-- ─── PO Line Items ────────────────────────────────────────────────────────────
CREATE TABLE po_line_items (
    id                  SERIAL PRIMARY KEY,
    purchase_order_id   INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id          INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    unit_price          FLOAT NOT NULL,     -- snapshot of price at order time
    line_total          FLOAT NOT NULL      -- quantity * unit_price
);
CREATE INDEX idx_line_items_po      ON po_line_items(purchase_order_id);
CREATE INDEX idx_line_items_product ON po_line_items(product_id);

-- ─── Seed Data ────────────────────────────────────────────────────────────────
INSERT INTO vendors (name, contact, email, rating) VALUES
    ('Tata Supplies Co.',    '+91-98765-43210', 'tata@supplies.in',    4.5),
    ('Reliance Procurement', '+91-87654-32109', 'proc@reliance.in',    4.0),
    ('Infosys Tech Parts',   '+91-76543-21098', 'parts@infosys.in',    4.8),
    ('Wipro Components',     '+91-65432-10987', 'components@wipro.in', 3.5);

INSERT INTO products (name, sku, category, unit_price, stock_level) VALUES
    ('Intel Core i9 Processor',   'CPU-I9-001',  'Electronics', 45000.00,  50),
    ('Samsung 32GB RAM DDR5',      'RAM-S32-002', 'Electronics', 12000.00, 200),
    ('Western Digital 2TB SSD',   'SSD-WD2-003', 'Storage',      8500.00, 150),
    ('Logitech MX Keys Keyboard', 'KBD-LG-004',  'Peripherals',  9500.00,  75),
    ('Dell 27" 4K Monitor',       'MON-DL27-005','Display',     35000.00,  30),
    ('Cisco Network Switch 24P',  'NET-CS24-006','Networking',  28000.00,  20);

-- ─── Audit Logs ────────────────────────────────────────────────────────────
CREATE TABLE audit_logs (
    id            SERIAL PRIMARY KEY,
    entity_type   VARCHAR(50) NOT NULL,
    entity_id     INTEGER NOT NULL,
    action        VARCHAR(50) NOT NULL,
    old_value     TEXT,
    new_value     TEXT,
    performed_by  VARCHAR(255) DEFAULT 'system',
    ip_address    VARCHAR(45),
    created_at    TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_action  ON audit_logs(action);
