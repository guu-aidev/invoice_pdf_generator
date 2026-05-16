"""PyInstaller でGUI付きexeをビルドするヘルパー。

使い方（プロジェクトルートから）:
    pip install -e ".[dev]"
    python app/scripts/build_exe.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

# このファイル: app/scripts/build_exe.py → 2階層上がプロジェクトルート
ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = ROOT / "app"
APP_NAME = "請求書ジェネレーター"
ENTRY = APP_DIR / "scripts" / "run_app.py"


def main() -> int:
    # 既存の build/ と spec ファイルだけ掃除（dist/ はユーザー資産があるかもしれないので残す）
    for p in (ROOT / "build", ROOT / f"{APP_NAME}.spec"):
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--collect-data", "reportlab",
        "--collect-submodules", "PySide6",
        "--collect-binaries", "PySide6",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6",
        "--paths", str(APP_DIR),  # invoice_generator パッケージを認識させる
        "--specpath", str(ROOT),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--noconfirm",
        str(ENTRY),
    ]
    print(">>> " + " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
