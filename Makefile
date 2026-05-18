## Backtesting the ProntoNLP Earnings-Call ATC Signal
##
## Default target:
##   make all          → reproduce ALL results from existing data parquets
##                       (no downloads; assumes data/events_with_returns.parquet exists)
##
## Full pipeline from scratch (with downloads):
##   make fresh        → data + analysis + tests + audit_gaps + report + charts
##                       (≈ 90 min; fetches yfinance prices via 00_data_prep)
##
## Individual targets:
##   make data         → data prep only (00_data_prep.ipynb; fetches yfinance prices)
##   make analysis     → analysis only (01_analysis.ipynb; ≈ 70 min)
##   make tests        → look-ahead bias tests (02_lookahead_tests.ipynb; T1–T8)
##   make audit_gaps   → audit-gap tests T15–T17 (07_audit_gap_tests.py)
##   make audit        → run ALL look-ahead tests (T1–T17) without data downloads
##   make report       → research_report.pdf from markdown
##   make charts       → backtest_charts.pdf from PNG bundle
##   make wrds         → optional: WRDS / CRSP pull + integration + audit (T9–T14)
##   make clean        → remove generated Parquet / PNG files

PYTHON        = python
JUPYTER_FLAGS = --to notebook --execute --inplace --ExecutePreprocessor.timeout=7200
PDF_ENGINE    = xelatex
PANDOC_FLAGS  = --pdf-engine=$(PDF_ENGINE) -V geometry:margin=1in -V fontsize=11pt \
                -V "mainfont=STIX Two Text" -V "mathfont=STIX Two Math"

.PHONY: all fresh data analysis tests audit_gaps audit report charts wrds clean

## Default: reproduce all results from cached parquets (no data downloads).
## If walkforward_ic.png is missing, this will trigger 01_analysis (~70 min);
## if it's present, only the cheap downstream steps run (~3 min).
all: analysis tests audit_gaps report charts
	@echo ""
	@echo "All deliverables produced. No data downloads were triggered by this build."

## Full pipeline from scratch — re-fetches yfinance prices via 00_data_prep.
fresh: data analysis tests audit_gaps report charts

## ── Audit gap tests T15–T17 (closes inspection-only gaps from §3.4, §3.9, §3.10)
## Order-only prereq on parquet: existence required, freshness not checked.
audit_gaps: 07_audit_gap_tests.py | data/events_with_returns.parquet
	$(PYTHON) 07_audit_gap_tests.py

## ── Run ALL look-ahead audit tests (T1–T17) — verify-only, no data downloads.
## Pre-flight checks that required parquets exist and fails fast if not, so
## this target NEVER triggers 00_data_prep or any other data fetch.
## Total runtime ≈ 3 minutes (2 min for T1–T8 notebook, ~30 sec each for T15–T17
## and the optional T9–T14 WRDS tests).
audit:
	@test -f data/events_with_returns.parquet || { \
	    echo "ERROR: data/events_with_returns.parquet missing."; \
	    echo "       Run 'make data' or 'make fresh' first (these will fetch yfinance prices)."; \
	    exit 1; \
	}
	@test -f data/prices.parquet || { \
	    echo "ERROR: data/prices.parquet missing."; \
	    echo "       Run 'make data' or 'make fresh' first."; \
	    exit 1; \
	}
	@echo "============================================================"
	@echo "T1-T8   Look-Ahead Bias Test Suite (02_lookahead_tests.ipynb)"
	@echo "============================================================"
	jupyter nbconvert $(JUPYTER_FLAGS) 02_lookahead_tests.ipynb
	@echo ""
	@echo "============================================================"
	@echo "T15-T17 Audit Gap Tests          (07_audit_gap_tests.py)"
	@echo "============================================================"
	$(PYTHON) 07_audit_gap_tests.py
	@if [ -f data/events_with_returns_wrds.parquet ]; then \
	    echo ""; \
	    echo "============================================================"; \
	    echo "T9-T14  WRDS / CRSP Pipeline Audit (06_wrds_lookahead_tests.py)"; \
	    echo "============================================================"; \
	    $(PYTHON) 06_wrds_lookahead_tests.py; \
	else \
	    echo ""; \
	    echo "[skip] T9-T14 WRDS tests - events_with_returns_wrds.parquet not found."; \
	    echo "       Run 'make wrds' if you want to verify the WRDS pipeline."; \
	fi
	@echo ""
	@echo "All look-ahead audit tests complete (no data downloads were triggered)."

## ── Data pipeline (yfinance fetch) — only run on demand via `make data` or `make fresh`
data/events_with_returns.parquet: 00_data_prep.ipynb
	jupyter nbconvert $(JUPYTER_FLAGS) 00_data_prep.ipynb

data: data/events_with_returns.parquet

## ── Analysis (IC, portfolios, walk-forward, robustness)
## Order-only prereq on parquet so `make all` does not re-trigger 00_data_prep
## just because the notebook is newer than the parquet.
reports/output/walkforward_ic.png: 01_analysis.ipynb | data/events_with_returns.parquet
	jupyter nbconvert $(JUPYTER_FLAGS) 01_analysis.ipynb

analysis: reports/output/walkforward_ic.png

## ── Formal look-ahead bias tests (T1–T8)
reports/look_ahead_audit.md: 02_lookahead_tests.ipynb | reports/output/walkforward_ic.png
	jupyter nbconvert $(JUPYTER_FLAGS) 02_lookahead_tests.ipynb

tests: reports/look_ahead_audit.md

## ── Research PDF
## Order-only prereq on the analysis output: report doesn't re-run analysis
## just to rebuild the PDF from the markdown.
reports/research_report.pdf: reports/research_report.md | reports/output/walkforward_ic.png
	cd reports && pandoc research_report.md \
		-o research_report.pdf \
		$(PANDOC_FLAGS)

report: reports/research_report.pdf

## ── Backtest charts PDF
reports/backtest_charts.pdf: build_charts_pdf.py | reports/output/walkforward_ic.png
	$(PYTHON) build_charts_pdf.py

charts: reports/backtest_charts.pdf

## ── Optional: WRDS / CRSP pipeline (requires WRDS credentials)
## Pulls survivorship-free CRSP daily prices and the PIT Russell 3000 proxy,
## merges them into events_with_returns_wrds.parquet, then runs the
## yfinance-vs-CRSP comparison and the T9–T14 look-ahead tests.
## The price pull (~14.9 M rows) takes ~10–30 minutes the first time.
data/wrds_prices.parquet: 03_wrds_pull.py
	$(PYTHON) 03_wrds_pull.py

data/events_with_returns_wrds.parquet: 04_wrds_integrate.py \
                                       data/wrds_prices.parquet \
                                       data/events_with_returns.parquet
	$(PYTHON) 04_wrds_integrate.py

wrds: data/events_with_returns_wrds.parquet
	$(PYTHON) 05_wrds_compare.py
	$(PYTHON) 06_wrds_lookahead_tests.py

## ── Clean generated artefacts (keeps raw CSV and Parquet inputs)
clean:
	rm -f data/signals.parquet data/prices.parquet \
	      data/events_with_returns.parquet data/signal_slices.parquet \
	      data/sparse_features.parquet
	rm -f data/wrds_prices.parquet data/events_with_returns_wrds.parquet
	rm -rf data/wrds_prices_chunks
	rm -f reports/output/*.png
	find . -name "*.pyc" -delete
