from pathlib import Path

import pandas as pd
import yaml

CLIENTS_REQUIRED = [
    "client_id", "client_name", "postal_code", "address", "contact_name",
    "bank_name", "bank_branch", "account_type", "account_number", "account_holder",
]
ITEMS_REQUIRED = ["client_id", "item_name", "quantity", "unit", "unit_price", "tax_rate"]

# Excelの「CSV (コンマ区切り)」(cp932) と「CSV UTF-8 (コンマ区切り)」(utf-8-sig) を
# どちらも自動判定で読み込めるように、優先順で試行する。
_CSV_ENCODINGS = ("utf-8-sig", "cp932", "utf-8")


def _read_csv_auto(path: str | Path, **kwargs) -> pd.DataFrame:
    last_err: Exception | None = None
    for enc in _CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError as e:
            last_err = e
    raise ValueError(
        f"{path}: 文字コードを判別できません（utf-8 / cp932 のいずれにも該当せず）"
    ) from last_err


def load_clients(path: str | Path) -> pd.DataFrame:
    df = _read_csv_auto(path, dtype=str).fillna("")
    _check_columns(df, CLIENTS_REQUIRED, str(path))
    return df


def load_items(path: str | Path) -> pd.DataFrame:
    df = _read_csv_auto(path)
    _check_columns(df, ITEMS_REQUIRED, str(path))
    df["quantity"] = pd.to_numeric(df["quantity"])
    df["unit_price"] = pd.to_numeric(df["unit_price"])
    df["tax_rate"] = pd.to_numeric(df["tax_rate"])
    df["item_name"] = df["item_name"].astype(str)
    df["unit"] = df["unit"].astype(str)
    df["client_id"] = df["client_id"].astype(str)
    return df


def load_config(path: str | Path) -> dict:
    last_err: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with open(path, "r", encoding=enc) as f:
                return yaml.safe_load(f)
        except UnicodeDecodeError as e:
            last_err = e
    raise ValueError(f"{path}: 文字コードを判別できません") from last_err


def _check_columns(df: pd.DataFrame, required: list[str], where: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{where}: 必須列が不足しています -> {missing}")
