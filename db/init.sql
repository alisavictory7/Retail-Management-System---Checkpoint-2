-- db/init.sql
-- Drop existing tables with cascade to handle dependencies
DROP TABLE IF EXISTS "FailedPaymentLog" CASCADE;
DROP TABLE IF EXISTS "SaleItem" CASCADE;
DROP TABLE IF EXISTS "Payment" CASCADE;
DROP TABLE IF EXISTS "Sale" CASCADE;
DROP TABLE IF EXISTS "Product" CASCADE;
DROP TABLE IF EXISTS "Admin" CASCADE;
DROP TABLE IF EXISTS "User" CASCADE;

-- Create tables
CREATE TABLE "User" (
    "userID" SERIAL PRIMARY KEY,
    "username" VARCHAR(255) UNIQUE NOT NULL,
    "passwordHash" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) UNIQUE NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "Admin" (
    "adminID" INTEGER PRIMARY KEY REFERENCES "User"("userID")
);

CREATE TABLE "Product" (
    "productID" SERIAL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "price" DECIMAL(10, 2) NOT NULL,
    "stock" INTEGER NOT NULL
);

CREATE TABLE "Sale" (
    "saleID" SERIAL PRIMARY KEY,
    "userID" INTEGER REFERENCES "User"("userID"),
    "sale_date" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "totalAmount" DECIMAL(10, 2) NOT NULL
);

CREATE TABLE "Payment" (
    "paymentID" SERIAL PRIMARY KEY,
    "saleID" INTEGER REFERENCES "Sale"("saleID"),
    "payment_date" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "amount" DECIMAL(10, 2) NOT NULL,
    "payment_method" VARCHAR(50),
    "status" VARCHAR(50)
);

CREATE TABLE "SaleItem" (
    "saleItemID" SERIAL PRIMARY KEY,
    "saleID" INTEGER REFERENCES "Sale"("saleID"),
    "productID" INTEGER REFERENCES "Product"("productID"),
    "quantity" INTEGER NOT NULL,
    "unit_price" DECIMAL(10, 2) NOT NULL,
    "subtotal" DECIMAL(10, 2) NOT NULL
);

CREATE TABLE "FailedPaymentLog" (
    "logID" SERIAL PRIMARY KEY,
    "userID" INTEGER REFERENCES "User"("userID"),
    "attempt_date" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "amount" DECIMAL(10, 2),
    "payment_method" VARCHAR(50),
    "reason" TEXT
);

-- Insert sample data
INSERT INTO "Product" ("name", "description", "price", "stock") VALUES
('Laptop', 'A high-performance laptop.', 1200.00, 40),
('Mouse', 'A wireless mouse.', 25.00, 150),
('Keyboard', 'A mechanical keyboard.', 75.00, 135),
('Monitor', 'A 27-inch 4K monitor.', 300.00, 80);

-- --- CHANGE HIGHLIGHT: Added more dummy user accounts ---
INSERT INTO "User" ("username", "passwordHash", "email") VALUES
('test_user', 'pbkdf2:sha256:600000$8n8d...$c7b...', 'test@example.com'),
('john_doe', 'pbkdf2:sha256:600000$8n8d...$c7b...', 'john.doe@example.com'),
('jane_smith', 'pbkdf2:sha256:600000$8n8d...$c7b...', 'jane.smith@example.com'),
('alice_jones', 'pbkdf2:sha256:600000$8n8d...$c7b...', 'alice.jones@example.com'),
('bob_brown', 'pbkdf2:sha256:600000$8n8d...$c7b...', 'bob.brown@example.com');
-- --- END CHANGE ---

