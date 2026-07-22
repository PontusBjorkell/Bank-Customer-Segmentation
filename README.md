# 🏦 Bank Customer Segmentation

An end-to-end customer analytics project combining reusable Python, SQLite, analytical SQL, statistical reporting, unsupervised machine learning, and an interactive Streamlit dashboard.

The project demonstrates a complete analytics workflow on more than **1 million banking transactions**, beginning with raw data preparation and ending with downloadable reports and business-oriented customer segmentation.

---

## Dashboard Preview

### Home

![Home](images/home.png)

---

### Overview

![Overview](images/overview.png)

---

### SQL Analytics

![SQL Analytics](images/sql-analytics.png)

---

### Customer Segments

![Customer Segments](images/customer-segments.png)

---

### Statistical Analysis

![Statistical Analysis](images/statistical-analysis.png)

---

### Business Insights

![Business Insights](images/business-insights.png)

---

### Downloads

![Downloads](images/downloads.png)

---

# Project Overview

This project was designed to resemble a small production analytics system rather than a traditional machine learning notebook.

The workflow includes

- data preparation
- feature engineering
- data validation
- normalized SQLite warehouse
- analytical SQL reporting
- unsupervised customer segmentation
- statistical model comparison
- business interpretation
- downloadable analytical artifacts
- interactive Streamlit dashboard

Instead of focusing only on clustering, the project emphasizes reproducibility, organization, documentation, and communication of analytical results.

---

# Dataset

The project analyzes over

- **1,048,567 banking transactions**
- **884,265 customers**
- **9,318 represented locations**

The transactional portfolio contains approximately

- **₹1.65 billion** total observed transaction value.

---

# Project Architecture

```
Bank-Customer-Segmentation/
│
├── app/                    # Streamlit dashboard
├── data/
│   ├── raw/
│   ├── processed/
│   └── warehouse/
│
├── artifacts/
│   ├── clustering/
│   ├── statistics/
│   ├── reports/
│   └── figures/
│
├── sql/
│   ├── schema.sql
│   ├── analytical_queries.sql
│   └── views.sql
│
├── scripts/
│   ├── prepare_data.py
│   ├── build_database.py
│   ├── run_sql_reports.py
│   ├── build_features.py
│   ├── clustering.py
│   ├── statistical_analysis.py
│   └── export_dashboard_data.py
│
├── images/
├── requirements.txt
└── README.md
```

---

# Workflow

The project follows a complete analytics pipeline.

```
Raw Transactions
        │
        ▼
Data Cleaning & Validation
        │
        ▼
Feature Engineering
        │
        ▼
SQLite Warehouse
        │
        ▼
32 SQL Reports
        │
        ▼
Customer Segmentation
        │
        ▼
Statistical Diagnostics
        │
        ▼
Business Interpretation
        │
        ▼
Interactive Dashboard
```

---

# Technologies

## Python

- pandas
- NumPy
- scikit-learn
- SciPy
- SQLite3
- Plotly
- Streamlit

---

## Machine Learning

The project compares several clustering algorithms including

- MiniBatch K-Means
- Gaussian Mixture Models
- Agglomerative Clustering
- DBSCAN

Model comparison is based on multiple internal validation metrics.

---

## Statistical Analysis

The project includes

- silhouette score
- Davies–Bouldin index
- Calinski–Harabasz index
- cluster profile comparison
- standardized feature importance
- PCA visualization
- post-hoc classifier diagnostics

Rather than reporting only a single clustering solution, multiple candidate models are evaluated and compared systematically.

---

# SQL Analytics

The project automatically generates **32 analytical SQL reports** covering topics including

- portfolio overview
- customer activity
- transaction patterns
- geographical distribution
- account balances
- customer value
- temporal trends
- location statistics
- feature summaries

All reports can be browsed directly inside the dashboard and exported as CSV files.

---

# Customer Segmentation

Customer segmentation is performed using engineered behavioral features such as

- transaction frequency
- observed active days
- account balance variability
- transaction amount variability
- transaction timing
- average balances
- transaction volume

The dashboard allows interactive exploration of the discovered customer groups.

---

# Statistical Diagnostics

The project emphasizes analytical transparency.

Rather than accepting clustering output at face value, the dashboard includes

- algorithm comparison
- parameter comparison
- cluster separability
- standardized feature comparisons
- PCA projections
- assignment confidence
- post-hoc reproducibility analysis

This provides evidence supporting why a particular clustering solution was selected.

---

# Business Insights

Technical clustering results are translated into business recommendations.

Each discovered segment includes

- customer count
- portfolio share
- behavioral profile
- observed patterns
- recommended business actions

The dashboard also discusses important methodological caveats, avoiding over-interpretation of unsupervised learning results.

---

# Download Center

The dashboard includes an export interface for

- SQL reports
- statistical tables
- clustering summaries
- generated figures
- customer segment assignments

This mimics a production analytics environment where results can be shared outside the application.

---

# Reproducibility

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Run the Project

Prepare the data

```bash
python scripts/prepare_data.py
```

Build the SQLite warehouse

```bash
python scripts/build_database.py
```

Generate SQL reports

```bash
python scripts/run_sql_reports.py
```

Run clustering

```bash
python scripts/clustering.py
```

Generate statistical analysis

```bash
python scripts/statistical_analysis.py
```

Export dashboard data

```bash
python scripts/export_dashboard_data.py
```

Launch Streamlit

```bash
streamlit run app/app.py
```

---

# Key Features

✅ End-to-end analytics pipeline

✅ SQLite data warehouse

✅ Automated SQL reporting

✅ Reusable Python modules

✅ Multiple clustering algorithms

✅ Statistical model comparison

✅ Interactive dashboard

✅ Downloadable reports

✅ Business-oriented interpretation

✅ Production-inspired project structure

---

# Learning Objectives

This project demonstrates practical skills in

- data cleaning
- feature engineering
- SQL analytics
- database design
- unsupervised machine learning
- statistical model validation
- visualization
- dashboard development
- software organization
- reproducible analytics workflows

---

# Future Improvements

Potential extensions include

- incremental data ingestion
- scheduled ETL
- customer lifetime value prediction
- churn prediction
- anomaly detection
- experiment tracking
- Docker deployment
- cloud database integration
- CI/CD workflows
- automated testing pipeline

---

# License

This repository is intended for educational and portfolio purposes.