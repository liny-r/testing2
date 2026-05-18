# Backtesting the ProntoNLP Earnings-Call ATC Signal

**Course:** LLM-Driven Quant Research  
**Author:** Yueqi Lin  
**Dataset:** `Earnings_ATC_until_2026-04-21.csv` (~4.5 GB, not included — see §Data)

---

## Overview

A rigorous, look-ahead-free backtest of the ProntoNLP Earnings-Call ATC (Aspect-Theme Classifier) signal across three equity universes: **S&P 500**, **S&P 1500**, and **Russell 3000**. The project spans earnings calls from 2010–2026 (~376 K events) and evaluates the signal at daily, weekly, and monthly rebalancing cadences.

---

## Repository Structure

```
├── 00_data_prep.ipynb          # Data pipeline: CSV → Parquet → features → returns
├── 01_analysis.ipynb           # IC, portfolios, walk-forward models, robustness
├── 02_lookahead_tests.ipynb    # 8 programmatic look-ahead tests T1–T8 (all pass)
├── 03_wrds_pull.py             # WRDS pull: CRSP prices + Russell 3000 PIT proxy (optional)
├── 04_wrds_integrate.py        # Merge CRSP into events_with_returns_wrds.parquet
├── 05_wrds_compare.py          # yfinance vs CRSP head-to-head (validation script; results no longer reported in §5 now that CRSP-first is primary)
├── 06_wrds_lookahead_tests.py  # 6 additional tests T9–T14 for the WRDS pipeline
├── 07_audit_gap_tests.py       # T15–T17: programmatic backstops for audit §3.4 / §3.9 / §3.10
├── Makefile                    # One-command reproduce: make all
├── build_charts_pdf.py         # Bundles reports/output/*.png into PDF
├── reports/
│   ├── look_ahead_audit.md     # one-page sign-off (markdown source, required deliverable)
│   ├── look_ahead_audit.pdf    # one-page sign-off (compiled deliverable)
│   ├── look_ahead_audit_detail.md  # full per-item evidence (supplementary)
│   ├── research_report.md      # Full research write-up (source for PDF)
│   ├── research_report.pdf     # Compiled report
│   ├── backtest_charts.pdf     # 20-figure bundle (committed)
│   └── output/                 # 23 PNG figures (committed, regenerable)
├── data/
│   ├── universes.json          # SP500 / SP1500 / RU3K ticker lists (committed)
│   ├── wrds_sp_constituents.parquet     # WRDS S&P current constituents (small, committed)
│   ├── wrds_link.parquet                # CRSP-Compustat link table (small, committed)
│   ├── wrds_names.parquet               # CRSP ticker history (small, committed)
│   ├── wrds_russell3k_proxy.parquet     # PIT top-3000 mcap snapshots (small, committed)
│   # signals.parquet, prices.parquet, events_with_returns.parquet,
│   # signal_slices.parquet, sparse_features.parquet,
│   # wrds_prices.parquet (330 MB), events_with_returns_wrds.parquet (257 MB) are gitignored
├── Student_Handout_Earnings_ATC_Backtest.pdf
└── README.md
```

---

## Reproducing Results

### Quick start (fresh machine, one command)

```bash
# 1. Clone the repo and cd into it
git clone <repo-url> && cd <repo-dir>

# 2. Create environment and install dependencies
conda create -n atc python=3.11 -y
conda activate atc
pip install pandas pyarrow yfinance lightgbm xgboost scikit-learn \
            tqdm requests jupyter nbconvert matplotlib scipy pandoc
# Optional (only needed if you want to re-run the WRDS / CRSP pull from scratch):
pip install wrds psycopg2-binary

# 3. Place the raw CSV in the project root
#    Earnings_ATC_until_2026-04-21.csv (~4.5 GB) — request from instructor

# 4. Run everything
make all    # → reproduces all results from cached parquets, NO data downloads
make fresh  # → full pipeline from scratch, fetches yfinance prices (~90 min)
```

**Default behaviour:** `make all` produces every deliverable (research PDF, charts PDF, look-ahead audit, walk-forward IC, etc.) from the existing `data/events_with_returns.parquet` and cached PNGs. **No yfinance downloads are triggered.** If every PNG in `reports/output/` is already fresh, the build is just the PDF / chart rebuilds (~3 minutes); if any PNG is missing, `make` will fall back to re-running `01_analysis.ipynb` (~70 minutes).

**Full pipeline from scratch:** `make fresh` runs `00_data_prep` first (which fetches yfinance prices), then everything else. Use this when the data parquets are not yet built.

Individual targets:

| Target | What it does |
|--------|-------------|
| `make all` | **Default.** Reproduce all results from cached parquets. No downloads. |
| `make fresh` | Full pipeline including `00_data_prep.ipynb` yfinance fetch (~90 min). |
| `make data` | Run `00_data_prep.ipynb` only (CSV → Parquet, fetches yfinance, ~30–60 min). |
| `make analysis` | Run `01_analysis.ipynb` only (IC, portfolios, walk-forward ML, ~70 min). |
| `make tests` | Run `02_lookahead_tests.ipynb` (T1–T8 look-ahead audit, ~2 min). |
| `make audit_gaps` | Run T15–T17 audit-gap tests (`07_audit_gap_tests.py`, ~30 sec). |
| `make audit` | **Run ALL look-ahead tests (T1–T17) end-to-end without data downloads** (~3 min). Pre-flight checks fail fast if the parquets are missing rather than re-running `00_data_prep`. Includes T9–T14 WRDS tests if `events_with_returns_wrds.parquet` is present, otherwise skips them with a clear message. |
| `make report` | Compile `reports/research_report.pdf` via pandoc. |
| `make charts` | Build `reports/backtest_charts.pdf` from PNG bundle. |
| `make clean` | Remove generated Parquet files and PNGs. |
| `make wrds` | (optional) Run the full WRDS pipeline: `03_wrds_pull.py` → `04_wrds_integrate.py` → `05_wrds_compare.py` → `06_wrds_lookahead_tests.py`. Requires WRDS credentials (~30 min for the price pull). |

### Manual step-by-step

1. **Prerequisites:** Install dependencies above, place raw CSV in project root.
2. **Data prep:** Run `00_data_prep.ipynb` top-to-bottom (Kernel → Restart & Run All). Outputs saved to `data/`:

| File | Size | Description |
|------|------|-------------|
| `signals.parquet` | ~320 MB | Cleaned signal rows (non-delete, Fluff/Filler dropped) |
| `prices.parquet` | ~42 MB | Daily adj-close for all universe tickers |
| `events_with_returns.parquet` | ~500 MB | Total-slice events + 772 features + 5 forward returns |
| `sparse_features.parquet` | ~42 MB | 376,790 rows × 405 raw AspectTheme columns |
| `signal_slices.parquet` | ~35 MB | ATCClassifierScore + EventScores for Total/CEO/CFO/Analysts |
| `universes.json` | <1 MB | SP500/SP1500/RU3K ticker lists |

> **Subsequent runs are incremental.** `signals.parquet` and `universes.json` are skipped if already present.

3. **Analysis:** Run `01_analysis.ipynb` top-to-bottom (~20–30 min). Figures saved to `reports/output/`.
4. **Look-ahead tests:** Run `02_lookahead_tests.ipynb` (~2 min). All 8 tests pass; figures saved to `reports/output/`.
5. **PDF report:** `cd reports && pandoc research_report.md -o research_report.pdf --pdf-engine=xelatex ...` (or `make report`).

---

## Key Design Decisions

### Entry timing (§3.1 — no look-ahead)
- Call hour **≥ 16 UTC** (after-market close): entry at **next** NYSE trading day close
- Call hour **< 16 UTC** (before/during market): entry at **same** NYSE trading day close
- NYSE calendar sourced from SPY daily prices

### INGESTDATEUTC (§3.7 — documented)
Mean ingestion lag is **1,658 days** — confirming this field records a batch historical backfill, not real-time data availability. Entry dates are based on `MOSTIMPORTANTDATEUTC` only. This choice is documented in `00_data_prep.ipynb` cell 18 and in the look-ahead audit.

### Universe membership
- **Russell 3000** is point-in-time: CRSP top-3000 by market cap, annual June reconstitution — survivorship-free (auto-loaded from `events_with_returns_wrds.parquet`; falls back to a current-composition exchange-flag proxy if WRDS data is unavailable). Prices use a **CRSP-first preference with yfinance fallback** for full coverage of delisted small-caps. See §2.4 / §2.5 in the research PDF.
- **S&P 500 / 1500** use **current (2026) composition** from Wikipedia (Compustat tier accessible did not include historical removed members). The S&P survivorship-bias caveat is stated explicitly in research report §7; reported S&P alpha is an upper bound (per handout §6.3).

### Transaction costs
**5 bps one-way** assumed throughout, per handout §2.2.

---

## Deliverables

| Item | Status | Location |
|------|--------|----------|
| Data pipeline | ✅ Complete | `00_data_prep.ipynb` |
| Look-ahead bias audit (10-item checklist §3.1–§3.10, signed) | ✅ Complete | `reports/look_ahead_audit.md` |
| Formal look-ahead bias tests (17 programmatic tests T1–T17) | ✅ Complete | `02_lookahead_tests.ipynb` + `06_wrds_lookahead_tests.py` + `07_audit_gap_tests.py` |
| Analysis notebook | ✅ Complete | `01_analysis.ipynb` |
| Research PDF (with embedded figures) | ✅ Complete | `reports/research_report.pdf` |
| Backtest charts (20 figures) | ✅ Complete | `reports/output/` + `reports/backtest_charts.pdf` |
| One-command reproducibility | ✅ Complete | `Makefile` — run `make all` |
| PIT Russell 3000 (WRDS / CRSP, survivorship-free) — primary RU3K | ✅ Complete | `03_wrds_pull.py` → `04_wrds_integrate.py`; report §2.4 / §2.5 |
| WRDS-pipeline look-ahead audit (T9–T14) | ✅ Complete | `06_wrds_lookahead_tests.py` |
