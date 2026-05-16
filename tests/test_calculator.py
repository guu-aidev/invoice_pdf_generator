import pandas as pd
import pytest

from invoice_generator.calculator import calculate


def _df(rows):
    return pd.DataFrame(rows)


def test_single_rate_10pct():
    df = _df([
        {"item_name": "A", "quantity": 1, "unit": "式", "unit_price": 150000, "tax_rate": 0.10},
        {"item_name": "B", "quantity": 3, "unit": "h", "unit_price": 15000, "tax_rate": 0.10},
        {"item_name": "C", "quantity": 1, "unit": "ヶ月", "unit_price": 30000, "tax_rate": 0.10},
    ])
    r = calculate(df)
    assert r["subtotal"] == 225000
    assert r["tax_total"] == 22500
    assert r["grand_total"] == 247500
    assert r["by_rate"][0.10] == {"subtotal": 225000, "tax": 22500}


def test_mixed_rates():
    df = _df([
        {"item_name": "A", "quantity": 1, "unit": "式", "unit_price": 100000, "tax_rate": 0.10},
        {"item_name": "B", "quantity": 1, "unit": "冊", "unit_price": 3000, "tax_rate": 0.08},
    ])
    r = calculate(df)
    assert r["by_rate"][0.10] == {"subtotal": 100000, "tax": 10000}
    assert r["by_rate"][0.08] == {"subtotal": 3000, "tax": 240}
    assert r["grand_total"] == 113240


def test_tax_floor():
    df = _df([
        {"item_name": "A", "quantity": 1, "unit": "式", "unit_price": 333, "tax_rate": 0.10},
    ])
    r = calculate(df)
    # 333 * 0.10 = 33.3 → 切り捨て = 33
    assert r["tax_total"] == 33
    assert r["grand_total"] == 366


def test_quantity_multiplied():
    df = _df([
        {"item_name": "A", "quantity": 2, "unit": "件", "unit_price": 50000, "tax_rate": 0.10},
    ])
    r = calculate(df)
    assert r["rows"][0]["amount"] == 100000
    assert r["grand_total"] == 110000


def test_empty():
    df = _df([]).reindex(columns=["item_name", "quantity", "unit", "unit_price", "tax_rate"])
    r = calculate(df)
    assert r["subtotal"] == 0
    assert r["tax_total"] == 0
    assert r["grand_total"] == 0
    assert r["rows"] == []
