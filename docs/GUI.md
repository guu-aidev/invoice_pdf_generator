# GUI — 画面設計

PySide6 (Qt 6) 製のデスクトップGUI。Fusion + カスタム QSS でモダンなSaaS風レイアウト。

---

## 画面構成

```
┌──────────────────────────────────────────────────────────┐
│ 請求書ジェネレーター                                 ─ □ × │
├──────────┬───────────────────────────────────────────────┤
│ ⚙ 設定   │                                               │
│┃📋 案件  │   QStackedWidget (タブごとに切替)              │
│          │                                               │
│          │    index 0: SettingsPage (パス4つ + ✓/⚠)      │
│          │    index 1: DealsPage (フィルタ + テーブル)    │
│          │                                               │
│  ↕       │                                               │
│          │                                               │
│ ────    │                                               │
│ [出力フ  │                                               │
│  ォルダ] │                                               │
│ 進捗ラベル│                                               │
└──────────┴───────────────────────────────────────────────┘
   ↑ サイドバー(180px,ダーク)
```

---

## クラス構成と責務

```
QMainWindow (MainWindow)
 ├─ サイドバー (QWidget)
 │   ├─ タブボタン × 2 (QPushButton checkable)
 │   ├─ 出力フォルダを開くボタン
 │   └─ 進捗ラベル (QLabel)
 │
 └─ QStackedWidget
     ├─ [0] 設定ページ (QWidget内蔵)
     │     └─ 4つのパスフィールド + validity icon
     │
     └─ [1] DealsPage (QWidget)
            ├─ フィルタカード
            │   ├─ 対象月 (QSpinBox × 2)
            │   ├─ 取引先 (MultiSelectCombo)
            │   └─ 状態   (QCheckBox × 2)
            ├─ 一括操作行 (全選択 + 請求書作成ボタン + 件数/金額ラベル)
            └─ QTableWidget (案件一覧)
```

| クラス | 役割 |
|---|---|
| `MainWindow` | 全体構築・設定タブ・設定永続化・ワーカー管理 |
| `DealsPage` | 案件タブ全体。フィルタ・テーブル描画・選択生成リクエスト発火 |
| `MultiSelectCombo` | 取引先複数選択ドロップダウン（QToolButton + QMenu + チェック式 QAction） |
| `Worker` | バックグラウンドで `core.generate_invoices()` を呼ぶ (QThread に moveToThread) |

---

## データフロー

### 起動 → 案件一覧表示
```
MainWindow.__init__
  └─ _restore_settings()
        ├─ パスを settings.json から復元 (なければ _defaults())
        ├─ _update_settings_validity()  ← ✓/⚠
        └─ deals_page.reload()
              ├─ load_clients(), load_items()
              ├─ groupby + calculate (件数・金額算出)
              ├─ output/ をグロブして状態判定
              └─ QTableWidget に反映
```

### フィルタ変更 → リアルタイム再描画
```
year/month/取引先/状態 → 任意の Signal
  └─ DealsPage._on_filter_changed
        └─ reload()  ← 上記と同じ
```

### 「請求書作成」押下 → 別スレッドで生成
```
DealsPage._on_generate
  ├─ 既に「作成済」を含む場合: QMessageBox.question で上書き確認
  └─ request_generate.emit([year, month, ids])
       └─ MainWindow._on_deals_generate
             ├─ Worker 生成 → QThread に moveToThread → start()
             └─ Worker.log / finished シグナルで UI 更新
                   ├─ 進捗ラベル更新 (log)
                   └─ 完了時: ダイアログ + deals_page.reload() (状態列再描画)
```

---

## 重要な実装ポイント

### 1. スレッド処理（UI凍結回避）
- `QThread` + `Worker (QObject)` の組み合わせ
- `Worker.log: Signal(str)` でUIスレッドに進捗通知
- `moveToThread()` パターンで `QThread` をサブクラス化しない（推奨パターン）

### 2. 設定の永続化
- `settings.json` をexe同階層に保存
- `config / output` パスは読取専用 → settings には保存しない (常にデフォルト)
- `clients / items` パスのみユーザー変更可 → settings に保存

### 3. デフォルトパスの自動検出 (`_find_up()`)
```python
def _find_up(base, rel, max_levels=2):
    """base から rel を探索、見つからなければ親ディレクトリも"""
```
→ exe を `dist/` から直接起動してもプロジェクトルートの `config.yaml` / `data/` を拾える。

### 4. 状態判定 (DBなし)
```python
output_dir.glob(f"{yyyymm}_{cid}_*.pdf")
```
→ ファイルがあれば「作成済 ✓」(緑)、なければ「未作成」(グレー)

### 5. 上書き確認ダイアログ
`DealsPage._on_generate` で選択行に「作成済」が含まれていれば `QMessageBox.question`。
→ 既送付済の請求書を間違って上書きする事故を防止。

### 6. パス validity アイコン (`_update_settings_validity()`)
- `file` / `dir` / `outdir` の3種で `Path.is_file()` / `is_dir()` を判定
- `outdir` は親が存在すれば OK 扱い（実行時に自動作成されるため）
- アイコンは ✓(緑) / ⚠(オレンジ)

### 7. 文字化け対策
- `main.py` 冒頭で `sys.stdout.reconfigure(encoding="utf-8")` (cp932回避)
- GUIテキストは元から UTF-8 で問題なし

---

## スタイリング

| 用途 | 色 |
|---|---|
| サイドバー背景 | `#1a1a2e` (DARK) |
| アクセント | `#4a9eff` (ACCENT) |
| 成功・OK | `#2da44e` (SUCCESS) |
| 警告 | `#dd6b20` |
| カード背景 | `#ffffff` (CARD_BG) |
| ページ背景 | `#f5f6fa` (LIGHT_BG) |

QSS は `gui.py` 内の `STYLESHEET` 定数に集約。各ウィジェットは `setObjectName()` で識別 (`sidebarTab`, `card`, `primary` 等)。

---

## 拡張ポイント

| やりたいこと | 修正箇所 |
|---|---|
| 新タブ追加 | `MainWindow._build_content()` の `stack.addWidget()` + サイドバーに `_make_tab_btn()` 追加 |
| 新フィルタ追加 | `DealsPage._build_ui()` でウィジェット追加 + `reload()` の絞り込みロジック追加 |
| 新カラム追加 | `DealsPage.COL_*` 定数 + `_fill_table()` |
| 取引先フィルタの方式変更 | `MultiSelectCombo` を差し替え (例: 検索ボックス付きにする) |
| デフォルトの「対象月」変更 | `_default_month()` 関数（現在は前月） |
| 別の状態ラベル追加 | `_fill_table()` の `state_item` 生成 + フィルタ条件 |

---

## ビルド (PyInstaller)

`app/scripts/build_exe.py` 経由。重要な引数:

| 引数 | 役割 |
|---|---|
| `--collect-submodules PySide6` | Qt サブモジュール全部 |
| `--collect-binaries PySide6` | Qt DLL/プラグイン |
| `--exclude-module PyQt5/PyQt6` | 競合する別バインディングを排除 |
| `--collect-data reportlab` | PDFのCIDフォントデータ |
| `--paths app` | `invoice_generator` パッケージを認識 |

→ サイズは約300MB。`--onedir` に変えればフォルダ配布で軽量化可能。

---

## 既知の制約

- バイナリ300MB級（PySide6同梱の代償）
- 「再描画ボタン」なし（フィルタ変更で自動再ロードのため）
- アイコン未設定（PyInstaller標準）
- macOS/Linux未検証（Windows前提）
