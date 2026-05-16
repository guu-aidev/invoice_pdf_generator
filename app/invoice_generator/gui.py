import json
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMenu, QMessageBox, QPushButton, QSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

from .calculator import calculate
from .core import generate_invoices
from .loader import load_clients, load_items

APP_TITLE = "請求書ジェネレーター"
SETTINGS_FILE = "settings.json"

DARK = "#1a1a2e"
DARK2 = "#252540"
DARK_HOVER = "#202035"
ACCENT = "#4a9eff"
LIGHT_BG = "#f5f6fa"
CARD_BG = "#ffffff"
BORDER = "#e1e4ea"
MUTED = "#7a8294"
SUCCESS = "#2da44e"
SIDEBAR_TEXT = "#ccd6f6"

SIDEBAR_WIDTH = 180

STYLESHEET = f"""
* {{ font-family: "Yu Gothic UI", "Meiryo UI", sans-serif; }}

QWidget#sidebar {{ background-color: {DARK}; }}

QPushButton#sidebarTab {{
    background: transparent;
    color: {SIDEBAR_TEXT};
    border: none;
    border-left: 4px solid transparent;
    padding: 14px 16px;
    text-align: left;
    font-size: 13px;
}}
QPushButton#sidebarTab:hover {{ background: {DARK_HOVER}; }}
QPushButton#sidebarTab:checked {{
    background: {DARK2};
    border-left: 4px solid {ACCENT};
    color: #ffffff;
    font-weight: 700;
}}

QPushButton#sidebarSecondary {{
    background: transparent;
    color: {SIDEBAR_TEXT};
    border: 1px solid #3a3a55;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 12px;
}}
QPushButton#sidebarSecondary:hover {{ background: {DARK_HOVER}; }}

QLabel#sidebarProgress {{
    color: #8892b0;
    font-size: 11px;
    padding: 4px 4px;
}}

QWidget#content {{ background-color: {LIGHT_BG}; }}

QLabel#pageTitle {{ font-size: 22px; font-weight: 700; color: {DARK}; }}
QLabel#pageSubtitle {{ font-size: 12px; color: {MUTED}; }}
QLabel#placeholder {{ font-size: 14px; color: {MUTED}; }}

QFrame#card {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QLineEdit, QSpinBox {{
    background: #fafbfc;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    color: #222;
}}
QLineEdit:focus, QSpinBox:focus {{ border: 1px solid {ACCENT}; background: #ffffff; }}
QLineEdit:read-only {{ background: #eef0f4; color: {MUTED}; }}

QPushButton#browse {{
    background: #ffffff;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    color: {DARK};
}}
QPushButton#browse:hover {{ background: #f0f2f7; }}

QToolButton#multiCombo {{
    background: #fafbfc;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    color: #222;
    text-align: left;
}}
QToolButton#multiCombo::menu-indicator {{ subcontrol-position: right center; subcontrol-origin: padding; }}

QPushButton#primary {{
    background: {ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 700;
    font-size: 12px;
}}
QPushButton#primary:hover {{ background: #3a8ae8; }}
QPushButton#primary:disabled {{ background: #c4cad6; color: #ffffff; }}

QPushButton#linkReset {{
    background: transparent;
    border: none;
    color: {ACCENT};
    font-size: 12px;
    text-decoration: underline;
    padding: 4px;
}}
QPushButton#linkReset:hover {{ color: #3a8ae8; }}

QTableWidget {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    gridline-color: #f0f2f5;
    font-size: 12px;
}}
QHeaderView::section {{
    background: #f8f9fb;
    color: {DARK};
    font-weight: 700;
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 6px;
}}
QTableWidget::item {{ padding: 6px 4px; }}
QTableWidget::item:selected {{ background: #e8f1ff; color: #222; }}
"""


# ---- 共通ユーティリティ ----

def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def _settings_path() -> Path:
    return _app_dir() / SETTINGS_FILE


def _load_settings() -> dict:
    p = _settings_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_settings(data: dict) -> None:
    try:
        _settings_path().write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _find_up(base: Path, rel: Path, max_levels: int = 2) -> Path | None:
    p = base
    for _ in range(max_levels + 1):
        target = p / rel
        if target.exists():
            return target
        if p.parent == p:
            break
        p = p.parent
    return None


def _defaults() -> dict[str, str]:
    base = _app_dir()
    rels = {
        "clients": Path("data") / "clients.csv",
        "items": Path("data") / "items",
        "config": Path("config.yaml"),
        "output": Path("output"),
    }
    out: dict[str, str] = {}
    for k, rel in rels.items():
        found = _find_up(base, rel)
        if found:
            out[k] = str(found)
        elif k == "output":
            out[k] = str(base / rel)
        else:
            out[k] = ""
    return out


def _default_month() -> tuple[int, int]:
    today = date.today()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


# ---- ワーカー ----

class Worker(QObject):
    log = Signal(str)
    finished = Signal(int, str)  # count, error_message (空文字なら成功)

    def __init__(self, clients, items, config, year, month, output, target_ids=None):
        super().__init__()
        self.args = (clients, items, config, year, month, output, target_ids)

    def run(self):
        clients, items, config, year, month, output, target_ids = self.args
        try:
            generated = generate_invoices(
                clients_path=Path(clients),
                items_path=Path(items),
                config_path=Path(config),
                year=year, month=month,
                output_dir=Path(output),
                log=self.log.emit,
                target_client_ids=target_ids,
            )
            self.finished.emit(len(generated), "")
        except Exception as e:
            self.finished.emit(0, str(e))


# ---- 取引先複数選択ドロップダウン ----

class MultiSelectCombo(QToolButton):
    """QToolButton + QMenu で「チェック式ドロップダウン」を実現。"""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("multiCombo")
        self.setPopupMode(QToolButton.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.setMinimumWidth(280)
        self._menu = QMenu(self)
        self._menu.aboutToHide.connect(self._on_menu_hide)
        self.setMenu(self._menu)
        self._actions: list[QAction] = []
        self._dirty = False
        self._update_text()

    def set_items(self, items: list[tuple[str, str]]) -> None:
        """items: [(client_id, label)]"""
        self._menu.clear()
        self._actions.clear()
        for cid, label in items:
            a = QAction(f"{cid}  {label}", self._menu)
            a.setCheckable(True)
            a.setChecked(True)
            a.setData(cid)
            a.triggered.connect(self._on_toggled)
            self._menu.addAction(a)
            self._actions.append(a)
        self._update_text()

    def checked_ids(self) -> list[str]:
        return [a.data() for a in self._actions if a.isChecked()]

    def set_all(self, checked: bool) -> None:
        for a in self._actions:
            a.setChecked(checked)
        self._update_text()
        self.changed.emit()

    def _on_toggled(self):
        self._dirty = True
        self._update_text()

    def _on_menu_hide(self):
        if self._dirty:
            self._dirty = False
            self.changed.emit()

    def _update_text(self):
        total = len(self._actions)
        n = len(self.checked_ids())
        if total == 0:
            self.setText("取引先なし")
        elif n == total:
            self.setText(f"すべて ({total}件)")
        elif n == 0:
            self.setText("未選択")
        else:
            self.setText(f"{n} / {total} 件選択中")


# ---- 案件ページ ----

class DealsPage(QWidget):
    request_generate = Signal(list)  # 選択された client_id のリスト

    COL_CHECK = 0
    COL_ID = 1
    COL_CLIENT = 2
    COL_LINES = 3
    COL_AMOUNT = 4
    COL_STATE = 5

    def __init__(self, get_paths_cb, parent=None):
        """get_paths_cb: () -> dict (設定タブのパスを返す)"""
        super().__init__(parent)
        self._get_paths = get_paths_cb
        self._reloading = False  # チェック変更時の自己トリガー回避
        self._build_ui()

    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)

        title = QLabel("案件")
        title.setObjectName("pageTitle")
        v.addWidget(title)

        # フィルタカード
        filter_card = QFrame()
        filter_card.setObjectName("card")
        g = QGridLayout(filter_card)
        g.setContentsMargins(20, 16, 20, 16)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(10)

        g.addWidget(self._label("対象月"), 0, 0)
        mrow = QHBoxLayout()
        mrow.setSpacing(6)
        y, m = _default_month()
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2099)
        self.year_spin.setFixedWidth(90)
        self.year_spin.setValue(y)
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setFixedWidth(70)
        self.month_spin.setValue(m)
        mrow.addWidget(self.year_spin)
        mrow.addWidget(QLabel("年"))
        mrow.addSpacing(8)
        mrow.addWidget(self.month_spin)
        mrow.addWidget(QLabel("月"))
        mrow.addStretch(1)
        mwrap = QWidget()
        mwrap.setLayout(mrow)
        g.addWidget(mwrap, 0, 1, 1, 2)

        g.addWidget(self._label("取引先"), 1, 0)
        self.client_combo = MultiSelectCombo()
        g.addWidget(self.client_combo, 1, 1, 1, 2)

        g.addWidget(self._label("状態"), 2, 0)
        srow = QHBoxLayout()
        srow.setSpacing(16)
        self.chk_pending = QCheckBox("未作成")
        self.chk_done = QCheckBox("作成済")
        self.chk_pending.setChecked(True)
        self.chk_done.setChecked(True)
        srow.addWidget(self.chk_pending)
        srow.addWidget(self.chk_done)
        srow.addStretch(1)
        swrap = QWidget()
        swrap.setLayout(srow)
        g.addWidget(swrap, 2, 1, 1, 2)

        self.reset_btn = QPushButton("リセット")
        self.reset_btn.setObjectName("linkReset")
        self.reset_btn.clicked.connect(self._on_reset)
        g.addWidget(self.reset_btn, 3, 2, alignment=Qt.AlignRight)

        g.setColumnStretch(1, 1)
        v.addWidget(filter_card)

        # 一括操作行
        action_row = QHBoxLayout()
        self.select_all_chk = QCheckBox()
        self.select_all_chk.setTristate(False)
        self.select_all_chk.stateChanged.connect(self._on_select_all)
        action_row.addWidget(self.select_all_chk)
        action_row.addWidget(QLabel("一括操作:"))
        self.generate_btn = QPushButton("請求書作成")
        self.generate_btn.setObjectName("primary")
        self.generate_btn.clicked.connect(self._on_generate)
        action_row.addWidget(self.generate_btn)
        self.count_label = QLabel("0 件 選択中")
        self.count_label.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        action_row.addWidget(self.count_label)
        action_row.addStretch(1)
        v.addLayout(action_row)

        # テーブル
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["", "案件ID", "取引先", "明細", "金額(税込)", "状態"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(self.COL_CHECK, QHeaderView.Fixed)
        hh.setSectionResizeMode(self.COL_ID, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(self.COL_CLIENT, QHeaderView.Stretch)
        hh.setSectionResizeMode(self.COL_LINES, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(self.COL_AMOUNT, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(self.COL_STATE, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(self.COL_CHECK, 36)
        v.addWidget(self.table, 1)

        self.empty_label = QLabel("")
        self.empty_label.setStyleSheet(f"color:{MUTED}; padding:20px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setVisible(False)
        v.addWidget(self.empty_label)

        # フィルタ変更をリアルタイムで反映
        self.year_spin.valueChanged.connect(self._on_filter_changed)
        self.month_spin.valueChanged.connect(self._on_filter_changed)
        self.client_combo.changed.connect(self._on_filter_changed)
        self.chk_pending.toggled.connect(self._on_filter_changed)
        self.chk_done.toggled.connect(self._on_filter_changed)

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size:12px; font-weight:600; color:{DARK};")
        return lbl

    # ---- データロード ----

    def reload(self):
        """設定タブのパス + 自身のフィルタを使ってテーブルを更新。"""
        self._reloading = True
        try:
            paths = self._get_paths()
            clients_path = paths.get("clients", "")
            items_path = paths.get("items", "")
            output_path = paths.get("output", "")

            if not clients_path or not Path(clients_path).exists():
                self._show_empty("⚙ 設定タブで取引先一覧CSVを指定してください。")
                self._set_client_options([])
                return
            if not items_path or not Path(items_path).exists():
                self._show_empty("⚙ 設定タブで明細フォルダを指定してください。")
                self._set_client_options([])
                return

            # 取引先マスタ
            try:
                clients_df = load_clients(clients_path)
            except Exception as e:
                self._show_empty(f"取引先CSVの読み込みに失敗: {e}")
                return

            # 取引先プルダウン更新（取引先マスタ全件をベースに、初回のみ全選択）
            current_checked = set(self.client_combo.checked_ids())
            options = [(r["client_id"], r["client_name"]) for _, r in clients_df.iterrows()]
            if not current_checked:
                self._set_client_options(options, default_all=True)
                current_checked = set(self.client_combo.checked_ids())
            else:
                self._set_client_options(options, default_all=False,
                                         keep_checked=current_checked)

            year = self.year_spin.value()
            month = self.month_spin.value()
            yyyymm = f"{year:04d}{month:02d}"

            # 当月明細
            items_dir = Path(items_path)
            items_file = items_dir / f"{year:04d}-{month:02d}.csv"
            if items_dir.is_file():
                items_file = items_dir  # 直接ファイル指定された場合
            if not items_file.exists():
                self._show_empty(f"{year:04d}年{month:02d}月の明細ファイルがありません。\n（{items_file}）")
                return

            try:
                items_df = load_items(items_file)
            except Exception as e:
                self._show_empty(f"明細CSVの読み込みに失敗: {e}")
                return

            clients_idx = {r["client_id"]: r.to_dict() for _, r in clients_df.iterrows()}
            all_item_ids = sorted(
                cid for cid in items_df["client_id"].unique() if cid in clients_idx
            )

            # 行データを構築（フィルタ前）
            output_dir = Path(output_path) if output_path else None
            allowed_ids = set(self.client_combo.checked_ids())
            want_pending = self.chk_pending.isChecked()
            want_done = self.chk_done.isChecked()

            rows = []
            for seq, cid in enumerate(all_item_ids, start=1):
                # 取引先フィルタ
                if cid not in allowed_ids:
                    continue
                client = clients_idx[cid]
                client_items = items_df[items_df["client_id"] == cid]
                calc = calculate(client_items.reset_index(drop=True))
                generated = self._is_generated(output_dir, yyyymm, cid)
                # 状態フィルタ
                if generated and not want_done:
                    continue
                if (not generated) and not want_pending:
                    continue
                rows.append({
                    "id": f"{yyyymm}-{seq:03d}",
                    "client_id": cid,
                    "client_name": client["client_name"],
                    "lines": len(client_items),
                    "amount": calc["grand_total"],
                    "generated": generated,
                })

            self._fill_table(rows)
            if not rows:
                self._show_empty("条件に一致する案件はありません。")
            else:
                self.empty_label.setVisible(False)
                self.table.setVisible(True)
        finally:
            self._reloading = False
            self._update_count_label()

    def _set_client_options(self, options, default_all: bool = True,
                            keep_checked: set | None = None):
        self.client_combo._menu.blockSignals(True)
        self.client_combo.set_items(options)
        if keep_checked is not None:
            for a in self.client_combo._actions:
                a.setChecked(a.data() in keep_checked)
            self.client_combo._update_text()
        elif not default_all:
            for a in self.client_combo._actions:
                a.setChecked(False)
            self.client_combo._update_text()
        self.client_combo._menu.blockSignals(False)

    def _is_generated(self, output_dir: Path | None, yyyymm: str, cid: str) -> bool:
        if not output_dir or not output_dir.exists():
            return False
        return any(output_dir.glob(f"{yyyymm}_{cid}_*.pdf"))

    def _show_empty(self, msg: str):
        self.table.setRowCount(0)
        self.table.setVisible(False)
        self.empty_label.setText(msg)
        self.empty_label.setVisible(True)
        self.select_all_chk.setChecked(False)

    def _fill_table(self, rows):
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            chk = QCheckBox()
            chk.setChecked(False)
            chk.stateChanged.connect(self._update_count_label)
            wrap = QWidget()
            hl = QHBoxLayout(wrap)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(chk)
            hl.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(i, self.COL_CHECK, wrap)

            self.table.setItem(i, self.COL_ID, QTableWidgetItem(r["id"]))
            self.table.setItem(i, self.COL_CLIENT, QTableWidgetItem(r["client_name"]))

            lines_item = QTableWidgetItem(str(r["lines"]))
            lines_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(i, self.COL_LINES, lines_item)

            amount_item = QTableWidgetItem(f"¥{r['amount']:,}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amount_item.setData(Qt.UserRole, int(r["amount"]))
            self.table.setItem(i, self.COL_AMOUNT, amount_item)

            state_item = QTableWidgetItem("作成済 ✓" if r["generated"] else "未作成")
            state_item.setForeground(QColor(SUCCESS if r["generated"] else MUTED))
            self.table.setItem(i, self.COL_STATE, state_item)

            # 行に client_id を仕込む（生成時に使う）
            self.table.item(i, self.COL_ID).setData(Qt.UserRole, r["client_id"])

    # ---- イベント ----

    def _on_filter_changed(self):
        if self._reloading:
            return
        self.reload()

    def _on_reset(self):
        y, m = _default_month()
        self.year_spin.setValue(y)
        self.month_spin.setValue(m)
        self.chk_pending.setChecked(True)
        self.chk_done.setChecked(True)
        self.client_combo.set_all(True)

    def _on_select_all(self, state):
        if self._reloading:
            return
        checked = state == Qt.Checked.value
        for i in range(self.table.rowCount()):
            wrap = self.table.cellWidget(i, self.COL_CHECK)
            if wrap:
                cb = wrap.findChild(QCheckBox)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(checked)
                    cb.blockSignals(False)
        self._update_count_label()

    def _selected_rows(self) -> list[int]:
        rows = []
        for i in range(self.table.rowCount()):
            wrap = self.table.cellWidget(i, self.COL_CHECK)
            if wrap:
                cb = wrap.findChild(QCheckBox)
                if cb and cb.isChecked():
                    rows.append(i)
        return rows

    def _selected_client_ids(self) -> list[str]:
        return [self.table.item(i, self.COL_ID).data(Qt.UserRole) for i in self._selected_rows()]

    def _selected_total_amount(self) -> int:
        total = 0
        for i in self._selected_rows():
            amt = self.table.item(i, self.COL_AMOUNT).data(Qt.UserRole)
            if amt is not None:
                total += int(amt)
        return total

    def _selected_already_generated_count(self) -> int:
        n = 0
        for i in self._selected_rows():
            state = self.table.item(i, self.COL_STATE).text()
            if "作成済" in state:
                n += 1
        return n

    def _update_count_label(self):
        n = len(self._selected_client_ids())
        if n == 0:
            self.count_label.setText("0 件 選択中")
        else:
            total = self._selected_total_amount()
            self.count_label.setText(f"{n} 件 選択中(合計 ¥{total:,})")
        self.generate_btn.setEnabled(n > 0)

    def _on_generate(self):
        ids = self._selected_client_ids()
        if not ids:
            return
        already = self._selected_already_generated_count()
        if already > 0:
            msg = (f"選択された {len(ids)} 件のうち {already} 件は既に作成済です。\n"
                   "上書きしますか?")
            reply = QMessageBox.question(
                self, APP_TITLE, msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        year = self.year_spin.value()
        month = self.month_spin.value()
        self.request_generate.emit([year, month, ids])


# ---- メインウィンドウ ----

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(960, 680)
        self.settings = _load_settings()
        self._thread: QThread | None = None
        self._build_ui()
        self._restore_settings()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_sidebar())
        outer.addWidget(self._build_content(), 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        v = QVBoxLayout(sidebar)
        v.setContentsMargins(0, 16, 0, 16)
        v.setSpacing(0)

        self.tab_settings = self._make_tab_btn("⚙   設定")
        self.tab_deals = self._make_tab_btn("📋   案件")
        self.tab_deals.setChecked(True)
        for i, btn in enumerate((self.tab_settings, self.tab_deals)):
            btn.toggled.connect(lambda checked, idx=i: checked and self._on_tab_changed(idx))
            v.addWidget(btn)
        v.addStretch(1)

        action_wrap = QWidget()
        av = QVBoxLayout(action_wrap)
        av.setContentsMargins(12, 8, 12, 4)
        av.setSpacing(8)
        self.open_btn = QPushButton("出力フォルダを開く")
        self.open_btn.setObjectName("sidebarSecondary")
        self.open_btn.clicked.connect(self._open_output)
        av.addWidget(self.open_btn)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("sidebarProgress")
        self.progress_label.setWordWrap(True)
        av.addWidget(self.progress_label)
        v.addWidget(action_wrap)
        return sidebar

    def _make_tab_btn(self, text):
        b = QPushButton(text)
        b.setObjectName("sidebarTab")
        b.setCheckable(True)
        b.setAutoExclusive(True)
        b.setCursor(Qt.PointingHandCursor)
        return b

    def _build_content(self) -> QWidget:
        content = QWidget()
        content.setObjectName("content")
        v = QVBoxLayout(content)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_settings_page())
        self.deals_page = DealsPage(get_paths_cb=self._current_paths)
        self.deals_page.request_generate.connect(self._on_deals_generate)
        self.stack.addWidget(self.deals_page)
        self.stack.setCurrentIndex(1)  # 案件タブを初期表示
        v.addWidget(self.stack)
        return content

    def _build_settings_page(self) -> QWidget:
        # 入力欄ごとの妥当性アイコン: edit -> (QLabel, kind)
        # kind: "file" / "dir" / "outdir"
        self._validity_icons: dict = {}

        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)
        title = QLabel("設定")
        title.setObjectName("pageTitle")
        sub = QLabel("ファイルパスや自社情報を設定します。")
        sub.setObjectName("pageSubtitle")
        v.addWidget(title)
        v.addWidget(sub)

        card = QFrame()
        card.setObjectName("card")
        form = QGridLayout(card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)
        self.clients_edit = self._add_file_row(form, 0, "取引先一覧CSV", "CSV (*.csv)", kind="file")
        self.items_edit = self._add_dir_row(form, 1, "明細フォルダ", kind="dir")
        self.config_edit = self._add_readonly_row(form, 2, "自社設定 (YAML)", kind="file")
        self.output_edit = self._add_readonly_row(form, 3, "出力先フォルダ", kind="outdir")
        form.setColumnStretch(1, 1)
        v.addWidget(card)
        v.addStretch(1)
        return page

    def _build_placeholder_page(self, title_text, msg) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)
        title = QLabel(title_text)
        title.setObjectName("pageTitle")
        v.addWidget(title)
        wrap = QFrame()
        wrap.setObjectName("card")
        wv = QVBoxLayout(wrap)
        wv.setContentsMargins(40, 60, 40, 60)
        ph = QLabel(f"🚧  {msg}")
        ph.setObjectName("placeholder")
        ph.setAlignment(Qt.AlignCenter)
        wv.addWidget(ph)
        v.addWidget(wrap)
        v.addStretch(1)
        return page

    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)
        if idx == 1:  # 案件タブ
            self.deals_page.reload()

    # ---- フィールドヘルパー ----
    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size:12px; font-weight:600; color:{DARK};")
        return lbl

    def _make_validity_icon(self) -> QLabel:
        icon = QLabel("")
        icon.setFixedWidth(18)
        icon.setAlignment(Qt.AlignCenter)
        return icon

    def _add_file_row(self, form, row, label, filt, kind="file"):
        form.addWidget(self._field_label(label), row, 0)
        edit = QLineEdit()
        edit.textChanged.connect(self._on_settings_changed)
        btn = QPushButton("参照…")
        btn.setObjectName("browse")
        btn.clicked.connect(lambda: self._pick_file(edit, filt))
        icon = self._make_validity_icon()
        form.addWidget(edit, row, 1)
        form.addWidget(btn, row, 2)
        form.addWidget(icon, row, 3)
        self._validity_icons[edit] = (icon, kind)
        return edit

    def _add_dir_row(self, form, row, label, kind="dir"):
        form.addWidget(self._field_label(label), row, 0)
        edit = QLineEdit()
        edit.textChanged.connect(self._on_settings_changed)
        btn = QPushButton("参照…")
        btn.setObjectName("browse")
        btn.clicked.connect(lambda: self._pick_dir(edit))
        icon = self._make_validity_icon()
        form.addWidget(edit, row, 1)
        form.addWidget(btn, row, 2)
        form.addWidget(icon, row, 3)
        self._validity_icons[edit] = (icon, kind)
        return edit

    def _add_readonly_row(self, form, row, label, kind="file"):
        form.addWidget(self._field_label(label), row, 0)
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.textChanged.connect(self._on_settings_changed)
        icon = self._make_validity_icon()
        form.addWidget(edit, row, 1, 1, 2)
        form.addWidget(icon, row, 3)
        self._validity_icons[edit] = (icon, kind)
        return edit

    def _update_settings_validity(self):
        for edit, (icon, kind) in self._validity_icons.items():
            text = edit.text().strip()
            if not text:
                icon.setText("⚠")
                icon.setStyleSheet(f"color:{MUTED}; font-size:14px;")
                icon.setToolTip("未設定")
                continue
            p = Path(text)
            if kind == "file":
                ok = p.is_file()
            elif kind == "dir":
                ok = p.is_dir()
            elif kind == "outdir":
                ok = p.exists() or (p.parent.exists() and p.parent.is_dir())
            else:
                ok = p.exists()
            if ok:
                icon.setText("✓")
                icon.setStyleSheet(f"color:{SUCCESS}; font-size:14px; font-weight:700;")
                icon.setToolTip("OK")
            else:
                icon.setText("⚠")
                icon.setStyleSheet("color:#dd6b20; font-size:14px; font-weight:700;")
                icon.setToolTip("ファイル/フォルダが見つかりません")

    def _pick_file(self, edit, filt):
        current = edit.text() or str(_app_dir())
        path, _ = QFileDialog.getOpenFileName(
            self, "ファイルを選択", str(Path(current).parent), f"{filt};;すべて (*.*)"
        )
        if path:
            edit.setText(path)

    def _pick_dir(self, edit):
        current = edit.text() or str(_app_dir())
        path = QFileDialog.getExistingDirectory(self, "フォルダを選択", current)
        if path:
            edit.setText(path)

    def _on_settings_changed(self):
        self._update_settings_validity()
        # 案件タブが現在表示中なら即反映
        if self.stack.currentIndex() == 1:
            self.deals_page.reload()

    # ---- アクション ----
    def _open_output(self):
        out = self.output_edit.text().strip()
        if not out:
            QMessageBox.information(self, APP_TITLE, "出力先フォルダが未設定です。")
            return
        p = Path(out)
        if not p.exists():
            QMessageBox.warning(self, APP_TITLE, "出力先フォルダが存在しません。")
            return
        try:
            os.startfile(str(p))
        except Exception as e:
            QMessageBox.critical(self, APP_TITLE, f"フォルダを開けませんでした:\n{e}")

    def _current_paths(self) -> dict:
        return {
            "clients": self.clients_edit.text().strip(),
            "items": self.items_edit.text().strip(),
            "config": self.config_edit.text().strip(),
            "output": self.output_edit.text().strip(),
        }

    def _on_deals_generate(self, payload: list):
        year, month, target_ids = payload
        paths = self._current_paths()
        for label, p in [("取引先一覧CSV", paths["clients"]),
                          ("明細フォルダ", paths["items"]),
                          ("自社設定YAML", paths["config"])]:
            if not p or not Path(p).exists():
                QMessageBox.critical(self, APP_TITLE, f"{label} を設定タブで正しく指定してください。")
                return

        self.deals_page.generate_btn.setEnabled(False)
        self.deals_page.generate_btn.setText("処理中…")
        self.progress_label.setText("準備中…")

        self._thread = QThread(self)
        self._worker = Worker(
            paths["clients"], paths["items"], paths["config"],
            year, month, paths["output"], target_ids=target_ids,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_log(self, msg: str):
        short = msg.strip()
        if len(short) > 26:
            short = short[:25] + "…"
        self.progress_label.setText(short)

    def _on_worker_done(self, count: int, err: str):
        self.deals_page.generate_btn.setEnabled(True)
        self.deals_page.generate_btn.setText("請求書作成")
        if err:
            self.progress_label.setText("× エラー")
            QMessageBox.critical(self, APP_TITLE, f"エラーが発生しました:\n{err}")
        else:
            self.progress_label.setText(f"✓ 完了 ({count} 件)")
            QMessageBox.information(self, APP_TITLE, f"{count} 件のPDFを生成しました。")
        # 状態カラムを更新
        self.deals_page.reload()

    # ---- 設定の永続化 ----
    def _restore_settings(self):
        s = self.settings
        d = _defaults()
        self.clients_edit.setText(s.get("clients") or d["clients"])
        self.items_edit.setText(s.get("items") or d["items"])
        self.config_edit.setText(d["config"])
        self.output_edit.setText(d["output"])
        self._update_settings_validity()
        # 初期表示として案件タブをロード
        self.deals_page.reload()

    def closeEvent(self, event):
        _save_settings({
            "clients": self.clients_edit.text(),
            "items": self.items_edit.text(),
        })
        super().closeEvent(event)


def _apply_palette(app: QApplication):
    app.setStyle("Fusion")
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(LIGHT_BG))
    pal.setColor(QPalette.Base, QColor(CARD_BG))
    pal.setColor(QPalette.Text, QColor("#222222"))
    pal.setColor(QPalette.WindowText, QColor(DARK))
    pal.setColor(QPalette.Button, QColor(CARD_BG))
    pal.setColor(QPalette.ButtonText, QColor(DARK))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)
    app.setStyleSheet(STYLESHEET)


def run() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    _apply_palette(app)
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    run()
