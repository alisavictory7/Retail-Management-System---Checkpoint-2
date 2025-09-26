-- db/init.sql
-- Drop tables in an order that respects foreign key constraints.
DROP TABLE IF EXISTS "FailedPaymentLog";
DROP TABLE IF EXISTS "SaleItem";
DROP TABLE IF EXISTS "Payment";
DROP TABLE IF EXISTS "Sale";
DROP TABLE IF EXISTS "Product";
DROP TABLE IF EXISTS "Admin";
DROP TABLE IF EXISTS "User";

-- Create tables

CREATE TABLE "User" (
    "userID" SERIAL PRIMARY KEY,
    "username" VARCHAR(255) UNIQUE NOT NULL,
    "passwordHash" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) UNIQUE NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE "Product" (
    "productID" SERIAL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "price" DECIMAL(10, 2) NOT NULL,
    "stock" INTEGER NOT NULL,
    "shipping_weight" DECIMAL(10, 2) NOT NULL DEFAULT 0.0,
    "discount_percent" DECIMAL(5, 2) NOT NULL DEFAULT 0.0,
    "country_of_origin" VARCHAR(255), -- New attribute
    "requires_shipping" BOOLEAN DEFAULT TRUE -- New attribute
);

CREATE TABLE "Sale" (
    "saleID" SERIAL PRIMARY KEY,
    "userID" INTEGER REFERENCES "User"("userID"),
    "sale_date" TIMESTAMP NOT NULL,
    "totalAmount" DECIMAL(10, 2) NOT NULL,
    "status" VARCHAR(50) NOT NULL
);

CREATE TABLE "Payment" (
    "paymentID" SERIAL PRIMARY KEY,
    "saleID" INTEGER REFERENCES "Sale"("saleID"),
    "payment_date" TIMESTAMP NOT NULL,
    "amount" DECIMAL(10, 2) NOT NULL,
    "status" VARCHAR(50) NOT NULL,
    "payment_type" VARCHAR(50),
    "cash_tendered" DECIMAL(10, 2),
    "card_number" VARCHAR(255),
    "card_type" VARCHAR(50),
    "card_exp_date" VARCHAR(7),
    "type" VARCHAR(50) -- New column
);

CREATE TABLE "SaleItem" (
    "saleItemID" SERIAL PRIMARY KEY,
    "saleID" INTEGER REFERENCES "Sale"("saleID"),
    "productID" INTEGER REFERENCES "Product"("productID"),
    "quantity" INTEGER NOT NULL,
    "original_unit_price" DECIMAL(10, 2) NOT NULL,
    "discount_applied" DECIMAL(10, 2) NOT NULL DEFAULT 0.0,
    "final_unit_price" DECIMAL(10, 2) NOT NULL,
    "shipping_fee_applied" DECIMAL(10, 2) NOT NULL DEFAULT 0.0, -- New attribute
    "import_duty_applied" DECIMAL(10, 2) NOT NULL DEFAULT 0.0, -- New attribute
    "subtotal" DECIMAL(10, 2) NOT NULL
);

CREATE TABLE "FailedPaymentLog" (
    "logID" SERIAL PRIMARY KEY,
    "userID" INTEGER REFERENCES "User"("userID"),
    "attempt_date" TIMESTAMP NOT NULL,
    "amount" DECIMAL(10, 2) NOT NULL,
    "payment_method" VARCHAR(50) NOT NULL,
    "reason" VARCHAR(255)
);

-- Insert sample data with new attributes
INSERT INTO "Product" ("name", "description", "price", "stock", "shipping_weight", "discount_percent", "country_of_origin", "requires_shipping") VALUES
('Laptop', 'A high-performance laptop.', 1200.00, 40, 2.5, 10.00, 'China', TRUE),
('Mouse', 'A wireless computer mouse.', 25.00, 200, 0.2, 0.00, 'USA', TRUE),
('Keyboard', 'A mechanical keyboard.', 75.00, 150, 0.8, 15.00, 'China', TRUE),
('Software License', 'A digital software license.', 300.00, 80, 0.0, 0.00, 'USA', FALSE);

INSERT INTO "User" ("username", "passwordHash", "email") VALUES
('testuser', 'pbkdf2:sha256:600000$lY1E6n8k3v9a2Z3j$c8b7c6a5b4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7', 'test@example.com'),
('john_doe', 'pbkdf2:sha256:600000$lY1E6n8k3v9a2Z3j$c8b7c6a5b4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7', 'john.doe@example.com'),
('jane_smith', 'pbkdf2:sha256:600000$lY1E6n8k3v9a2Z3j$c8b7c6a5b4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7', 'jane.smith@example.com'),
('alice_jones', 'pbkdf2:sha256:600000$lY1E6n8k3v9a2Z3j$c8b7c6a5b4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7', 'alice.jones@example.com'),
('bob_brown', 'pbkdf2:sha256:600000$lY1E6n8k3v9a2Z3j$c8b7c6a5b4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7', 'bob.brown@example.com');

ALTER TABLE "Payment" ALTER COLUMN "payment_type" DROP NOT NULL;

