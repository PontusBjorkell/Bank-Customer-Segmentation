PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS vw_data_coverage;
DROP VIEW IF EXISTS vw_location_performance;
DROP VIEW IF EXISTS vw_monthly_kpis;
DROP VIEW IF EXISTS vw_customer_360;
DROP VIEW IF EXISTS vw_transaction_enriched;

DROP TABLE IF EXISTS customer_feature_mart;
DROP TABLE IF EXISTS fact_transaction;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_location;

CREATE TABLE dim_location (
    location_id     INTEGER PRIMARY KEY,
    location_name   TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_customer (
    customer_id             TEXT PRIMARY KEY NOT NULL,
    gender                  TEXT CHECK (gender IN ('M', 'F') OR gender IS NULL),
    customer_age            REAL CHECK (customer_age BETWEEN 18 AND 100 OR customer_age IS NULL),
    primary_location_id     INTEGER,
    first_transaction_date  TEXT,
    last_transaction_date   TEXT,
    FOREIGN KEY (primary_location_id) REFERENCES dim_location(location_id)
);

CREATE TABLE fact_transaction (
    transaction_id                 TEXT PRIMARY KEY NOT NULL,
    customer_id                    TEXT NOT NULL,
    customer_dob                   TEXT,
    customer_age                   REAL,
    gender                         TEXT CHECK (gender IN ('M', 'F') OR gender IS NULL),
    account_balance_inr            REAL,
    transaction_date               TEXT,
    transaction_time               TEXT,
    transaction_datetime           TEXT,
    transaction_hour               INTEGER CHECK (transaction_hour BETWEEN 0 AND 23 OR transaction_hour IS NULL),
    transaction_weekday            TEXT,
    transaction_month              TEXT,
    daypart                        TEXT,
    is_weekend                     INTEGER CHECK (is_weekend IN (0, 1) OR is_weekend IS NULL),
    transaction_amount_inr         REAL,
    balance_to_transaction_ratio   REAL,
    log_transaction_amount         REAL,
    log_account_balance            REAL,
    location_id                    INTEGER,
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    FOREIGN KEY (location_id) REFERENCES dim_location(location_id)
);

CREATE TABLE customer_feature_mart (
    customer_id                         TEXT PRIMARY KEY NOT NULL,
    customer_age                        REAL,
    distinct_locations                  INTEGER,
    transaction_count                   INTEGER NOT NULL,
    total_transaction_amount            REAL,
    average_transaction_amount          REAL,
    median_transaction_amount           REAL,
    minimum_transaction_amount          REAL,
    maximum_transaction_amount          REAL,
    transaction_amount_std              REAL,
    average_account_balance             REAL,
    median_account_balance              REAL,
    minimum_account_balance             REAL,
    maximum_account_balance             REAL,
    account_balance_std                 REAL,
    first_transaction_date              TEXT,
    last_transaction_date               TEXT,
    average_transaction_hour            REAL,
    weekend_transaction_share           REAL,
    transaction_amount_cv               REAL,
    account_balance_cv                   REAL,
    night_transaction_share             REAL,
    morning_transaction_share           REAL,
    afternoon_transaction_share         REAL,
    evening_transaction_share           REAL,
    late_evening_transaction_share      REAL,
    active_days                         INTEGER,
    transactions_per_active_day         REAL,
    balance_to_total_spend_ratio        REAL,
    is_single_transaction_customer      INTEGER CHECK (is_single_transaction_customer IN (0, 1)),
    log_total_transaction_amount        REAL,
    log_average_transaction_amount      REAL,
    log_average_account_balance         REAL,
    primary_location_id                 INTEGER,
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    FOREIGN KEY (primary_location_id) REFERENCES dim_location(location_id)
);

CREATE INDEX idx_fact_transaction_customer
    ON fact_transaction(customer_id);

CREATE INDEX idx_fact_transaction_date
    ON fact_transaction(transaction_date);

CREATE INDEX idx_fact_transaction_month
    ON fact_transaction(transaction_month);

CREATE INDEX idx_fact_transaction_location
    ON fact_transaction(location_id);

CREATE INDEX idx_fact_transaction_amount
    ON fact_transaction(transaction_amount_inr);

CREATE INDEX idx_customer_gender
    ON dim_customer(gender);

CREATE INDEX idx_customer_location
    ON dim_customer(primary_location_id);

CREATE INDEX idx_feature_transaction_count
    ON customer_feature_mart(transaction_count);

CREATE INDEX idx_feature_total_amount
    ON customer_feature_mart(total_transaction_amount);

CREATE INDEX idx_feature_average_balance
    ON customer_feature_mart(average_account_balance);
