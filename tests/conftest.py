from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def raw_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TransactionID": ["T1", "T2", "T3", "T4"],
            "CustomerID": ["C1", "C1", "C2", "C3"],
            "CustomerDOB": ["10/1/94", "10/1/94", "1/1/1800", "4/4/57"],
            "CustGender": ["F", "F", "T", "M"],
            "CustLocation": [" mumbai ", "MUMBAI", None, "JHAJJAR"],
            "CustAccountBalance": [1000.0, 1200.0, 500.0, 2000.0],
            "TransactionDate": ["2/8/16", "3/8/16", "2/8/16", "2/8/16"],
            "TransactionTime": [143207, 93015, 250000, 141858],
            "TransactionAmount (INR)": [25.0, 50.0, 100.0, 200.0],
        }
    )
