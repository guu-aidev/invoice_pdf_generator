import math
from collections import defaultdict

import pandas as pd


def calculate(items_df: pd.DataFrame) -> dict:
    rows = []
    by_rate: dict[float, dict[str, int]] = defaultdict(lambda: {"subtotal": 0, "tax": 0})

    for _, row in items_df.iterrows():
        qty = float(row["quantity"])
        price = int(row["unit_price"])
        amount = int(qty * price)
        rate = float(row["tax_rate"])
        rows.append({
            "item_name": str(row["item_name"]),
            "quantity": qty,
            "unit": str(row["unit"]),
            "unit_price": price,
            "amount": amount,
            "tax_rate": rate,
        })
        by_rate[rate]["subtotal"] += amount

    # 税額は税率ごとの小計に対して算出し、円未満は切り捨て（インボイス制度の典型処理）。
    for rate, vals in by_rate.items():
        vals["tax"] = math.floor(vals["subtotal"] * rate)

    subtotal = sum(v["subtotal"] for v in by_rate.values())
    tax_total = sum(v["tax"] for v in by_rate.values())

    return {
        "rows": rows,
        "by_rate": dict(by_rate),
        "subtotal": subtotal,
        "tax_total": tax_total,
        "grand_total": subtotal + tax_total,
    }
