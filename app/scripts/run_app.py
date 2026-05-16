"""PyInstaller 用のトップレベルエントリスクリプト。

- 引数なし: GUI を起動（exe ダブルクリック相当）
- 引数あり: CLI として動作
"""
import sys
from pathlib import Path

# プロジェクトルート (このファイルから2階層上) を sys.path に追加し、
# `invoice_generator` パッケージを import 可能にする。
_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

if __name__ == "__main__":
    if len(sys.argv) == 1:
        from invoice_generator.gui import run
        run()
    else:
        from invoice_generator.main import main
        raise SystemExit(main())
