DROP VIEW IF EXISTS vw_transaction_enriched;
CREATE VIEW vw_transaction_enriched AS
SELECT
    t.transaction_id,
    t.customer_id,
    t.transaction_date,
    t.transaction_time,
    t.transaction_datetime,
    t.transaction_month,
    t.transaction_weekday,
    t.transaction_hour,
    t.daypart,
    t.is_weekend,
    t.transaction_amount_inr,
    t.account_balance_inr,
    t.balance_to_transaction_ratio,
    t.gender AS transaction_gender,
    t.customer_age AS transaction_customer_age,
    l.location_name AS transaction_location
FROM fact_transaction AS t
LEFT JOIN dim_location AS l
    ON l.location_id = t.location_id;

DROP VIEW IF EXISTS vw_customer_360;
CREATE VIEW vw_customer_360 AS
SELECT
    c.customer_id,
    c.gender,
    c.customer_age,
    l.location_name AS primary_location,
    f.distinct_locations,
    f.transaction_count,
    f.total_transaction_amount,
    f.average_transaction_amount,
    f.median_transaction_amount,
    f.minimum_transaction_amount,
    f.maximum_transaction_amount,
    f.transaction_amount_std,
    f.transaction_amount_cv,
    f.average_account_balance,
    f.median_account_balance,
    f.minimum_account_balance,
    f.maximum_account_balance,
    f.account_balance_std,
    f.account_balance_cv,
    f.first_transaction_date,
    f.last_transaction_date,
    f.active_days,
    f.transactions_per_active_day,
    f.average_transaction_hour,
    f.weekend_transaction_share,
    f.night_transaction_share,
    f.morning_transaction_share,
    f.afternoon_transaction_share,
    f.evening_transaction_share,
    f.late_evening_transaction_share,
    f.balance_to_total_spend_ratio,
    f.is_single_transaction_customer,
    f.log_total_transaction_amount,
    f.log_average_transaction_amount,
    f.log_average_account_balance
FROM dim_customer AS c
JOIN customer_feature_mart AS f
    ON f.customer_id = c.customer_id
LEFT JOIN dim_location AS l
    ON l.location_id = c.primary_location_id;

DROP VIEW IF EXISTS vw_monthly_kpis;
CREATE VIEW vw_monthly_kpis AS
SELECT
    transaction_month,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS active_customers,
    ROUND(SUM(transaction_amount_inr), 2) AS total_transaction_amount_inr,
    ROUND(AVG(transaction_amount_inr), 2) AS average_transaction_amount_inr,
    ROUND(AVG(account_balance_inr), 2) AS average_account_balance_inr,
    ROUND(100.0 * AVG(CASE WHEN is_weekend = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS weekend_transaction_pct
FROM fact_transaction
WHERE transaction_month IS NOT NULL
GROUP BY transaction_month;

DROP VIEW IF EXISTS vw_location_performance;
CREATE VIEW vw_location_performance AS
SELECT
    l.location_id,
    l.location_name,
    COUNT(t.transaction_id) AS transaction_count,
    COUNT(DISTINCT t.customer_id) AS unique_customers,
    ROUND(SUM(t.transaction_amount_inr), 2) AS total_transaction_amount_inr,
    ROUND(AVG(t.transaction_amount_inr), 2) AS average_transaction_amount_inr,
    ROUND(AVG(t.account_balance_inr), 2) AS average_account_balance_inr
FROM dim_location AS l
LEFT JOIN fact_transaction AS t
    ON t.location_id = l.location_id
GROUP BY l.location_id, l.location_name;

DROP VIEW IF EXISTS vw_data_coverage;
CREATE VIEW vw_data_coverage AS
SELECT
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(CASE WHEN customer_age IS NULL THEN 1 ELSE 0 END) AS missing_age_count,
    SUM(CASE WHEN gender IS NULL THEN 1 ELSE 0 END) AS missing_gender_count,
    SUM(CASE WHEN location_id IS NULL THEN 1 ELSE 0 END) AS missing_location_count,
    SUM(CASE WHEN account_balance_inr IS NULL THEN 1 ELSE 0 END) AS missing_balance_count,
    SUM(CASE WHEN transaction_date IS NULL THEN 1 ELSE 0 END) AS missing_date_count,
    SUM(CASE WHEN transaction_time IS NULL THEN 1 ELSE 0 END) AS missing_time_count,
    SUM(CASE WHEN transaction_amount_inr IS NULL THEN 1 ELSE 0 END) AS missing_amount_count
FROM fact_transaction;
