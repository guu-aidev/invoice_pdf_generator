import calendar
from datetime import date
from pathlib import Path
from typing import Callable

from .calculator import calculate
from .loader import load_clients, load_config, load_items
from .pdf_renderer import render_invoice


def _safe_filename(name: str) -> str:
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name


def _resolve_items_file(items_path: str | Path, year: int, month: int) -> Path:
    """items_path がフォルダなら `{YYYY-MM}.csv` を解決、ファイルならそのまま返す。"""
    p = Path(items_path)
    if p.is_dir():
        target = p / f"{year:04d}-{month:02d}.csv"
        if not target.exists():
            raise FileNotFoundError(
                f"対象月のファイルが見つかりません: {target}\n"
                f"（{p} に '{year:04d}-{month:02d}.csv' を配置してください）"
            )
        return target
    return p


def generate_invoices(
    clients_path: str | Path,
    items_path: str | Path,
    config_path: str | Path,
    year: int,
    month: int,
    output_dir: str | Path,
    log: Callable[[str], None] = print,
    target_client_ids: list[str] | None = None,
) -> list[Path]:
    """取引先ごとに請求書PDFを生成し、生成されたファイルパスのリストを返す。

    target_client_ids: 指定した client_id のみ生成する。None なら全件。
        案件IDの採番順序を保つため、絞り込み後も全体ソート順での seq を維持する。
    log: 進捗を1行ずつ通知するコールバック（GUIではログ欄に流す）。
    """
    issue_d = date(year, month, 1)
    due_d = date(year, month, calendar.monthrange(year, month)[1])
    yyyymm = f"{year:04d}{month:02d}"

    items_file = _resolve_items_file(items_path, year, month)
    log(f"明細ファイル: {items_file}")
    clients = load_clients(clients_path)
    items = load_items(items_file)
    config = load_config(config_path)
    issuer = config["issuer"]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    clients_idx = {row["client_id"]: row.to_dict() for _, row in clients.iterrows()}
    item_ids = list(items["client_id"].unique())

    for cid in item_ids:
        if cid not in clients_idx:
            log(f"[WARN] client_id={cid} は clients.csv に存在しません — スキップ")

    all_targets = sorted(cid for cid in item_ids if cid in clients_idx)
    target_set = set(target_client_ids) if target_client_ids is not None else None
    pending = [c for c in all_targets if target_set is None or c in target_set]
    generated: list[Path] = []

    pending_total = len(pending)
    done = 0
    for seq, cid in enumerate(all_targets, start=1):
        if cid not in pending:
            continue
        done += 1
        client = clients_idx[cid]
        client_items = items[items["client_id"] == cid].reset_index(drop=True)
        calc = calculate(client_items)
        invoice_no = f"{yyyymm}-{seq:03d}"
        fname = _safe_filename(f"{yyyymm}_{cid}_{client['client_name']}.pdf")
        out_file = out_dir / fname

        log(f"[{done}/{pending_total}] {cid} {client['client_name']} を生成中…")
        render_invoice(
            out_file,
            issuer=issuer,
            client=client,
            items_calc=calc,
            invoice_no=invoice_no,
            issue_date=issue_d.strftime("%Y年%m月%d日"),
            due_date=due_d.strftime("%Y年%m月%d日"),
            contact_person=client["contact_name"],
        )
        log(f"  → {out_file.name}  合計 ¥{calc['grand_total']:,}")
        generated.append(out_file)

    log(f"完了: {len(generated)} 件のPDFを {out_dir} に生成しました。")
    return generated
