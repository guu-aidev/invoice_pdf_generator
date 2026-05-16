import argparse
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _parse_month(s: str) -> tuple[int, int]:
    y, m = s.split("-")
    return int(y), int(m)


def main(argv: list[str] | None = None) -> int:
    from .core import generate_invoices

    ap = argparse.ArgumentParser(description="月次請求書 一括PDF生成ツール")
    ap.add_argument("--clients", required=True, help="取引先一覧CSV")
    ap.add_argument("--items", required=True, help="当月明細CSV または 明細フォルダ（フォルダ指定時は {YYYY-MM}.csv を自動選択）")
    ap.add_argument("--config", required=True, help="自社情報 YAML")
    ap.add_argument("--month", required=True, help="対象月 YYYY-MM")
    ap.add_argument("--output-dir", required=True, help="PDF出力先ディレクトリ")
    args = ap.parse_args(argv)

    year, month = _parse_month(args.month)
    try:
        generate_invoices(
            clients_path=Path(args.clients),
            items_path=Path(args.items),
            config_path=Path(args.config),
            year=year,
            month=month,
            output_dir=Path(args.output_dir),
            log=print,
        )
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # 引数なし起動（exe ダブルクリック等）→ GUI を立ち上げる
    if len(sys.argv) == 1:
        from .gui import run as run_gui
        run_gui()
    else:
        raise SystemExit(main())
