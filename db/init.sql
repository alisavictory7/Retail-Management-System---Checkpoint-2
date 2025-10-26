-- db/init.sql
-- Drop tables in an order that respects foreign key constraints.
-- New tables for Checkpoint 2 tactics
DROP TABLE IF EXISTS "AuditLog";
DROP TABLE IF EXISTS "CircuitBreakerState";
DROP TABLE IF EXISTS "OrderQueue";
DROP TABLE IF EXISTS "FeatureToggle";
DROP TABLE IF EXISTS "PartnerAPIKey";
DROP TABLE IF EXISTS "MessageQueue";
DROP TABLE IF EXISTS "TestRecord";
DROP TABLE IF EXISTS "SystemMetrics";
DROP TABLE IF EXISTS "FlashSaleReservation";
DROP TABLE IF EXISTS "FlashSale";
DROP TABLE IF EXISTS "PartnerProduct";
DROP TABLE IF EXISTS "Partner";
-- Existing tables
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

-- ==============================================
-- CHECKPOINT 2: NEW TABLES FOR QUALITY TACTICS
-- ==============================================

-- Flash Sale Tables (for Performance & Availability tactics)
CREATE TABLE "FlashSale" (
    "flashSaleID" SERIAL PRIMARY KEY,
    "productID" INTEGER REFERENCES "Product"("productID") NOT NULL,
    "start_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "end_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "discount_percent" DECIMAL(5, 2) NOT NULL,
    "max_quantity" INTEGER NOT NULL,
    "reserved_quantity" INTEGER DEFAULT 0,
    "status" VARCHAR(20) DEFAULT 'active' -- active, expired, cancelled
);

CREATE TABLE "FlashSaleReservation" (
    "reservationID" SERIAL PRIMARY KEY,
    "flashSaleID" INTEGER REFERENCES "FlashSale"("flashSaleID") NOT NULL,
    "userID" INTEGER REFERENCES "User"("userID") NOT NULL,
    "quantity" INTEGER NOT NULL,
    "reserved_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "expires_at" TIMESTAMP WITH TIME ZONE NOT NULL,
    "status" VARCHAR(20) DEFAULT 'reserved' -- reserved, confirmed, expired, cancelled
);

-- Partner/VAR Tables (for Integrability & Security tactics)
CREATE TABLE "Partner" (
    "partnerID" SERIAL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "api_endpoint" VARCHAR(500),
    "api_key" VARCHAR(255),
    "sync_frequency" INTEGER DEFAULT 3600, -- seconds
    "last_sync" TIMESTAMP WITH TIME ZONE,
    "status" VARCHAR(20) DEFAULT 'active' -- active, inactive, suspended
);

CREATE TABLE "PartnerProduct" (
    "partnerProductID" SERIAL PRIMARY KEY,
    "partnerID" INTEGER REFERENCES "Partner"("partnerID") NOT NULL,
    "external_product_id" VARCHAR(255) NOT NULL,
    "productID" INTEGER REFERENCES "Product"("productID"),
    "sync_status" VARCHAR(20) DEFAULT 'pending', -- pending, synced, failed
    "last_synced" TIMESTAMP WITH TIME ZONE,
    "sync_data" TEXT -- JSON data from partner
);

-- Security Tables (for Authenticate Actors & Validate Input tactics)
CREATE TABLE "PartnerAPIKey" (
    "keyID" SERIAL PRIMARY KEY,
    "partnerID" INTEGER REFERENCES "Partner"("partnerID") NOT NULL,
    "api_key" VARCHAR(255) UNIQUE NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "expires_at" TIMESTAMP WITH TIME ZONE,
    "is_active" BOOLEAN DEFAULT TRUE,
    "last_used" TIMESTAMP WITH TIME ZONE,
    "usage_count" INTEGER DEFAULT 0
);

-- Availability Tables (for Circuit Breaker, Graceful Degradation, Retry tactics)
CREATE TABLE "CircuitBreakerState" (
    "breakerID" SERIAL PRIMARY KEY,
    "service_name" VARCHAR(100) NOT NULL UNIQUE,
    "state" VARCHAR(20) NOT NULL DEFAULT 'closed', -- closed, open, half_open
    "failure_count" INTEGER DEFAULT 0,
    "last_failure_time" TIMESTAMP WITH TIME ZONE,
    "next_attempt_time" TIMESTAMP WITH TIME ZONE,
    "failure_threshold" INTEGER DEFAULT 5,
    "timeout_duration" INTEGER DEFAULT 60, -- seconds
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE "OrderQueue" (
    "queueID" SERIAL PRIMARY KEY,
    "saleID" INTEGER REFERENCES "Sale"("saleID") NOT NULL,
    "userID" INTEGER REFERENCES "User"("userID") NOT NULL,
    "queue_type" VARCHAR(50) NOT NULL, -- payment_retry, flash_sale, processing
    "priority" INTEGER DEFAULT 0, -- higher number = higher priority
    "status" VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "scheduled_for" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "attempts" INTEGER DEFAULT 0,
    "max_attempts" INTEGER DEFAULT 3,
    "error_message" TEXT,
    "retry_after" TIMESTAMP WITH TIME ZONE
);

-- Modifiability Tables (for Feature Toggle tactic)
CREATE TABLE "FeatureToggle" (
    "toggleID" SERIAL PRIMARY KEY,
    "feature_name" VARCHAR(100) NOT NULL UNIQUE,
    "is_enabled" BOOLEAN DEFAULT FALSE,
    "description" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updated_by" VARCHAR(100),
    "rollout_percentage" INTEGER DEFAULT 0, -- 0-100 for gradual rollouts
    "target_users" TEXT -- JSON array of user IDs or conditions
);

-- Integrability Tables (for Publish-Subscribe pattern)
CREATE TABLE "MessageQueue" (
    "messageID" SERIAL PRIMARY KEY,
    "topic" VARCHAR(100) NOT NULL,
    "message_type" VARCHAR(50) NOT NULL,
    "payload" TEXT NOT NULL, -- JSON message content
    "status" VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "scheduled_for" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "attempts" INTEGER DEFAULT 0,
    "max_attempts" INTEGER DEFAULT 3,
    "error_message" TEXT,
    "subscriber_id" VARCHAR(100) -- which subscriber processed this
);

-- Testability Tables (for Record/Playback tactic)
CREATE TABLE "TestRecord" (
    "recordID" SERIAL PRIMARY KEY,
    "test_name" VARCHAR(100) NOT NULL,
    "record_type" VARCHAR(50) NOT NULL, -- request, response, state
    "sequence_number" INTEGER NOT NULL,
    "timestamp" TIMESTAMP WITH TIME ZONE NOT NULL,
    "data" TEXT NOT NULL, -- JSON data
    "record_metadata" TEXT, -- JSON metadata
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit & Metrics Tables (for all tactics)
CREATE TABLE "AuditLog" (
    "auditID" SERIAL PRIMARY KEY,
    "event_type" VARCHAR(50) NOT NULL,
    "entity_type" VARCHAR(50) NOT NULL,
    "entity_id" INTEGER,
    "user_id" INTEGER REFERENCES "User"("userID"),
    "action" VARCHAR(100) NOT NULL,
    "old_values" TEXT, -- JSON
    "new_values" TEXT, -- JSON
    "ip_address" VARCHAR(45),
    "user_agent" TEXT,
    "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "success" BOOLEAN DEFAULT TRUE,
    "error_message" TEXT
);

CREATE TABLE "SystemMetrics" (
    "metricID" SERIAL PRIMARY KEY,
    "metric_name" VARCHAR(100) NOT NULL,
    "metric_value" DECIMAL(15, 4) NOT NULL,
    "metric_unit" VARCHAR(20), -- ms, count, percent, etc.
    "tags" TEXT, -- JSON key-value pairs
    "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "service_name" VARCHAR(100),
    "instance_id" VARCHAR(100)
);

-- ==============================================
-- INDEXES FOR PERFORMANCE
-- ==============================================

-- Flash Sale indexes
CREATE INDEX "idx_flashsale_product_status" ON "FlashSale"("productID", "status");
CREATE INDEX "idx_flashsale_time_range" ON "FlashSale"("start_time", "end_time");
CREATE INDEX "idx_flashsale_reservation_user" ON "FlashSaleReservation"("userID", "status");

-- Partner indexes
CREATE INDEX "idx_partner_status" ON "Partner"("status");
CREATE INDEX "idx_partnerproduct_partner" ON "PartnerProduct"("partnerID", "sync_status");
CREATE INDEX "idx_partnerapikey_key" ON "PartnerAPIKey"("api_key", "is_active");

-- Circuit Breaker indexes
CREATE INDEX "idx_circuitbreaker_service" ON "CircuitBreakerState"("service_name", "state");

-- Queue indexes
CREATE INDEX "idx_orderqueue_status_priority" ON "OrderQueue"("status", "priority", "scheduled_for");
CREATE INDEX "idx_orderqueue_type" ON "OrderQueue"("queue_type", "status");
CREATE INDEX "idx_messagequeue_topic_status" ON "MessageQueue"("topic", "status", "scheduled_for");

-- Audit indexes
CREATE INDEX "idx_auditlog_timestamp" ON "AuditLog"("timestamp");
CREATE INDEX "idx_auditlog_entity" ON "AuditLog"("entity_type", "entity_id");
CREATE INDEX "idx_systemmetrics_name_timestamp" ON "SystemMetrics"("metric_name", "timestamp");

-- ==============================================
-- SAMPLE DATA FOR TESTING
-- ==============================================

-- Insert sample partners
INSERT INTO "Partner" ("name", "api_endpoint", "api_key", "sync_frequency", "status") VALUES
('TechSupplier Inc', 'https://api.techsupplier.com/products', 'ts_key_12345', 3600, 'active'),
('Global Electronics', 'https://api.globalelectronics.com/catalog', 'ge_key_67890', 7200, 'active'),
('Digital Distributors', 'https://api.digitaldist.com/items', 'dd_key_abcdef', 1800, 'active');

-- Insert sample API keys
INSERT INTO "PartnerAPIKey" ("partnerID", "api_key", "expires_at") VALUES
(1, 'ts_key_12345', NOW() + INTERVAL '1 year'),
(2, 'ge_key_67890', NOW() + INTERVAL '1 year'),
(3, 'dd_key_abcdef', NOW() + INTERVAL '1 year');

-- Insert sample feature toggles
INSERT INTO "FeatureToggle" ("feature_name", "is_enabled", "description", "rollout_percentage") VALUES
('flash_sale_enabled', TRUE, 'Enable Flash Sale functionality', 100),
('partner_sync_enabled', TRUE, 'Enable Partner catalog synchronization', 100),
('circuit_breaker_enabled', TRUE, 'Enable Circuit Breaker for payment service', 100),
('queue_processing_enabled', TRUE, 'Enable Order Queue processing', 100),
('advanced_analytics', FALSE, 'Enable advanced analytics dashboard', 0);

-- Insert sample circuit breaker states
INSERT INTO "CircuitBreakerState" ("service_name", "state", "failure_threshold", "timeout_duration") VALUES
('payment_service', 'closed', 5, 60),
('partner_api', 'closed', 3, 30),
('inventory_service', 'closed', 10, 120);

-- Insert sample flash sales
INSERT INTO "FlashSale" ("productID", "start_time", "end_time", "discount_percent", "max_quantity", "status") VALUES
(1, NOW() - INTERVAL '1 hour', NOW() + INTERVAL '23 hours', 25.00, 10, 'active'),
(2, NOW() - INTERVAL '30 minutes', NOW() + INTERVAL '1 hour 30 minutes', 15.00, 50, 'active'),
(3, NOW() + INTERVAL '1 day', NOW() + INTERVAL '2 days', 30.00, 20, 'active');

