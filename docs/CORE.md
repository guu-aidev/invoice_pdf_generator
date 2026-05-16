# CORE — 処理設計

CSVから請求書PDFを生成するパイプライン。GUIとCLIから共通で呼ばれる中核。

---

## データフロー

```
┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐
│ data/clients.csv│    │ data/items/     │    │ config.yaml  │
│ (取引先マスタ)   │    │   {YYYY-MM}.csv │    │ (自社情報)    │
└────────┬────────┘    └────────┬────────┘    └──────┬───────┘
         │                      │                    │
         ▼                      ▼                    ▼
       loader.load_clients / load_items / load_config
         │                      │                    │
         └──────────┬───────────┴────────────────────┘
                    ▼
          core.generate_invoices()
            │
            ├─ groupby(client_id)
            │     │
            │     ▼
            │   calculator.calculate()  ── 税率別 小計/税額/合計(切り捨て)
            │     │
            │     ▼
            │   pdf_renderer.render_invoice()  ── ReportLab で1ページPDF
            │
            └─→ output/{YYYYMM}_{client_id}_{client_name}.pdf
```

## モジュール責務

| ファイル | 責務 | 主な関数 |
|---|---|---|
| `core.py` | パイプライン統合 | `generate_invoices()` |
| `loader.py` | CSV/YAML読込・文字コード自動判定 | `load_clients()` / `load_items()` / `load_config()` |
| `calculator.py` | 税率別 集計 | `calculate(items_df)` |
| `pdf_renderer.py` | PDF描画 (ReportLab) | `render_invoice()` |
| `main.py` | CLI (argparse) | `main(argv)` |

---

## 重要な設計判断（なぜそうしたか）

### 1. CSV文字コード自動判定
試行順: **`utf-8-sig` → `cp932` → `utf-8`**

→ Excelの「CSV (コンマ区切り)」(Shift-JIS) と「CSV UTF-8 (コンマ区切り)」(BOM付き) 両方をユーザー意識なしで読める。

### 2. 月別アーカイブ `data/items/{YYYY-MM}.csv`
1ファイルではなく月単位のフォルダ運用。

| メリット | |
|---|---|
| 過去案件の再発行が容易 | 対象月を変えるだけ |
| 履歴が残る | バックアップしやすい |

`core._resolve_items_file()` がフォルダ指定時に `{year:04d}-{month:02d}.csv` を解決。**直接ファイル指定も後方互換**で受け付ける。

### 3. 税額計算は切り捨て（`math.floor`）
税率ごとに小計を出してから税額を計算 → インボイス制度の典型処理。

```python
for rate, vals in by_rate.items():
    vals["tax"] = math.floor(vals["subtotal"] * rate)
```

### 4. 案件ID = `{YYYYMM}-{seq:03d}`
`seq` は items.csv 内の `client_id` ソート順で 1 始まり。`target_client_ids` で絞り込んでも採番順は維持。

### 5. 状態判定 = 出力ファイルの存在
DBなし。`output/{YYYYMM}_{client_id}_*.pdf` をグロブして発見できれば「作成済」。

```python
def is_generated(output_dir, yyyymm, cid):
    return any(output_dir.glob(f"{yyyymm}_{cid}_*.pdf"))
```

### 6. 部分生成 `target_client_ids`
GUI の案件タブから「選択行だけ生成」を実現するため `generate_invoices()` に追加。`None` なら全件。

---

## 拡張ポイント

| やりたいこと | 修正箇所 |
|---|---|
| CSV列を追加 | `loader.py` の `CLIENTS_REQUIRED` / `ITEMS_REQUIRED` 配列 |
| 新しい計算ロジック | `calculator.py` に関数追加 → `core.py` から呼ぶ |
| PDFレイアウト変更 | `pdf_renderer.py` の `_items_table()` / `_summary_table()` 等 |
| 自社情報の項目追加 | `config.yaml` + `pdf_renderer._issuer_html()` |
| 別の出力形式 (Excel等) | `core.py` で `render_invoice()` の代わりに新エンジン呼出し |

---

## 既知の落とし穴

| 罠 | 対策 |
|---|---|
| Windows コンソールが `¥` を出せない (cp932) | `main.py` 冒頭で `sys.stdout.reconfigure(encoding="utf-8")` |
| 取引先名を後で変更 → 古いPDFが状態判定でヒットしない | グロブは `client_id` で行うため発生 (`client_name` 部分はワイルドカード) |
| ReportLab の日本語フォント | CIDフォント `HeiseiKakuGo-W5` を `UnicodeCIDFont` で登録 (PyInstaller時は `--collect-data reportlab` 必須) |
| `data/items/{YYYY-MM}.csv` が無い月を指定 | `_resolve_items_file()` が `FileNotFoundError` + 親切メッセージ |

---

## テスト
- 単体: `tests/test_calculator.py` (税率混在・端数切り捨て・空明細)
- 統合: 手動で `python -m invoice_generator.main --month YYYY-MM ...`
