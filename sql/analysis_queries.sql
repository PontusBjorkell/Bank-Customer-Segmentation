-- Bank Customer Segmentation: analytical SQL catalogue
-- Every query is read-only and is exported automatically by scripts/run_analysis.py.

-- name: 01_portfolio_overview
-- description: Headline transaction, customer, location, balance, and monetary KPIs.
SELECT
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    COUNT(DISTINCT location_id) AS represented_locations,
    ROUND(SUM(transaction_amount_inr), 2) AS total_transaction_amount_inr,
    ROUND(AVG(transaction_amount_inr), 2) AS average_transaction_amount_inr,
    ROUND(AVG(account_balance_inr), 2) AS average_account_balance_inr,
    MIN(transaction_date) AS first_transaction_date,
    MAX(transaction_date) AS last_transaction_date
FROM fact_transaction;

-- name: 02_data_quality_coverage
-- description: Missing-value coverage for the transaction fact table.
SELECT * FROM vw_data_coverage;

-- name: 03_customer_transaction_frequency
-- description: Distribution of customers by observed transaction count.
SELECT
    transaction_count,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_pct
FROM customer_feature_mart
GROUP BY transaction_count
ORDER BY transaction_count;

-- name: 04_single_vs_repeat_customers
-- description: Comparison between customers with one transaction and repeat customers.
SELECT
    CASE
        WHEN transaction_count = 1 THEN 'Single transaction'
        ELSE 'Repeat customer'
    END AS customer_type,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_pct,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(average_transaction_amount), 2) AS average_transaction_value_inr,
    ROUND(AVG(average_account_balance), 2) AS average_account_balance_inr
FROM customer_feature_mart
GROUP BY customer_type
ORDER BY customer_count DESC;

-- name: 05_gender_customer_profile
-- description: Customer counts and behavioral KPIs by gender.
SELECT
    COALESCE(c.gender, 'Unknown') AS gender,
    COUNT(*) AS customer_count,
    ROUND(AVG(f.customer_age), 2) AS average_age,
    ROUND(AVG(f.transaction_count), 3) AS average_transaction_count,
    ROUND(AVG(f.total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(f.average_account_balance), 2) AS average_account_balance_inr
FROM customer_feature_mart AS f
JOIN dim_customer AS c ON c.customer_id = f.customer_id
GROUP BY COALESCE(c.gender, 'Unknown')
ORDER BY customer_count DESC;

-- name: 06_age_band_profile
-- description: Customer behavior across interpretable age groups.
WITH customer_bands AS (
    SELECT
        CASE
            WHEN customer_age IS NULL THEN 'Unknown'
            WHEN customer_age < 25 THEN '18-24'
            WHEN customer_age < 35 THEN '25-34'
            WHEN customer_age < 45 THEN '35-44'
            WHEN customer_age < 55 THEN '45-54'
            WHEN customer_age < 65 THEN '55-64'
            ELSE '65+'
        END AS age_band,
        transaction_count,
        total_transaction_amount,
        average_transaction_amount,
        average_account_balance
    FROM customer_feature_mart
)
SELECT
    age_band,
    COUNT(*) AS customer_count,
    ROUND(AVG(transaction_count), 3) AS average_transaction_count,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(average_transaction_amount), 2) AS average_transaction_value_inr,
    ROUND(AVG(average_account_balance), 2) AS average_account_balance_inr
FROM customer_bands
GROUP BY age_band
ORDER BY CASE age_band
    WHEN '18-24' THEN 1 WHEN '25-34' THEN 2 WHEN '35-44' THEN 3
    WHEN '45-54' THEN 4 WHEN '55-64' THEN 5 WHEN '65+' THEN 6 ELSE 7 END;

-- name: 07_top_locations_by_customers
-- description: Locations ranked by unique customer count.
SELECT
    location_name,
    unique_customers,
    transaction_count,
    total_transaction_amount_inr,
    average_transaction_amount_inr,
    average_account_balance_inr
FROM vw_location_performance
WHERE unique_customers > 0
ORDER BY unique_customers DESC, total_transaction_amount_inr DESC
LIMIT 25;

-- name: 08_top_locations_by_value
-- description: Locations ranked by total transaction value.
SELECT
    location_name,
    transaction_count,
    unique_customers,
    total_transaction_amount_inr,
    average_transaction_amount_inr,
    average_account_balance_inr
FROM vw_location_performance
WHERE transaction_count > 0
ORDER BY total_transaction_amount_inr DESC
LIMIT 25;

-- name: 09_location_customer_value
-- description: High-level customer value metrics for sufficiently represented locations.
SELECT
    l.location_name,
    COUNT(*) AS customer_count,
    ROUND(AVG(f.total_transaction_amount), 2) AS average_customer_total_inr,
    ROUND(AVG(f.average_transaction_amount), 2) AS average_transaction_value_inr,
    ROUND(AVG(f.average_account_balance), 2) AS average_account_balance_inr,
    ROUND(AVG(f.transaction_count), 3) AS average_transaction_count
FROM customer_feature_mart AS f
LEFT JOIN dim_location AS l ON l.location_id = f.primary_location_id
GROUP BY l.location_name
HAVING COUNT(*) >= 100
ORDER BY average_customer_total_inr DESC
LIMIT 25;

-- name: 10_monthly_kpis
-- description: Monthly transaction activity and monetary KPIs.
SELECT *
FROM vw_monthly_kpis
ORDER BY transaction_month;

-- name: 11_daily_transaction_trend
-- description: Daily volume, customer activity, and monetary value.
SELECT
    transaction_date,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS active_customers,
    ROUND(SUM(transaction_amount_inr), 2) AS total_transaction_amount_inr,
    ROUND(AVG(transaction_amount_inr), 2) AS average_transaction_amount_inr
FROM fact_transaction
WHERE transaction_date IS NOT NULL
GROUP BY transaction_date
ORDER BY transaction_date;

-- name: 12_weekday_activity
-- description: Transaction activity by day of week.
SELECT
    transaction_weekday,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    ROUND(SUM(transaction_amount_inr), 2) AS total_transaction_amount_inr,
    ROUND(AVG(transaction_amount_inr), 2) AS average_transaction_amount_inr
FROM fact_transaction
WHERE transaction_weekday IS NOT NULL
GROUP BY transaction_weekday
ORDER BY CASE transaction_weekday
    WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
    WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
    WHEN 'Sunday' THEN 7 ELSE 8 END;

-- name: 13_weekend_vs_weekday
-- description: Comparison of weekend and weekday transaction behavior.
SELECT
    CASE WHEN is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS period_type,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS transaction_pct,
    ROUND(SUM(transaction_amount_inr), 2) AS total_transaction_amount_inr,
    ROUND(AVG(transaction_amount_inr), 2) AS average_transaction_amount_inr
FROM fact_transaction
WHERE is_weekend IS NOT NULL
GROUP BY is_weekend
ORDER BY is_weekend;

-- name: 14_hourly_activity
-- description: Hour-by-hour transaction patterns.
SELECT
    transaction_hour,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    ROUND(SUM(transaction_amount_inr), 2) AS total_transaction_amount_inr,
    ROUND(AVG(transaction_amount_inr), 2) AS average_transaction_amount_inr
FROM fact_transaction
WHERE transaction_hour IS NOT NULL
GROUP BY transaction_hour
ORDER BY transaction_hour;

-- name: 15_daypart_activity
-- description: Transaction activity and value by daypart.
SELECT
    daypart,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS transaction_pct,
    ROUND(SUM(transaction_amount_inr), 2) AS total_transaction_amount_inr,
    ROUND(AVG(transaction_amount_inr), 2) AS average_transaction_amount_inr
FROM fact_transaction
WHERE daypart IS NOT NULL
GROUP BY daypart
ORDER BY CASE daypart
    WHEN 'night' THEN 1 WHEN 'morning' THEN 2 WHEN 'afternoon' THEN 3
    WHEN 'evening' THEN 4 WHEN 'late_evening' THEN 5 ELSE 6 END;

-- name: 16_transaction_amount_distribution
-- description: Transaction count and value across practical monetary bands.
WITH amount_bands AS (
    SELECT
        CASE
            WHEN transaction_amount_inr < 100 THEN 'Below 100'
            WHEN transaction_amount_inr < 500 THEN '100-499'
            WHEN transaction_amount_inr < 1000 THEN '500-999'
            WHEN transaction_amount_inr < 5000 THEN '1,000-4,999'
            WHEN transaction_amount_inr < 10000 THEN '5,000-9,999'
            WHEN transaction_amount_inr < 50000 THEN '10,000-49,999'
            ELSE '50,000+'
        END AS amount_band,
        transaction_amount_inr
    FROM fact_transaction
    WHERE transaction_amount_inr IS NOT NULL
)
SELECT
    amount_band,
    COUNT(*) AS transaction_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS transaction_pct,
    ROUND(SUM(transaction_amount_inr), 2) AS total_transaction_amount_inr
FROM amount_bands
GROUP BY amount_band
ORDER BY CASE amount_band
    WHEN 'Below 100' THEN 1 WHEN '100-499' THEN 2 WHEN '500-999' THEN 3
    WHEN '1,000-4,999' THEN 4 WHEN '5,000-9,999' THEN 5
    WHEN '10,000-49,999' THEN 6 ELSE 7 END;

-- name: 17_account_balance_distribution
-- description: Customer distribution across average account-balance bands.
WITH balance_bands AS (
    SELECT
        CASE
            WHEN average_account_balance IS NULL THEN 'Unknown'
            WHEN average_account_balance < 1000 THEN 'Below 1,000'
            WHEN average_account_balance < 10000 THEN '1,000-9,999'
            WHEN average_account_balance < 50000 THEN '10,000-49,999'
            WHEN average_account_balance < 100000 THEN '50,000-99,999'
            WHEN average_account_balance < 500000 THEN '100,000-499,999'
            ELSE '500,000+'
        END AS balance_band,
        total_transaction_amount,
        transaction_count
    FROM customer_feature_mart
)
SELECT
    balance_band,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_pct,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(transaction_count), 3) AS average_transaction_count
FROM balance_bands
GROUP BY balance_band
ORDER BY CASE balance_band
    WHEN 'Below 1,000' THEN 1 WHEN '1,000-9,999' THEN 2
    WHEN '10,000-49,999' THEN 3 WHEN '50,000-99,999' THEN 4
    WHEN '100,000-499,999' THEN 5 WHEN '500,000+' THEN 6 ELSE 7 END;

-- name: 18_transaction_value_deciles
-- description: Customer transaction value by total-spend decile.
WITH ranked AS (
    SELECT
        customer_id,
        total_transaction_amount,
        transaction_count,
        average_account_balance,
        NTILE(10) OVER (ORDER BY total_transaction_amount) AS spend_decile
    FROM customer_feature_mart
    WHERE total_transaction_amount IS NOT NULL
)
SELECT
    spend_decile,
    COUNT(*) AS customer_count,
    ROUND(MIN(total_transaction_amount), 2) AS minimum_total_inr,
    ROUND(MAX(total_transaction_amount), 2) AS maximum_total_inr,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_inr,
    ROUND(AVG(transaction_count), 3) AS average_transaction_count,
    ROUND(AVG(average_account_balance), 2) AS average_account_balance_inr
FROM ranked
GROUP BY spend_decile
ORDER BY spend_decile;

-- name: 19_balance_deciles
-- description: Customer characteristics by average-account-balance decile.
WITH ranked AS (
    SELECT
        customer_id,
        average_account_balance,
        total_transaction_amount,
        average_transaction_amount,
        NTILE(10) OVER (ORDER BY average_account_balance) AS balance_decile
    FROM customer_feature_mart
    WHERE average_account_balance IS NOT NULL
)
SELECT
    balance_decile,
    COUNT(*) AS customer_count,
    ROUND(MIN(average_account_balance), 2) AS minimum_balance_inr,
    ROUND(MAX(average_account_balance), 2) AS maximum_balance_inr,
    ROUND(AVG(average_account_balance), 2) AS average_balance_inr,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(average_transaction_amount), 2) AS average_transaction_value_inr
FROM ranked
GROUP BY balance_decile
ORDER BY balance_decile;

-- name: 20_top_customers_by_total_value
-- description: Highest-value observed customers by total transaction amount.
SELECT
    f.customer_id,
    c.gender,
    f.customer_age,
    l.location_name AS primary_location,
    f.transaction_count,
    ROUND(f.total_transaction_amount, 2) AS total_transaction_amount_inr,
    ROUND(f.average_transaction_amount, 2) AS average_transaction_amount_inr,
    ROUND(f.average_account_balance, 2) AS average_account_balance_inr
FROM customer_feature_mart AS f
JOIN dim_customer AS c ON c.customer_id = f.customer_id
LEFT JOIN dim_location AS l ON l.location_id = f.primary_location_id
ORDER BY f.total_transaction_amount DESC
LIMIT 100;

-- name: 21_top_customers_by_balance
-- description: Customers with the highest observed average account balances.
SELECT
    f.customer_id,
    c.gender,
    f.customer_age,
    l.location_name AS primary_location,
    f.transaction_count,
    ROUND(f.average_account_balance, 2) AS average_account_balance_inr,
    ROUND(f.total_transaction_amount, 2) AS total_transaction_amount_inr,
    ROUND(f.balance_to_total_spend_ratio, 4) AS balance_to_spend_ratio
FROM customer_feature_mart AS f
JOIN dim_customer AS c ON c.customer_id = f.customer_id
LEFT JOIN dim_location AS l ON l.location_id = f.primary_location_id
WHERE f.average_account_balance IS NOT NULL
ORDER BY f.average_account_balance DESC
LIMIT 100;

-- name: 22_repeat_customer_profile
-- description: Detailed profile of customers with multiple observed transactions.
SELECT
    transaction_count,
    COUNT(*) AS customer_count,
    ROUND(AVG(active_days), 2) AS average_active_days,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(transaction_amount_cv), 4) AS average_amount_variability,
    ROUND(AVG(account_balance_cv), 4) AS average_balance_variability
FROM customer_feature_mart
WHERE transaction_count >= 2
GROUP BY transaction_count
ORDER BY transaction_count;

-- name: 23_multi_location_customers
-- description: Customers observed across multiple locations.
SELECT
    distinct_locations,
    COUNT(*) AS customer_count,
    ROUND(AVG(transaction_count), 3) AS average_transaction_count,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(average_account_balance), 2) AS average_account_balance_inr
FROM customer_feature_mart
WHERE distinct_locations >= 2
GROUP BY distinct_locations
ORDER BY distinct_locations;

-- name: 24_high_value_low_balance_customers
-- description: Customers whose observed spending is high relative to their account balance.
SELECT
    f.customer_id,
    c.gender,
    f.customer_age,
    l.location_name AS primary_location,
    f.transaction_count,
    ROUND(f.total_transaction_amount, 2) AS total_transaction_amount_inr,
    ROUND(f.average_account_balance, 2) AS average_account_balance_inr,
    ROUND(f.balance_to_total_spend_ratio, 4) AS balance_to_spend_ratio
FROM customer_feature_mart AS f
JOIN dim_customer AS c ON c.customer_id = f.customer_id
LEFT JOIN dim_location AS l ON l.location_id = f.primary_location_id
WHERE f.total_transaction_amount >= 10000
  AND f.balance_to_total_spend_ratio IS NOT NULL
ORDER BY f.balance_to_total_spend_ratio ASC, f.total_transaction_amount DESC
LIMIT 100;

-- name: 25_high_balance_low_activity_customers
-- description: High-balance customers with only one observed transaction.
SELECT
    f.customer_id,
    c.gender,
    f.customer_age,
    l.location_name AS primary_location,
    ROUND(f.average_account_balance, 2) AS average_account_balance_inr,
    ROUND(f.total_transaction_amount, 2) AS total_transaction_amount_inr
FROM customer_feature_mart AS f
JOIN dim_customer AS c ON c.customer_id = f.customer_id
LEFT JOIN dim_location AS l ON l.location_id = f.primary_location_id
WHERE f.transaction_count = 1
  AND f.average_account_balance IS NOT NULL
ORDER BY f.average_account_balance DESC
LIMIT 100;

-- name: 26_transaction_amount_outliers
-- description: Largest individual transactions with customer context.
SELECT
    t.transaction_id,
    t.customer_id,
    t.transaction_date,
    t.transaction_time,
    l.location_name AS transaction_location,
    ROUND(t.transaction_amount_inr, 2) AS transaction_amount_inr,
    ROUND(t.account_balance_inr, 2) AS account_balance_inr,
    ROUND(t.balance_to_transaction_ratio, 4) AS balance_to_transaction_ratio
FROM fact_transaction AS t
LEFT JOIN dim_location AS l ON l.location_id = t.location_id
WHERE t.transaction_amount_inr IS NOT NULL
ORDER BY t.transaction_amount_inr DESC
LIMIT 100;

-- name: 27_balance_to_spend_ratio_distribution
-- description: Customer distribution across balance-to-total-spend ratio bands.
WITH ratio_bands AS (
    SELECT
        CASE
            WHEN balance_to_total_spend_ratio IS NULL THEN 'Unknown'
            WHEN balance_to_total_spend_ratio < 0.5 THEN 'Below 0.5'
            WHEN balance_to_total_spend_ratio < 1 THEN '0.5-0.99'
            WHEN balance_to_total_spend_ratio < 5 THEN '1-4.99'
            WHEN balance_to_total_spend_ratio < 10 THEN '5-9.99'
            ELSE '10+'
        END AS ratio_band,
        total_transaction_amount,
        average_account_balance
    FROM customer_feature_mart
)
SELECT
    ratio_band,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_pct,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(average_account_balance), 2) AS average_account_balance_inr
FROM ratio_bands
GROUP BY ratio_band
ORDER BY CASE ratio_band
    WHEN 'Below 0.5' THEN 1 WHEN '0.5-0.99' THEN 2 WHEN '1-4.99' THEN 3
    WHEN '5-9.99' THEN 4 WHEN '10+' THEN 5 ELSE 6 END;

-- name: 28_customer_activity_span
-- description: Customer distribution by observed active-day span.
WITH spans AS (
    SELECT
        CASE
            WHEN active_days IS NULL THEN 'Unknown'
            WHEN active_days = 1 THEN '1 day'
            WHEN active_days <= 7 THEN '2-7 days'
            WHEN active_days <= 30 THEN '8-30 days'
            WHEN active_days <= 60 THEN '31-60 days'
            ELSE '61+ days'
        END AS active_span,
        transaction_count,
        total_transaction_amount
    FROM customer_feature_mart
)
SELECT
    active_span,
    COUNT(*) AS customer_count,
    ROUND(AVG(transaction_count), 3) AS average_transaction_count,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr
FROM spans
GROUP BY active_span
ORDER BY CASE active_span
    WHEN '1 day' THEN 1 WHEN '2-7 days' THEN 2 WHEN '8-30 days' THEN 3
    WHEN '31-60 days' THEN 4 WHEN '61+ days' THEN 5 ELSE 6 END;

-- name: 29_customer_daypart_preferences
-- description: Dominant observed transaction daypart for each customer.
WITH preferences AS (
    SELECT
        customer_id,
        CASE MAX(
            night_transaction_share,
            morning_transaction_share,
            afternoon_transaction_share,
            evening_transaction_share,
            late_evening_transaction_share
        )
            WHEN night_transaction_share THEN 'Night'
            WHEN morning_transaction_share THEN 'Morning'
            WHEN afternoon_transaction_share THEN 'Afternoon'
            WHEN evening_transaction_share THEN 'Evening'
            ELSE 'Late evening'
        END AS preferred_daypart,
        total_transaction_amount,
        average_account_balance
    FROM customer_feature_mart
)
SELECT
    preferred_daypart,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_pct,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(average_account_balance), 2) AS average_account_balance_inr
FROM preferences
GROUP BY preferred_daypart
ORDER BY customer_count DESC;

-- name: 30_weekend_oriented_customers
-- description: Customers whose observed transactions are predominantly on weekends.
SELECT
    CASE
        WHEN weekend_transaction_share = 0 THEN 'No weekend activity'
        WHEN weekend_transaction_share < 0.5 THEN 'Mostly weekdays'
        WHEN weekend_transaction_share < 1 THEN 'Mostly weekends'
        ELSE 'Weekend only'
    END AS weekend_profile,
    COUNT(*) AS customer_count,
    ROUND(AVG(transaction_count), 3) AS average_transaction_count,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(average_account_balance), 2) AS average_account_balance_inr
FROM customer_feature_mart
WHERE weekend_transaction_share IS NOT NULL
GROUP BY weekend_profile
ORDER BY customer_count DESC;

-- name: 31_customer_value_matrix
-- description: Four-quadrant customer matrix based on median spend and balance.
WITH medians AS (
    SELECT
        AVG(total_transaction_amount) AS spend_reference,
        AVG(average_account_balance) AS balance_reference
    FROM customer_feature_mart
    WHERE total_transaction_amount IS NOT NULL
      AND average_account_balance IS NOT NULL
), classified AS (
    SELECT
        CASE
            WHEN f.total_transaction_amount >= m.spend_reference
             AND f.average_account_balance >= m.balance_reference
                THEN 'High spend / High balance'
            WHEN f.total_transaction_amount >= m.spend_reference
                THEN 'High spend / Lower balance'
            WHEN f.average_account_balance >= m.balance_reference
                THEN 'Lower spend / High balance'
            ELSE 'Lower spend / Lower balance'
        END AS value_quadrant,
        f.transaction_count,
        f.total_transaction_amount,
        f.average_account_balance
    FROM customer_feature_mart AS f
    CROSS JOIN medians AS m
    WHERE f.total_transaction_amount IS NOT NULL
      AND f.average_account_balance IS NOT NULL
)
SELECT
    value_quadrant,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_pct,
    ROUND(AVG(transaction_count), 3) AS average_transaction_count,
    ROUND(AVG(total_transaction_amount), 2) AS average_total_amount_inr,
    ROUND(AVG(average_account_balance), 2) AS average_account_balance_inr
FROM classified
GROUP BY value_quadrant
ORDER BY customer_count DESC;

-- name: 32_segmentation_feature_summary
-- description: Summary statistics for the main numerical clustering candidates.
SELECT
    COUNT(*) AS customer_count,
    ROUND(AVG(customer_age), 4) AS mean_customer_age,
    ROUND(AVG(transaction_count), 4) AS mean_transaction_count,
    ROUND(AVG(total_transaction_amount), 4) AS mean_total_transaction_amount,
    ROUND(AVG(average_transaction_amount), 4) AS mean_average_transaction_amount,
    ROUND(AVG(average_account_balance), 4) AS mean_average_account_balance,
    ROUND(AVG(transaction_amount_cv), 4) AS mean_transaction_amount_cv,
    ROUND(AVG(account_balance_cv), 4) AS mean_account_balance_cv,
    ROUND(AVG(weekend_transaction_share), 4) AS mean_weekend_share,
    ROUND(AVG(average_transaction_hour), 4) AS mean_transaction_hour,
    ROUND(AVG(balance_to_total_spend_ratio), 4) AS mean_balance_to_spend_ratio
FROM customer_feature_mart;
