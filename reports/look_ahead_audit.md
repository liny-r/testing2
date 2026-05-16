---
geometry: margin=0.6in
fontsize: 10pt
---

# Look-Ahead Bias Audit — One-Page Sign-Off

**Project:** Backtesting the ProntoNLP Earnings-Call ATC Signal &nbsp;·&nbsp; **Author:** Yueqi Lin &nbsp;·&nbsp; **Reference:** Student Handout §3

| #    | Item                                   | Status &amp; Evidence (notebook cell / test ID)                                                                                                                                                          |
| ---- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3.1  | Entry timing (AMC vs BMO)              | **PASS** — `hour >= 16 UTC` -> next NYSE day; `hour < 16 UTC` -> same day. Assertion in `00_data_prep.ipynb` cell 19. Gray-zone (13–15 UTC) rule documented in cell 18.                          |
| 3.2  | Forward returns are targets only       | **PASS** — `{return_1d ... return_20d}` disjoint from `feature_cols` (cell 24). T2: 0 overlaps / 772 features.                                                                                  |
| 3.3  | Cross-sectional features are PIT       | **PASS** — All Z-scores / sector ranks deferred to `01_analysis.ipynb` walk-forward; per-fold on training events only.                                                                          |
| 3.4  | Feature selection inside training      | **PASS** — IC top-30 sparse selection re-fit on each fold's training data; no full-sample selection. T15 (`07_audit_gap_tests.py`) asserts selection is data-dependent (Jaccard 0.05 across disjoint windows). |
| 3.5  | Imputation / scaling inside training   | **PASS** — `StandardScaler.fit(train)` then `transform(test)` inside walk-forward loop.                                                                                                         |
| 3.6  | Universe membership is PIT             | **PASS** — RU3K fully PIT via CRSP top-3000 mcap (annual June reconstitution; T11 = 0 violations / 153,988 events). SP500/SP1500 current-composition caveat documented per handout §6.3.        |
| 3.7  | INGESTDATEUTC is not availability date | **PASS** — Inspected: 1,658d mean lag (batch backfill). Entry date uses `MOSTIMPORTANTDATEUTC` only; rationale in cell 18. T6: 0 INGEST features in model input.                                |
| 3.8  | No "future" QoQ deltas                 | **PASS** — All QoQ/2Q/YoY deltas use `groupby(BESTTICKER).shift(1/2/4)` on data sorted by `entry_date` ascending. T8 verified.                                                                   |
| 3.9  | Corporate-action / delisting           | **PASS** — NaN-return events excluded from all analyses (no roll-forward, no imputation). Documented in `00_data_prep.ipynb` §9b and research PDF §7. T16 (`07_audit_gap_tests.py`) asserts no mass `fillna(0)` in `return_20d`. |
| 3.10 | Hyperparameter tuning                  | **PASS** — Tuning sub-period 2010–2017; walk-forward test 2018Q1+ uses frozen hyperparameters. No full-sample grid search. T17 (`07_audit_gap_tests.py`) asserts no `GridSearchCV` / Optuna / hyperopt in `01_analysis.ipynb`. |

**Programmatic verification:** T1–T8 in `02_lookahead_tests.ipynb`, T9–T14 in `06_wrds_lookahead_tests.py`, T15–T17 in `07_audit_gap_tests.py` — **all 17 tests PASS**.

**Detailed implementation notes** for each item are preserved in `reports/look_ahead_audit_detail.md`.

---

I certify that all ten look-ahead audit items above have been reviewed and pass. The backtest implementation in `00_data_prep.ipynb` and `01_analysis.ipynb` contains no look-ahead bias that I am aware of.

**Signed:** Yueqi Lin &nbsp;·&nbsp; **Date:** May 2026 &nbsp;·&nbsp; **Course:** LLM-Driven Quant Research — Final Assignment
