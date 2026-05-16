"""pytest が `invoice_generator` パッケージを import できるよう sys.path を整える。

`pip install -e .` 済みであれば不要だが、未インストールでも pytest が動くようにフォールバック。
"""
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent / "app"
if _APP_DIR.exists() and str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
