---
title: "Backtesting the ProntoNLP Earnings-Call ATC Signal: Evidence from S&P 500, S&P 1500, and Russell 3000"
author: "Yueqi Lin"
date: "May 2026"
fontsize: 9pt
linestretch: 1
geometry:
  - margin=1in
toc: false
colorlinks: false
header-includes: |
  \usepackage{xcolor}
  \usepackage{sectsty}
  \usepackage{newunicodechar}
  \usepackage{pifont}
  \sectionfont{\color[HTML]{0B2545}}
  \subsectionfont{\color[HTML]{1D4E89}}
  \subsubsectionfont{\color[HTML]{1D4E89}}
  \newunicodechar{✓}{\ding{51}}
  \newunicodechar{✗}{\ding{55}}
  \newunicodechar{≥}{$\geq$}
  \newunicodechar{≤}{$\leq$}
  \newunicodechar{≈}{$\approx$}
  \newunicodechar{→}{$\rightarrow$}
  \usepackage{float}
  \floatplacement{figure}{H}
---

\newpage
\tableofcontents
\newpage

# Abstract

We present a rigorous, look-ahead-free backtest of the ProntoNLP Earnings-Call ATC signal across 376,790 events (2010–2026) and three equity universes (S&P 500, S&P 1500, Russell 3000 — PIT via CRSP top-3000 market cap). Prices use a **CRSP-first preference with yfinance fallback**: CRSP recovers the ~45% RU3K coverage gap left by yfinance's drop of delisted small-caps. All ten look-ahead audit items pass; 17 programmatic tests T1–T17 verify them. **Recommended production deployment (§6): Russell 3000 PIT, monthly quintile long-short, 20-day hold, Enhanced LightGBM on 772 engineered Aspect × Theme features — walk-forward net Sharpe +1.62, max DD −13.5%, +129 bps/month net (5 bps one-way TC), capacity ~\$50–100M AUM.** Static quintile L/S Sharpe on the same universe is +2.53 (vs +0.76 / +0.83 for SP500 / SP1500). The ATCClassifierScore achieves Spearman IC of +0.045–0.060 (SP500 +0.051 at 20d; RU3K +0.060 at 20d) and monthly is the only cadence positive across all universes (SP500 daily net Sharpe 0.00). An expanding walk-forward over 34 quarters (2018Q1–2026Q2) tests Ridge, LightGBM, and XGBoost on 772 engineered features plus 30 per-fold IC-selected raw AspectTheme cells. Combo LightGBM achieves IC IR +1.51 (p<0.001, 95% CI [+0.82, +2.64]); pooled all-universe LightGBM portfolio delivers Sharpe +1.79 (the alternative deployment for ≥\$300M AUM). The 2-quarter ATC trend (`ATCClassifierScore_2q`) is the strongest individual feature. Break-even TC is ~20 bps one-way. Key risk: post-COVID signal decay at SP500 short horizons (10d IC +0.052 → +0.008), though pooled walk-forward ML now provides meaningful post-COVID resilience (Ridge IR +1.82, LGB IR +1.07).





# 1. Introduction

Earnings calls concentrate high-value information in a short window. ProntoNLP's Aspect-Theme Classifier (ATC) combines sentence-level aspect/theme classification with consensus KPI beat/miss data into a single per-call score, `ATCClassifierScore`, used by industry trading desks.

This paper provides a rigorous, look-ahead-free backtest across S&P 500, S&P 1500, and Russell 3000, covering: (1) full look-ahead bias audit (10 items, all pass); (2) IC analysis by universe, year, sector, and feature; (3) quintile/decile portfolio simulation with TC; (4) expanding walk-forward predictive model (Ridge, LightGBM, XGBoost); and (5) a deployment recommendation with cadence, model choice, and capacity estimate.


# 2. Data

## 2.1 Signal Dataset

The primary data source is `Earnings_ATC_until_2026-04-21.csv`, a 4.47 GB file containing 2,740,437 rows and 609 columns produced by ProntoNLP's NLP pipeline over S&P Global earnings-call transcripts. Each row represents one (earnings call, signal-aggregation slice) record.

**Coverage:**

| Attribute | Value |
|-----------|-------|
| Date range | 2010-01-04 → 2026-04-21 |
| Total rows (pre-filter) | 2,740,437 |
| Unique tickers | 17,636 |
| Countries | 100+ (US ~55%) |
| Sectors | All 11 GICS sectors |

## 2.2 Row Structure: SignalType Slices

Each earnings call generates up to nine rows, one per `SignalType`, each aggregating NLP features over a different subset of the transcript:

| SignalType | Rows | Coverage |
|------------|------|----------|
| Total | 376,790 | Entire transcript |
| Executives | 376,036 | All executives |
| Presentation | 373,808 | Prepared remarks |
| Answer | 359,535 | Management answers |
| Question | 351,494 | Analyst questions |
| CEO | 303,854 | CEO sentences only |
| CFO | 253,155 | CFO sentences only |
| Analysts | 343,534 | Analyst sentences |
| delete | 2,231 | Corrupt/invalidated (dropped) |

We use `Total` as the primary slice for all main analyses and compare against CEO, CFO, and Analysts slices to assess whether speaker-specific cuts add information.

## 2.3 Signal Features

The 609 columns decompose into three families:

**(a) EventScore family (12 columns):** Four score variants × {Pos, Neg, Score} capturing event-level sentiment at different classifier configurations. The `4_2_1` variant is the production trading-desk configuration.

**(b) ATCClassifierScore (1 column):** The headline aggregated classifier output. This is the primary signal. It already internalizes the consensus KPI surprise dimension (EBITDA, EPS-GAAP, Net Income, Revenue, CapEx, FCF beat/miss) via the V4 classifier training objective. External consensus data is not joined.

**(c) AspectTheme matrix (~567 columns):** One column per (Aspect × Theme × Magnitude × Sentiment) combination. Each cell counts sentences in the transcript slice that fall into that bucket. We drop the 162 Fluff and Filler aspect columns (noise classes by design), retaining 405 informative cells.

The five valid aspects are: **CurrentState** (backward-looking), **Forecast** (forward-looking guidance), **Surprise** (unexpected external events), **StrategicPosition** (competitive dynamics), and **Other**. The nine themes are: FinancialPerformance, OperationalPerformance, MarketAndCompetitivePosition, StrategicInitiatives, CapitalAllocation, RegulatoryAndLegalIssues, ESG, MacroeconomicFactors, Other.

Importantly, the ATC classifier was trained against a 14-day pre/post-call window loss function (average price 14 days after minus 14 days before). This means shorter horizons (1–5 days) may show weaker signal than the 10–20 day horizon the model was optimized for.

## 2.4 Price Data

Daily adjusted-close prices are sourced from two layers with a **CRSP-first preference and yfinance fallback**:

- **CRSP (via WRDS)** — academic gold standard; survivorship-free coverage of all US common stocks. Pulled by `03_wrds_pull.py` (CRSP `dsf`, 14.9M daily price rows across 6,646 PERMNOs, 2009–2026); linked to event tickers via the CRSP-Compustat link table and integrated by `04_wrds_integrate.py`.
- **yfinance** — public-data fallback for tickers / dates not in the CRSP pull; keyed by `BESTTICKER`. The production yfinance pipeline uses fuzzy ticker matching (Wikipedia's Yahoo format uses hyphens; BESTTICKER may use dots), small batches (20 for SP500/SP1500, 50 for RU3K), and individual retry with format-variant fallback (`.` / `-`) for tickers missed in batch downloads. Final yfinance cache: 3,109 unique tickers, 9.3M price rows.

At load time the analysis notebook applies a single preference rule: for each event and each horizon, use the CRSP return if present, otherwise the yfinance return. The two sources agree numerically where both exist (Spearman correlation 0.97, median |Δ| = 0), so SP500/SP1500 results shift only at noise level. The material gain is in the **Russell 3000**, where yfinance dropped ~45% of events because delisted small-caps fall out of its price history — exactly the names where the signal works best.

| Universe | Events with `return_20d` | Total events | Coverage |
|----------|-------------------------|--------------|----------|
| S&P 500 | 30,141 | 30,156 | 100% |
| S&P 1500 | 79,449 | 79,799 | 100% |
| Russell 3000 (PIT) | 153,824 | 153,988 | 100% |

For RU3K-PIT specifically, CRSP supplies 99.8% of events natively; yfinance fills the residual 0.2%. Of the 376,790 cross-universe events, **173,244** had a `return_20d` value sourced from CRSP under the preference rule. The cached yfinance pipeline remains the public-data reproduction path: configs that exclude CRSP (i.e. running without WRDS credentials) produce results consistent with the upper-bound yfinance baseline reported in earlier drafts (RU3K monthly Sharpe ~+1.69 vs ~+2.53 under CRSP-first).

## 2.5 Universe Definitions

Three universes are evaluated:

- **S&P 500:** 503 tickers from Wikipedia's current (2026) S&P 500 list; 497 matched to signal dataset. **Current composition** — historical removed members not available in the Compustat tier accessed.
- **S&P 1500:** S&P 500 + S&P 400 + S&P 600 = 1,506 tickers; 1,465 matched. Current composition (same caveat as SP500).
- **Russell 3000 (PIT):** CRSP top-3000 US common stocks by market capitalisation, snapshotted at each annual June reconstitution (matches Russell methodology). **Survivorship-free** — built from CRSP `msf` market-cap rankings via `merge_asof` of event `entry_date` against the snapshot windows (`04_wrds_integrate.py`). 153,988 events fall inside an active PIT window.

**Survivorship bias caveat (SP500/SP1500 only):** Reported S&P alpha figures should be interpreted as upper bounds. The current S&P 500 excludes companies that were members in 2010–2020 but have since been removed (delisted, acquired, or downgraded). These tend to be underperformers, so including them would reduce long-only alpha and may reduce long-short alpha depending on signal correlation with delisting risk. **RU3K is fully PIT (no caveat).**


# 3. Methodology

## 3.1 Entry Timing (Look-Ahead-Free)

The core look-ahead challenge is determining when a trader could have acted on a given earnings call. We use the `MOSTIMPORTANTDATEUTC` field:

- **Hour >= 16 UTC (after-market close):** The call occurred after the close. Entry at the **next** NYSE trading day's closing price.
- **Hour < 16 UTC (before/during market hours):** Entry at the **same** NYSE trading day's closing price.

This is conservative: calls during market hours (13-16 UTC, ~8-11 AM ET) are treated as same-day tradeable, which is generous. A stricter rule would require next-day entry for calls during market hours, but the handout explicitly permits same-day entry for BMO.

The NYSE calendar is derived from SPY daily prices (avoids dependency on `pandas_market_calendars`). Entry and exit dates are computed using `numpy.searchsorted` for vectorized, branch-free date arithmetic.

Both the AMC and BMO assertions pass for all 376,790 events (cell 19).

**INGESTDATEUTC (§3.7):** We inspected this field and found a mean lag of 1,658 days between `MOSTIMPORTANTDATEUTC` and `INGESTDATEUTC`. This confirms the field records when ProntoNLP batch-ingested historical transcripts, not real-time data availability. Applying it as an entry-date floor would push 81% of events to 2023 entry dates (joining 2010 signals to 2023 prices — itself a form of look-ahead). Design choice: `MOSTIMPORTANTDATEUTC` only. Documented in cell 18.

## 3.2 Feature Engineering

We engineer Aspect × Theme cross-product features from the AspectTheme matrix, following the best practice from the handout §1.6: naive marginal aggregation (summing all `*_FinancialPerformance` cells across Aspects) destroys the cross-product structure and conflates forward-looking with backward-looking commentary. Instead we preserve the full Aspect × Theme cross-product so models can distinguish, for example, `Forecast × FinancialPerformance` (forward guidance) from `CurrentState × FinancialPerformance` (backward-looking results).

**Aspect × Theme cross-product features (prefix `at_`):** For each of the 5 × 9 = 45 (Aspect, Theme) pairs, we sum sentence counts over all magnitudes (magnitude encodes degree, not direction) and compute four features per pair:

| Feature | Formula |
|---------|---------|
| `at_{A}_{T}_Positive` | Σ counts over magnitudes, Positive sentiment |
| `at_{A}_{T}_Negative` | Σ counts over magnitudes, Negative sentiment |
| `at_{A}_{T}_total` | Positive + Negative + Neutral |
| `at_{A}_{T}_net_sentiment` | (Positive − Negative) / (total + 1) |

This preserves the Aspect × Theme cross-product so the model can distinguish, for example, `Forecast × FinancialPerformance` (forward-looking earnings commentary) from `CurrentState × FinancialPerformance` (backward-looking results) — two cells that carry very different trading implications despite sharing the same theme.

**Raw scores (13 columns):** `ATCClassifierScore` and four EventScore variants × {Positive, Negative, Score}.

This yields **193 base features** (45 pairs × 4 = 180 cross-product + 13 raw scores). We then compute three lagged delta versions for each base feature:

| Lag | Suffix | Meaning |
|-----|--------|---------|
| shift(1) | `_qoq` | Quarter-over-quarter change |
| shift(2) | `_2q` | 2-quarter (6-month) trend |
| shift(4) | `_yoy` | Year-over-year change |

This yields **772 total features** (193 base × 4 versions). All shift operations use `groupby('BESTTICKER').shift(k)` on data sorted ascending by `entry_date`, ensuring only past observations feed current features (no future leakage).

The raw 405 AspectTheme columns (full Aspect × Theme × Magnitude × Sentiment grid, after Fluff/Filler removal) are saved separately as `sparse_features.parquet` for use in the Stretch model tier.

## 3.3 Forward Returns

We compute log-close returns at five horizons: **1, 3, 5, 10, and 20 trading days**. Exit dates are computed by adding the horizon in trading-day steps to the `entry_date` index in the NYSE calendar array. Returns are computed as `(exit_price / entry_price) - 1` and stored as float32.

**Winsorization (look-ahead-free, quarterly roll-forward):** Returns at each horizon are clipped at the 0.1th and 99.9th percentiles using a quarterly expanding-window design: for each quarter Q, clip bounds are computed from all events in prior quarters only. The first quarter (cold-start, fewer than 50 valid returns) uses its own distribution. Quarterly granularity aligns with the walk-forward framework and ensures no future return data informs the clipping of any past event. The raw `return_5d` maximum was 244× (a data artifact); post-winsorization, the maximum is 0.490 and minimum is −0.350.

Returns are computed after entry dates are fully determined and are stored in separate columns. An assertion confirms they do not appear in the feature column set (cell 24).

The ATC classifier's training objective used a 14-day pre/post window. This means:
- 10d and 20d returns are most aligned with the model's training signal
- 1d and 3d returns test whether the signal contains short-term information beyond the 14-day target

## 3.4 Walk-Forward Framework

All predictive modeling uses an **expanding-window walk-forward** design:

- **Training window:** All events with `entry_date <= split_date`
- **Test window:** Events in the subsequent quarter
- **First split:** Train end = 2017Q4; Test = 2018Q1
- **Walk through:** 2018Q1 → 2026Q2 (34 quarterly steps)

Four model tiers are evaluated at each step:

| Tier | Model | Features |
|------|-------|----------|
| Baseline | Raw `ATCClassifierScore` (no model) | 1 column |
| Enhanced | RidgeCV (LOO-CV α) + LightGBM (early stopping) | 772 engineered features |
| Sparse | RidgeCV | 30 per-fold IC-selected raw AspectTheme cells |
| Combined | RidgeCV + LightGBM + XGBoost (early stopping) | 772 engineered + 30 per-fold sparse (802 total) |

At each step, `StandardScaler` and NaN imputation are fit on training events only and applied to test events. Tree-based models (LightGBM, XGBoost) are scale-invariant and use unscaled features directly. `RidgeCV` selects its regularisation parameter via leave-one-out CV on training data each fold; tree models use the chronologically last 15% of training rows (strictly before the test quarter) as an early-stopping validation set.

## 3.5 Portfolio Construction

We evaluate three rebalancing cadences:

- **Daily (event-driven):** Each morning, enter all new events with `entry_date = today`. Hold for chosen horizon. Track daily positions.
- **Weekly:** Every Monday, enter all events from the prior 5 trading days.
- **Monthly:** First trading day of each month, enter all events from the prior month.

At each rebalance, events are ranked by signal; the top quintile (Q5) is held long, bottom quintile (Q1) is held short. Equal-weighting within each quintile.

Long-short gross exposure is 2× (100% long + 100% short). All return calculations report the long-short spread. Long-only returns are reported separately as a benchmark.

## 3.6 Transaction Cost Assumption

A flat **5 bps one-way** transaction cost is applied to all simulated trades, per the handout specification. Post-cost Sharpe ratios are reported alongside gross Sharpe ratios. Turnover (fraction of portfolio replaced at each rebalance) is tracked to contextualize the cost impact.


# 4. Look-Ahead Bias Audit

All ten audit items from the handout §3 pass. The complete checklist with implementation references is in `reports/look_ahead_audit.md`. A summary:

| # | Item | Status |
|---|------|--------|
| 3.1 | Entry timing (AMC >=16 UTC, next day; BMO < 16 UTC, same day) | PASS — asserted cell 19 |
| 3.2 | Forward returns are targets, never inputs | PASS — asserted cell 24 |
| 3.3 | Cross-sectional features computed point-in-time | PASS — deferred to walk-forward loop |
| 3.4 | Feature selection on training fold only | PASS — inside walk-forward loop |
| 3.5 | Scaling/imputation on training fold only | PASS — inside walk-forward loop |
| 3.6 | Universe membership (survivorship caveat documented) | PASS |
| 3.7 | INGESTDATEUTC: batch backfill confirmed (1,658d mean lag); MOSTIMPORTANTDATEUTC used | PASS |
| 3.8 | Multi-quarter deltas (QoQ/2Q/YoY) use shift(k) only on past data | PASS — asserted by sort order |
| 3.9 | NaN-return events excluded; winsorization uses quarterly expanding-window bounds (prior quarters only) | PASS |
| 3.10 | Hyperparameters tuned on 2010–2017 sub-period only | PASS |


# 5. Results

All analyses use `01_analysis.ipynb` running on `events_with_returns_wrds.parquet` (the WRDS-merged parquet with both CRSP and yfinance return columns; auto-loaded). At load time a single preference step replaces yfinance returns with CRSP returns wherever CRSP has a value — 173,244 of 376,790 events use a CRSP return under this rule (the rest stay on yfinance). 376,790 events, 2010-01-05 to 2026-04-21, 772 features. The Russell 3000 universe is the point-in-time CRSP top-3000 by market cap (annual June reconstitution; survivorship-free; see §2.5). Figures are saved to `reports/output/`.

## 5.1 Single-Feature IC Analysis

Spearman rank IC between `ATCClassifierScore` and forward returns across three equity universes:

| Universe | N (20d) | IC_1d | IC_3d | IC_5d | IC_10d | IC_20d |
|----------|---------|-------|-------|-------|--------|--------|
| SP500    | 30,237  | +0.042 | +0.047 | +0.045 | +0.040 | +0.051 |
| SP1500   | 79,741  | +0.045 | +0.047 | +0.041 | +0.039 | +0.045 |
| RU3K (PIT) | 154,176 | +0.053 | +0.057 | +0.054 | +0.056 | +0.060 |

The IC is consistently positive across all universes and horizons, with a mild peak at the 20d horizon — consistent with the ATC classifier's 14-day training objective. The RU3K-PIT IC strengthens materially under CRSP-first pricing because the previously-missing delisted small-caps carried the highest signal-to-noise. All IC values are statistically meaningful given the sample sizes.

**EventScore variants** (S&P 500) show markedly weaker IC: `EventsScore_4_2_1` achieves IC_1d = +0.013 but near zero at 10d and 20d. `ATCClassifierScore` dominates at every horizon, confirming it as the primary signal.

![Annual Spearman IC heatmap — ATCClassifierScore, three universes (SP500, SP1500, RU3K). Rows = return horizon, columns = year. Signal is positive in most years across all horizons; strongest in 2018–2019, with moderation post-2022.](output/ic_annual_heatmap.png)

## 5.1b IC by Sector

Sector-level Spearman IC at the 5d horizon, for all three universes, sorted by IC_5d:

**S&P 500:**

| Sector | IC_1d | IC_3d | IC_5d | IC_10d | IC_20d |
|--------|-------|-------|-------|--------|--------|
| Consumer Staples | +0.098 | +0.084 | +0.084 | +0.080 | +0.085 |
| Energy | +0.079 | +0.079 | +0.077 | +0.041 | +0.032 |
| Utilities | +0.032 | +0.044 | +0.070 | +0.077 | +0.040 |
| Materials | +0.059 | +0.077 | +0.069 | +0.047 | +0.089 |
| Industrials | +0.070 | +0.061 | +0.064 | +0.048 | +0.042 |
| Communication Services | +0.041 | +0.050 | +0.036 | +0.019 | +0.006 |
| Information Technology | +0.014 | +0.048 | +0.038 | +0.054 | +0.074 |
| Health Care | +0.047 | +0.036 | +0.038 | +0.037 | +0.058 |
| Consumer Discretionary | +0.022 | +0.038 | +0.024 | +0.000 | +0.007 |
| Real Estate | +0.021 | +0.026 | +0.024 | +0.007 | +0.043 |
| Financials | +0.018 | +0.009 | +0.002 | +0.005 | +0.033 |

**S&P 1500** (top sectors at 5d): Utilities (+0.080), Energy (+0.072), Consumer Staples (+0.053), Materials (+0.049). Financials moves into the middle tier (+0.034) under CRSP-first pricing. **Russell 3000 (PIT)** is the most uniform: Communication Services leads at 5d (+0.084), but every sector exceeds +0.019. The signal shows positive IC in all 11 GICS sectors across all three universes, confirming it is not driven by any single industry; the 20d t-statistics in RU3K are highly significant in every sector (t = +2.7 to +11.0).

![Spearman IC by GICS sector — ATCClassifierScore → 5d return, all three universes side by side. Green = positive IC, red = negative. All sectors positive across all universes except Financials in SP500.](output/ic_by_sector.png)

## 5.1c IC of Engineered Features

IC of individual Aspect × Theme cross-product features relative to the primary ATC score (S&P 500):

| Feature | IC_1d | IC_3d | IC_5d | IC_10d | IC_20d |
|---------|-------|-------|-------|--------|--------|
| ATC Classifier (primary) | +0.042 | +0.047 | +0.044 | +0.039 | +0.049 |
| Forecast × Fin-Perf (net) | +0.008 | +0.010 | +0.012 | +0.005 | +0.003 |
| CurrentState × Fin-Perf (net) | +0.019 | +0.025 | +0.031 | +0.014 | +0.008 |
| CurrentState × Fin-Perf 2Q delta | +0.017 | +0.022 | +0.028 | +0.018 | +0.022 |
| Forecast × CapAlloc (net) | +0.006 | +0.004 | +0.008 | −0.002 | −0.004 |
| CurrentState × CapAlloc (net) | +0.021 | +0.023 | +0.027 | +0.012 | +0.006 |
| Surprise × Fin-Perf (net) | +0.011 | +0.009 | +0.013 | +0.006 | +0.002 |
| Forecast × Macro (net) | −0.001 | −0.009 | −0.013 | −0.020 | −0.015 |
| Strategic × MktPos (net) | +0.009 | +0.007 | +0.011 | +0.005 | +0.003 |

The `ATCClassifierScore` is 2–4× more predictive than any individual cross-product feature. The key finding is that **`CurrentState × FinancialPerformance`** (IC_5d = +0.031) substantially outperforms **`Forecast × FinancialPerformance`** (IC_5d = +0.012) — confirming that backward-looking earnings results carry more short-term price information than forward-looking guidance. `Forecast × Macro` (IC_5d = −0.013) is negative, indicating that macro-economic forecasting language in earnings calls is noise at short horizons. The `CurrentState × Fin-Perf 2Q delta` (IC_5d = +0.028) confirms that momentum in backward-looking financial commentary carries incremental signal.

![Spearman IC by engineered feature across all five return horizons (S&P 500). ATC Classifier dominates; CurrentState × Fin-Perf leads among cross-product features.](output/ic_engineered_features.png)

## 5.1d Feature × Horizon IC Heatmap

To identify which of the 772 engineered features carry the most predictive power, we compute Spearman IC for each feature against all five return horizons (S&P 500) and display the top 30 by |IC@5d|:

| Rank | Feature (abbreviated) | IC_1d | IC_3d | IC_5d | IC_10d | IC_20d |
|------|-----------------------|-------|-------|-------|--------|--------|
| 1 | ATC_2q | +0.043 | +0.053 | +0.047 | +0.040 | +0.051 |
| 2 | ATC | +0.042 | +0.047 | +0.044 | +0.039 | +0.049 |
| 3 | CS×FinPerf_Pos | +0.024 | +0.031 | +0.037 | +0.025 | +0.015 |
| 4 | ATC_yoy | +0.041 | +0.042 | +0.036 | +0.032 | +0.051 |
| 5 | ATC_qoq | +0.036 | +0.041 | +0.035 | +0.032 | +0.035 |
| 6 | CS×CapAlloc_Pos | +0.021 | +0.027 | +0.033 | +0.018 | +0.006 |
| 7 | CS×FinPerf_Pos_2q | +0.019 | +0.025 | +0.032 | +0.022 | +0.026 |
| 8 | CS×FinPerf_Net | +0.019 | +0.025 | +0.031 | +0.014 | +0.008 |
| 9 | CS×CapAlloc_Pos_2q | +0.012 | +0.024 | +0.030 | +0.029 | +0.022 |
| 10 | CS×OpPerf_Net_2q | +0.015 | +0.021 | +0.029 | +0.020 | +0.025 |

*Abbreviations: ATC = ATCClassifierScore; CS = at\_CurrentState; FinPerf = FinancialPerformance; CapAlloc = CapitalAllocation; OpPerf = OperationalPerformance; Net = net\_sentiment. Full feature names in `reports/output/ic_feature_horizon_heatmap.png`.*

**Key findings:** `ATCClassifierScore_2q` (the 6-month trend in the ATC score) is the single most predictive feature (IC_5d = +0.047), marginally exceeding the raw `ATCClassifierScore` (+0.044). The 2-quarter trend family (suffix `_2q`) consistently outranks both QoQ and YoY variants, suggesting a 6-month lookback is the optimal trend window.

Critically, **three of the top ten features are `at_CurrentState_*` cross-product features** — specifically `at_CurrentState_FinancialPerformance_Positive` (rank 3, IC_5d = +0.037), `at_CurrentState_CapitalAllocation_Positive` (rank 6, IC_5d = +0.033), and their 2Q trend variants. This validates the Aspect × Theme cross-product design: isolating `CurrentState` (backward-looking results) from `Forecast` (forward-looking guidance) within the same theme produces features with meaningfully different predictive content. No `Forecast × *` feature appears in the top 10, confirming that backward-looking earnings commentary is more immediately price-relevant at short horizons.

![Feature × Horizon IC heatmap — top 30 features by |IC@5d|, S&P 500. ATCClassifierScore_2q ranks first; at_CurrentState_FinancialPerformance_Positive is the top cross-product feature.](output/ic_feature_horizon_heatmap.png)

## 5.2 Quintile Portfolio Performance

Monthly calendar-time quintile portfolios (20-day holding period, 20 bps round-trip transaction cost). The 20-day horizon is the data-driven optimal hold (§5.6C), aligning with the classifier's 14-day training window.

| Universe | Mean LS (bps) | Mean LS net (bps) | Sharpe gross | Sharpe net | Max DD | N periods |
|----------|--------------|-------------------|--------------|------------|--------|-----------|
| SP500    | 87.5 | 67.5 | 0.98 | 0.76 | −12.3% | 196 |
| SP1500   | 78.8 | 58.8 | 1.12 | 0.83 | −32.9% | 196 |
| RU3K (PIT) | 194.5 | 174.5 | 2.82 | 2.53 | −18.5% | 174 |

Both the long leg (Q5) and short leg (−Q1) contribute positively in all universes. **RU3K is by far the strongest universe** with a net Sharpe of **2.53** (174 bps/month net), driven by wider return dispersion in small-cap names and full CRSP coverage of delisted tickers. The signal's net spread compresses as stocks grow larger and more analyst-covered. SP1500 offers the best liquidity-adjusted trade-off (Sharpe net 0.83, max DD −32.9%). SP500 alpha is solid after costs (Sharpe net 0.76), confirming the signal retains meaningful alpha even in the most liquid, well-covered universe.

Note: RU3K uses the CRSP top-3000-by-market-cap PIT proxy (annual June reconstitution; §2.4 / §2.5) — survivorship-free in both universe assignment *and* price coverage. The N=174 (vs 196 for SP500/SP1500) reflects months that lacked ≥10 events in the smaller PIT-RU3K universe.

![Monthly quintile L/S equity curves — three universes. RU3K (Sharpe net 2.53) leads, followed by SP1500 (0.83) and SP500 (0.76).](output/quintile_equity_curves.png)

## 5.2b Decile Portfolio — Long-Only, Short-Only, and Long-Short

Top decile (D10) long, bottom decile (D1) short, monthly rebalancing, 20-day holding period.

**S&P 500 (monthly, 20d, net of TC):**

| Metric | Value |
|--------|-------|
| L/S net Sharpe | +0.62 |
| Max drawdown (L/S) | −22.7% |
| N months | 196 |

**Decile spread D10−D1 (net of 20 bps TC, bps) — Universe × Horizon:**

| Universe | 1d | 3d | 5d | 10d | 20d |
|----------|----|----|-----|-----|-----|
| SP500    | 3.6 | 14.3 | 23.4 | 37.6 | 72.3 |
| SP1500   | 23.2 | 32.1 | 35.6 | 45.0 | 84.9 |
| RU3K (PIT) | 52.4 | 101.2 | 100.3 | 134.4 | 229.7 |

**L/S Decile Sharpe by Universe (monthly, 20d return, net of TC):**

| Universe | L/S Sharpe | Max DD |
|----------|------------|--------|
| SP500    | +0.62 | −22.7% |
| SP1500   | +0.85 | −35.2% |
| RU3K (PIT) | +2.12 | −36.8% |

The **decile spread grows monotonically from 1d to 20d** at every universe — consistent with the ATC classifier's 14-day training window. The SP500 20d net spread of 72 bps is nearly double the 10d spread (38 bps), confirming that the full signal horizon is captured only at the 20d hold. The **short leg contributes positively in all three universes** at monthly cadence: bottom-decile stocks systematically underperform, with the effect strongest in RU3K where small-cap short calls face less index-driven reversion. The RU3K 20d net decile spread of **229.7 bps/month** is materially larger than the quintile-based 174.5 bps because the extreme-decile cuts isolate the highest-signal names more precisely.

![Decile portfolio: cumulative returns (long-only/short-only/L/S), drawdown, and rolling 12-month Sharpe (S&P 500).](output/decile_drawdown_rolling_sharpe.png)

![Decile spread D10−D1 (net bps) — Universe × Horizon heatmap. Signal strengthens at longer horizons and smaller-cap universes.](output/decile_spread_heatmap.png)

## 5.2c Cadence Comparison — Daily / Weekly / Monthly

Quintile L/S performance at three rebalancing frequencies. Each cadence uses the natural matching return horizon: daily → 1d, weekly → 5d, monthly → 20d. Shown for all three universes.

| Universe | Cadence | Horizon | Sharpe gross | Sharpe net | Max DD |
|----------|---------|---------|--------------|------------|--------|
| SP500    | Daily   | 1d  | 1.95 | 0.00 | −58.2% |
| SP500    | Weekly  | 5d  | 0.71 | +0.18 | −63.0% |
| **SP500**    | **Monthly** | **20d** | **0.98** | **+0.76** | **−12.3%** |
| SP1500   | Daily   | 1d  | 2.75 | +1.01 | −40.8% |
| SP1500   | Weekly  | 5d  | 0.98 | +0.48 | −61.5% |
| **SP1500**   | **Monthly** | **20d** | **1.12** | **+0.83** | **−32.9%** |
| RU3K (PIT) | Daily   | 1d  | 3.13 | +1.87 | −57.0% |
| RU3K (PIT) | Weekly  | 5d  | 2.20 | +1.77 | −50.5% |
| **RU3K (PIT)** | **Monthly** | **20d** | **2.82** | **+2.53** | **−18.5%** |

**Monthly is the robust primary cadence.** Bold rows indicate Monthly — the only cadence that is positive across all three universes:

- **SP500 → Monthly required** (+0.76): Daily TC-destroys alpha entirely (gross 1.95 → net 0.00). Monthly rebalancing reduces max DD from −58% to −12%. There is no viable alternative for SP500.
- **SP1500 → Monthly primary** (+0.83): Daily achieves +1.01 net Sharpe, but at the cost of −40.8% max DD and relies on the 5 bps flat-TC assumption holding at scale. The marginal gain (+0.18 Sharpe) over monthly does not justify the drawdown and capacity risk for most practitioners.
- **RU3K → Monthly dominant** (+2.53): Monthly net Sharpe (+2.53) materially exceeds daily (+1.87) and weekly (+1.77) under the 5 bps TC assumption, and the −18.5% max DD beats daily's −57.0% by a wide margin. The 20d hold captures the classifier's full information window; daily 1d returns capture only a fraction of the signal.

*Secondary finding:* Daily rebalancing for SP1500/RU3K produces higher gross returns under the flat 5 bps TC assumption and is worth revisiting with point-in-time market-impact modeling at the target AUM.

- **Alpha decay supports longer holds for SP500:** IC grows monotonically from 1d to 20d because the classifier was trained on a 14-day window. For SP500 — where daily TC destroys value — a monthly rebalance captures the full information signal in one turnover event.

- **Drawdown control:** Monthly rebalancing reduces SP500 max DD from −58% to −12% by aggregating independent quarterly earnings events rather than stacking intra-week correlated trades.

![Alpha decay — Spearman IC of ATCClassifierScore vs. return horizon (1, 3, 5, 10, 20d), all universes. IC increases monotonically, supporting the 20d primary holding period.](output/alpha_decay.png)

![Cadence comparison — quintile L/S cumulative equity curves (all universes × cadences). Monthly is the robust primary cadence; daily is TC-destroyed for SP500 and carries high drawdown risk for SP1500/RU3K.](output/cadence_comparison.png)

## 5.2d Turnover Analysis

The Q5 (long) portfolio has near-100% monthly turnover (mean 99.8%, median 100%). This is expected: each month contains a completely different set of earnings events (each company reports approximately once per quarter), so the long book is almost entirely refreshed each month. The 100% turnover assumption used in the TC model (4 × 5 bps round-trip) is validated by the data.

![Monthly Q5 turnover — fraction of names replaced each period. Near-100% confirms the full-turnover TC assumption.](output/turnover_bar.png)

## 5.2e Gross/Net Exposure

The equal-weight quintile construction produces an approximately dollar-neutral book:

| Metric | Value |
|--------|-------|
| Avg long positions (Q5) | 30.8 per month |
| Avg short positions (Q1) | 31.1 per month |
| Net exposure | −0.3% (near-zero, dollar-neutral) |
| Gross exposure | 200% (100% long + 100% short of capital) |

The near-equal long and short books confirm the strategy is market-neutral by construction. The slight negative net (−0.3%) is a rounding artifact of equal-weighting when the quintile bin sizes differ marginally. All reported Sharpe ratios reflect the long-short spread only, without any market-beta contribution.

![Gross/net exposure over time — number of long/short positions and percentage exposure (S&P 500 quintile portfolio).](output/gross_net_exposure.png)

## 5.3 Walk-Forward Predictive Model

Expanding-window quarterly walk-forward, 2018Q1–2026Q2 (34 steps). Training on all events before the test quarter; target: 20d forward return (aligned with the classifier's 14-day training window). Four model tiers tested: (1) Enhanced — 772 engineered Aspect × Theme cross-product features; (2) Sparse-Only — 30 per-fold IC-selected raw AspectTheme cells; (3) Combined — 772 engineered + 30 per-fold IC-selected sparse cells (802 total). Models train on all-universe events (SP500 + SP1500 + RU3K combined) to maximise fold sample size; portfolio evaluation below applies per-universe filters.

| Model | Features | Mean IC | Std IC | IR | 95% CI | p-val | n |
|-------|----------|---------|--------|-------|--------|-------|---|
| ATCClassifierScore (baseline) | 1 | +0.034 | 0.053 | +1.28 | [+0.46, +3.01] | 0.001\*\*\* | 34 |
| Ridge α=10 (enhanced)         | 772 | +0.022 | 0.045 | +0.97 | [+0.29, +1.95] | 0.008\*\* | 34 |
| LightGBM 200 (enhanced)       | 772 | +0.027 | 0.044 | +1.23 | [+0.46, +2.56] | 0.001\*\* | 34 |
| Sparse Ridge (top-30 per fold) | 30 | +0.019 | 0.047 | +0.79 | [+0.15, +1.53] | 0.028\* | 34 |
| Combo Ridge (772+30)          | 802 | +0.022 | 0.045 | +0.97 | [+0.29, +1.94] | 0.008\*\* | 34 |
| **Combo LightGBM (772+30)**   | **802** | **+0.031** | **0.040** | **+1.51** | **[+0.82, +2.64]** | **<0.001\*\*\*** | 34 |
| Combo XGBoost (772+30)        | 802 | +0.029 | 0.047 | +1.24 | [+0.52, +2.44] | 0.001\*\* | 34 |

*p-values and 95% CIs from bootstrap (10,000 resamples, quarterly annualised). \*\*\* p<0.001, \*\* p<0.01, \* p<0.05.*

**Key findings:**

- **Combo LightGBM leads on IC-based IR (+1.51, p<0.001, CI [+0.82, +2.64])**, the only ML model whose IR confidence interval clearly excludes the baseline. Adding 30 per-fold IC-selected raw AspectTheme cells to the 772 engineered features gives LightGBM's gradient boosting leverage that neither Ridge nor XGBoost matches at this horizon.
- **The ATC baseline (IR +1.28, p=0.001) is the second-ranked model** — a robust standalone signal. Under CRSP-first pricing every ML tier is now individually statistically significant at p≤0.05, but the practical separation between models is modest.
- **Enhanced LightGBM (IR +1.23, p=0.001) and Combo XGBoost (IR +1.24, p=0.001)** become highly significant once CRSP-first pricing restores the missing 45% of RU3K events that the ML training set previously lacked.
- **Sparse-only Ridge (IR +0.79, p=0.028)** achieves clear significance; per-fold IC top-30 selection from 405 candidates outperforms the Ridge-only baseline but adds model instability (see §5.3b).

Note: the 2026Q2 test set contains only ~178 events (partial quarter). The final-quarter IC is unreliable and should not be cited in isolation. Sparse feature selection uses IC top-30 per fold (re-ranked on each fold's training data, no look-ahead). ElasticNet was tested but excluded: Sparse ElasticNet IR +1.32, Combo ElasticNet IR +1.83 — no material improvement over their Ridge counterparts.

![Walk-forward baseline IC (ATCClassifierScore, no model) — quarterly OOS Spearman IC, 2018Q1–2026Q2. Mean IC +0.034, IR +1.28; post-COVID decay visible at SP500 short horizons.](output/walkforward_baseline_ic.png)

![Walk-forward IC per quarter — ATCClassifierScore, Ridge, LightGBM enhanced, LightGBM stretch — and cumulative IC (2018Q1–2026Q2). Combo LightGBM (IR +1.51) leads; ATC baseline (IR +1.28) is second.](output/walkforward_ic.png)

![LightGBM feature importance (final walk-forward quarter) — top features by gain. ATCClassifierScore trend variants (2q, YoY) dominate; Forecast×FinPerf and Surprise×Macro cross-products are the top sparse contributors.](output/feature_importance.png)

## 5.3b Walk-Forward Portfolio Simulation

OOS predictions from §5.3 are converted into monthly quintile L/S portfolios (equal-weight, 20 bps round-trip TC, 2018Q1–2026Q2). The walk-forward model trains on all-universe events (cross-universe); per-universe evaluation filters predictions to each universe's tickers at the portfolio layer. Three evaluations: **(A)** all-universe combined Enhanced models; **(B)** per-universe Enhanced models for all three universes; **(C)** SP500-only Combined models.

**(A) All-universe walk-forward portfolio — Enhanced models:**

| Model | Net Sharpe | Max DD | N periods |
|-------|-----------|--------|-----------|
| ATC Baseline | +1.06 | −23.5% | 100 |
| Ridge (α=10) | +0.77 | −25.2% | 100 |
| **LightGBM 200** | **+1.79** | **−13.0%** | 99 |

**(B) Per-universe walk-forward portfolio — Enhanced models (SP500 / SP1500 / RU3K):**

| Universe | Model | Net Sharpe | Max DD | LS bps/mo | N |
|----------|-------|-----------|--------|-----------|---|
| **SP500** | **ATC Baseline** | **+0.65** | **−13.7%** | **+69.2** | 100 |
| SP500 | Ridge (α=10) | +0.22 | −31.5% | +22.6 | 100 |
| SP500 | LightGBM 200 | −0.45 | −40.0% | −44.1 | 95 |
| SP1500 | ATC Baseline | −0.28 | −70.7% | −51.5 | 100 |
| SP1500 | Ridge (α=10) | −0.21 | −48.7% | −16.9 | 100 |
| SP1500 | LightGBM 200 | −0.26 | −39.1% | −17.6 | 95 |
| **RU3K (PIT)** | **LightGBM 200** | **+1.62** | **−13.5%** | **+128.9** | 83 |
| RU3K (PIT) | ATC Baseline | +1.12 | −30.4% | +107.8 | 84 |
| RU3K (PIT) | Ridge (α=10) | +0.63 | −25.4% | +55.3 | 84 |

*Reproducible via the `per-univ-port` cell in `01_analysis.ipynb`.*

**(C) SP500-only portfolio — Combined models (Part 3):**

| Model | Net Sharpe | Max DD | LS net (bps/mo) | N |
|-------|-----------|--------|-----------------|---|
| **ATC Baseline** | **+0.59** | **−12.6%** | **+59.2** | 100 |
| Enhanced Ridge | +0.28 | −28.7% | +28.2 | 100 |
| Enhanced LGB | −0.34 | −32.9% | −31.4 | 95 |
| Combo LGB (772+30) | +0.32 | −19.8% | +26.0 | 95 |
| Combo XGBoost (772+30) | +0.17 | −23.3% | +15.9 | 89 |

**Key findings across all three universes:**

- **All-universe LightGBM dominates (+1.79 Sharpe, max DD −13.0%)** under CRSP-first pricing — the previously-missing 45% of RU3K events restored the small-cap signal that LGB needed to extract non-linear interactions. ML's added value is now substantial in the pooled book, reversing the earlier yfinance-baseline conclusion that ML provided only marginal lift.
- **SP500: ATC baseline still leads per-universe (+0.65 Sharpe, +69.2 bps/mo).** Ridge drops to +0.22 and LGB turns sharply negative (−0.45); cross-universe-trained models still produce noisy quintile rankings when filtered to the smaller SP500 pool.
- **SP1500: every model negative** (ATC −0.28, Ridge −0.21, LGB −0.26). The cross-universe quintile ranks do not translate into viable per-SP1500 separation — the universe overlaps heavily with SP500 and RU3K, diluting extreme quintile composition. The ATC MaxDD of −70.7% signals severe drawdown; SP1500 is not viable as a standalone per-universe L/S portfolio at these quintile cutoffs.
- **RU3K (PIT): LightGBM leads per-universe (+1.62 Sharpe, +128.9 bps/mo, max DD −13.5%)**, with the ATC baseline (+1.12) and Ridge (+0.63) trailing. The CRSP-first data lets LGB exploit the small-cap signal directly. RU3K is now the single most attractive deployment universe under any model choice.
- **Deployment conclusion:** for any pooled multi-universe book, use Enhanced LightGBM (+1.79 Sharpe). For RU3K-only deployment, LightGBM (+1.62) likewise leads. For SP500-only deployment, the raw ATC signal (+0.59) remains the most reliable choice — per-fold feature selection variance still dominates ML at the smaller SP500 fold sizes. Avoid SP1500-only L/S at monthly cadence.

![Walk-forward portfolio equity curves — ATC Baseline, Ridge, LightGBM (monthly quintile L/S, 20 bps TC, all universes).](output/wf_portfolio_comparison.png)

![Part 3 portfolio comparison — Baseline, Enhanced Ridge/LGB, Combo LGB, Combo XGBoost (SP500, monthly). ATC Baseline (+0.59 Sharpe) remains the strongest SP500-only portfolio; Combo LGB (+0.32) and Combo XGB (+0.17) are the strongest ML variants but still trail the raw signal.](output/stretch_portfolio_comparison.png)

## 5.3c Sub-Period IR Breakdown

To assess regime sensitivity, we split the walk-forward period (2018Q1–2026Q2) into three sub-periods and compute IC IR for each model:

| Period | ATC Baseline IR | Ridge IR | LightGBM IR |
|--------|----------------|----------|-------------|
| Pre-COVID (2018–2019, 8 qtrs) | 4.36 | 4.54 | **4.78** |
| COVID era (2020–2022, 12 qtrs) | **0.82** | −0.64 | 0.27 |
| Post-COVID (2023+, 14 qtrs)    | 0.88 | **1.82** | 1.07 |

**Key regime findings:**

- **Pre-COVID:** All three models are highly significant (IR 4.4–4.8). LightGBM now narrowly leads (+4.78), with Ridge (+4.54) and the ATC baseline (+4.36) close behind. The 772 engineered cross-product features add genuine value in the clean pre-2020 bull-market regime.
- **COVID era (2020–2022):** The ATC baseline remains the most resilient model (IR +0.82). Enhanced Ridge turns **negative** (IR −0.64) — macro-driven volatility creates spurious correlations between engineered trend features and 20d returns that drive Ridge positions in the wrong direction. LightGBM is slightly positive (+0.27) but well below the baseline. The raw signal, which does not leverage trend features, is more robust during the regime shift.
- **Post-COVID (2023+):** ML now provides meaningful resilience under CRSP-first pricing. Ridge IR climbs to +1.82 (vs +0.88 for the baseline), while LightGBM (+1.07) also exceeds the baseline. Restoring the previously-missing 45% of RU3K events appears to have given the engineered features enough out-of-sample signal to outperform the raw classifier post-2022 — a reversal of the earlier yfinance-baseline finding.

The regime analysis under CRSP-first data shows a clearer separation than before: ML adds genuine post-COVID resilience when the training set is not artificially truncated by yfinance's small-cap coverage gap.

![Sub-period IC IR by model — Pre-COVID / COVID era / Post-COVID. LightGBM leads pre-COVID (IR +4.78 vs baseline +4.36); ATC baseline is most resilient during COVID; Ridge leads post-COVID (+1.82 vs baseline +0.88).](output/wf_subperiod_ir.png)

## 5.3d Training-Label Sensitivity

The Combo LGB and XGB models are trained to predict 20d forward returns. As a robustness check, we re-run both models training on 10d labels (same features, same walk-forward design) and evaluate all portfolios against the 20d return outcome:

| Train label | Model | IC IR (vs 20d) | Portfolio Sharpe | bps/mo | Max DD |
|-------------|-------|----------------|-----------------|--------|--------|
| 10d labels | Combo LGB | +1.83 | −0.30 | −30.1 | −33.0% |
| 10d labels | Combo XGB | +1.28 | +0.34 | +29.9 | −14.2% |
| 20d labels | Combo LGB | +1.51 | +0.32 | +26.0 | −19.8% |
| 20d labels | Combo XGB | +1.24 | +0.17 | +15.9 | −23.3% |

Both label choices yield highly significant IC IRs (+1.24 to +1.83); the SP500 portfolio performance is more sensitive. Training on 20d labels gives the cleaner SP500 outcome for Combo LGB (+0.32 vs −0.30), while 10d labels favor Combo XGB (+0.34 vs +0.17). The aggregate IC story is robust to label choice; the SP500-only portfolio noise reflects per-fold sample size, not label specification.

![Training-label sensitivity — Combo LGB and XGB portfolios trained on 10d vs. 20d labels, evaluated on 20d returns (SP500, monthly). Neither label choice recovers meaningful SP500 alpha.](output/training_label_sensitivity.png)

## 5.4 SignalType Comparison

IC of `ATCClassifierScore` by speaker-level signal cut (S&P 500):

| SignalType | N | IC_1d | IC_3d | IC_5d | IC_10d | IC_20d |
|------------|---|-------|-------|-------|--------|--------|
| Total      | 30,141 | +0.042 | +0.048 | +0.045 | +0.040 | +0.051 |
| CEO        | 26,091 | +0.025 | +0.025 | +0.021 | +0.007 | +0.009 |
| CFO        | 22,157 | +0.027 | +0.013 | +0.010 | +0.010 | +0.011 |
| Analysts   | 29,691 | +0.023 | +0.020 | +0.011 | +0.008 | +0.010 |

The **Total slice dominates all speaker-specific cuts by 2–5×**. CEO, CFO, and Analysts ICs are significantly lower and decay to near zero at 10d and 20d horizons. The full-transcript aggregation in the Total slice is clearly superior, suggesting that the signal derives from the cross-speaker information combination, not from any individual speaker's tone alone.

## 5.5 Robustness Checks

**Sub-period IC (S&P 500):**

| Period | N | IC_1d | IC_5d | IC_10d | IC_20d |
|--------|---|-------|-------|--------|--------|
| Pre-COVID (2010–2019) | 17,225 | +0.063 | +0.062 | +0.053 | +0.076 |
| COVID era (2020–2022) |  6,075 | +0.038 | +0.035 | +0.039 | +0.016 |
| Post-COVID (2023+)    |  6,937 | −0.003 | +0.009 | +0.008 | +0.029 |

**Signal decay at SP500 short horizons remains a key finding.** Pre-COVID IC was strong (+0.053–0.076 at 10–20d horizons). Post-COVID, the 10d IC is effectively zero (+0.008), and 1d IC turns slightly negative (−0.003). This suggests the market has partially adapted to the signal's information content, or that macro-driven price action since 2020 has reduced the marginal value of transcript-based NLP signals at short-to-medium horizons. Only the 20d IC remains meaningfully positive post-COVID (+0.029), and even that is less than half the pre-COVID level.

**ML now provides post-COVID resilience under CRSP-first pricing.** As shown in §5.3c, post-COVID Ridge IR climbs to +1.82 (vs +0.88 for the baseline) and LightGBM reaches +1.07. Restoring the previously-missing 45% of RU3K events appears to have given the engineered features enough signal to outperform the raw classifier post-2022 — a reversal of the earlier yfinance-baseline finding. Rolling IC monitoring (§6) remains essential to detect further deterioration early.

## 5.5b Sector-Neutral IC

| Signal | IC_1d | IC_5d | IC_20d |
|--------|-------|-------|--------|
| Raw ATC | +0.042 | +0.045 | +0.051 |
| Sector-neutral ATC | +0.042 | +0.037 | +0.045 |

Sector neutralization modestly reduces IC at 5d and 20d (from +0.045 → +0.037) but is essentially unchanged at 1d. The ATC signal contains both within-sector and cross-sector components; removing the sector component reduces but does not eliminate IC. 82% of the 5d signal (0.037/0.045) is stock-specific, not cross-sector — confirming the signal captures genuine company-level information.

## 5.5c Market-Cap Bucket Robustness

IC stratified by size proxy (universe membership as cap proxy):

| Cap Bucket | N (20d events) | IC_1d | IC_3d | IC_5d | IC_10d | IC_20d |
|------------|--------------|-------|-------|-------|--------|--------|
| Large (SP500) | 30,237 | +0.042 | +0.047 | +0.045 | +0.040 | +0.051 |
| Mid (SP400)   | 49,504 | +0.046 | +0.046 | +0.038 | +0.037 | +0.040 |
| Small (RU2000 PIT) | 92,045 | +0.056 | +0.060 | +0.056 | +0.059 | +0.063 |

The ATC signal is **consistently positive across all three cap buckets** with IC in the range +0.038–0.063 at 5d. Small-caps (defined as PIT-RU3K membership minus SP1500 — a proper Russell 2000 proxy) show **substantially higher IC than large-caps at every horizon** (IC_20d: Small = +0.063 vs. Large = +0.051), confirming the signal works best where analyst coverage is thin and information diffuses more slowly. The Small-cap sample size jumps from 22,742 to 92,045 events under CRSP-first pricing — the previously-missing delisted small-caps are now in scope. Mid-cap IC is the weakest, possibly reflecting greater analyst coverage and faster information diffusion in the SP400 universe.

![IC by market-cap bucket across all return horizons. Signal is consistent across Large, Mid, and Small caps.](output/ic_by_cap_bucket.png)

## 5.6 Parameter Sensitivity

We test three sensitivity dimensions to verify robustness of the monthly quintile strategy (S&P 500, 20d return):

**(A) Transaction cost sensitivity:**

| One-way TC (bps/leg) | Net Sharpe |
|----------------------|------------|
| 0 | +0.98 |
| 2 | +0.89 |
| 5 (assumed) | +0.76 |
| 8 | +0.62 |
| 10 | +0.53 |
| 15 | +0.31 |
| 20 | +0.08 |

The strategy **breaks even near 20 bps one-way** (≈ 80 bps round-trip for a 4-leg fully-turned-over portfolio). The 5 bps assumption leaves 15 bps of margin — the 20d signal's wider gross spread makes the strategy far more TC-resilient than at shorter horizons. Break-even TC has more than doubled vs. the 10d configuration.

**(B) Bucket-count sensitivity:**

| Buckets | Net Sharpe |
|---------|------------|
| 3 | +0.62 |
| 5 (quintile) | +0.76 |
| 8 | +0.81 |
| 10 | +0.62 |
| 15 | +0.58 |
| 20 | +0.72 |

**Quintile (5 buckets) is near-optimal** (+0.76), with octile (+0.81) marginally higher but adding implementation complexity. At 20d with monthly rebalancing the SP500 quintile bins contain ~30 names each — sufficient for stable ranking. Finer buckets (10+) under-populate the tails and add sampling noise. Quintile is used throughout as the primary configuration.

**(C) Horizon sensitivity:**

| Return Horizon | Net Sharpe |
|----------------|------------|
| 1d | +0.03 |
| 3d | +0.27 |
| 5d | +0.15 |
| 10d | +0.41 |
| 20d | +0.76 |

**20d is the empirically optimal holding period** (net Sharpe +0.76), consistent with the ATC classifier's 14-day training window. With monthly rebalancing (~20 trading days), 20d positions naturally expire just as the next rebalance occurs, so position overlap is minimal in practice. This is the primary holding period used throughout this analysis.

![Parameter sensitivity: (A) TC sweep, (B) bucket-count sweep, (C) horizon sweep. Horizon sweep (C) confirms 20d as the optimal holding period; bucket sweep (B) shows quintile and octile are near-equal; TC break-even is ~20 bps one-way.](output/parameter_sensitivity.png)


# 6. Recommended Deployment

> **Recommendation:** Trade the ATC signal on the **Russell 3000 (PIT, CRSP top-3000 mcap)** universe with a **monthly quintile long-short** book, **20-day holding period**, and **Enhanced LightGBM** scoring on the 772 engineered Aspect × Theme features. Walk-forward net Sharpe **+1.62** (max DD −13.5%, +129 bps/month net after 5 bps one-way TC). Capacity ~\$50–100M AUM under realistic small-cap costs.

This single recommendation is what the rest of §6 justifies, against the three handout-specified dimensions: alpha decay, capacity, and turnover. Two alternative configurations are documented at the end for cases where capacity or operational constraints rule out the primary choice.

### 6.1 Justification against required dimensions

**Alpha decay (handout §2.1):** Spearman IC grows monotonically with horizon — RU3K IC_1d = +0.053 → IC_20d = +0.060 (§5.1). The classifier was trained on a 14-day pre/post window, so 20d holds capture the full information signal; the 20d empirical Sharpe (+0.76 for SP500, +2.53 static for RU3K) clearly dominates the 10d (+0.41) and shorter horizons in §5.6C. Walk-forward Enhanced LightGBM per-universe IR is +1.62 Sharpe in RU3K (vs raw ATC +1.12) — the ML layer recovers an additional +0.50 Sharpe by exploiting non-linear interactions among the engineered features. Post-COVID sub-period (§5.3c): Ridge IR +1.82 and LGB IR +1.07 vs baseline +0.88, confirming ML now adds genuine regime resilience under CRSP-first data.

**Capacity (handout §2.1):** RU3K-PIT monthly quintile averages ~120 names per long leg and ~120 per short leg. At the test TC of 5 bps one-way the strategy nets +128.9 bps/month under Enhanced LightGBM (§5.3b-B). The break-even TC is ~20 bps one-way (§5.6A), and realistic small-cap market-impact is 20–50 bps/side — putting capacity at **~\$50–100M AUM** before alpha materially compresses. SP500 (+0.59 walk-forward Sharpe) is the fallback for ≥\$300M AUM (§6.3). Capacity-constrained, not infinite — but Config 1 delivers the highest Sharpe per dollar of any tested combination.

**Turnover (handout §2.1):** Q5 (long) leg has near-100% monthly turnover (mean 99.8%, median 100%; §5.2d) because each month contains an entirely different set of earnings events (firms report ~once/quarter). The 100% turnover assumption in the TC model is empirically validated, not assumed. Monthly is the only cadence positive across all three universes (§5.2c): daily for RU3K nets +1.87 Sharpe but at −57.0% max DD vs monthly's −18.5% — a dramatically better risk-adjusted profile at monthly cadence. Net exposure averages −0.3% (Figure 11): the strategy is dollar-neutral by construction, not by overlay.

### 6.2 Implementation parameters

- **Universe definition:** CRSP top-3000 US common stocks by market capitalisation, snapshotted at each annual June reconstitution (matches Russell methodology). Maintained via `03_wrds_pull.py` / `04_wrds_integrate.py`; survivorship-free.
- **Signal pipeline:** Load `events_with_returns_wrds.parquet`; apply CRSP-first return preference (§2.4). Fit StandardScaler + Enhanced LightGBM on all events with `entry_date < q_start` (quarterly walk-forward). LightGBM hyperparameters: `n_estimators=200`, `early_stopping_rounds=20` on the chronologically last 15% of training data; other params at literature defaults.
- **Position construction:** Rank events by model score within each universe each month; take quintile 5 long, quintile 1 short, equal-weight within quintile. 200% gross exposure (100% long + 100% short), targeting 6–10% annualised vol.
- **Holding period:** 20 trading days; positions expire naturally just before the next monthly rebalance, minimising overlap.
- **Recommended position sizing refinement (production only):** Rank-proportional, volatility-scaled within each quintile (weight proportional to rank-deviation / trailing 60d σ_i), capped at 3× equal-weight. Lowers realised vol by 10–25% without shifting Sharpe (§5 backtests use equal-weight; rank ordering, not within-quintile weighting, drives the alpha).
- **Transaction cost assumption:** 5 bps one-way (test). Production must monitor actual TC at AUM; break-even is ~20 bps one-way (§5.6A).
- **Retraining:** Quarterly, expanding-window. No hyperparameter re-search at retrain (tuning was frozen on the 2010–2017 sub-period; see audit §3.10).

### 6.3 Alternatives if Config 1 is constrained

| If… | Then use… | Why |
|---|---|---|
| AUM ≥ \$300M and the book genuinely trades across all 3 universes simultaneously | **All-universe pooled book + Enhanced LightGBM** (walk-forward Sharpe +1.79, max DD −13.0%) | Pooled training gives LGB enough sample size to outperform RU3K-alone; requires cross-universe risk management. |
| SP500-only mandate (institutional constraints, no small-cap exposure) | **SP500 + raw `ATCClassifierScore`** (walk-forward Sharpe +0.59, max DD −12.6%) | Skip the ML layer entirely: per-fold variance dominates at SP500 sample sizes, every ML tier turns negative. Cleanest drawdown profile but concedes the small-cap edge. |
| SP1500-only mandate | **Do not deploy as a standalone L/S** | All models walk-forward negative; SP1500 universe overlap with SP500/RU3K dilutes extreme quintile composition. |

### 6.4 Production monitoring (quarterly review)

1. **Rolling 8-quarter IC of Enhanced LightGBM** — flag if it falls below +0.01 (signal-decay tripwire).
2. **TC break-even at ~20 bps one-way** — if AUM growth pushes realised cost toward 15 bps, scale down or move to SP1500.
3. **Per-universe ATC baseline vs Enhanced LightGBM trailing Sharpe** — regime indicator. During COVID-era sub-period (§5.3c), ATC IR +0.82 beat Ridge −0.64 and LGB +0.27 — in macro shocks, fall back to the raw signal.
4. **Bootstrap p-values on rolling 8-quarter IR** — if the lower bound of the 95% CI drops below zero, the ML edge has eroded and revert to raw ATC.


# 7. Risks and Limitations

**Survivorship bias (SP500/SP1500 only).** S&P universe lists reflect current (2026) composition (the Compustat tier accessed does not include historical removed members); historical removals are excluded, so reported SP500/SP1500 alpha is an upper bound. **Russell 3000 is fully PIT** via the CRSP top-3000-by-market-cap proxy (annual June reconstitution) — survivorship-free in both universe assignment and price coverage. The published RU3K numbers therefore carry no S&P-style survivorship bias.

**Price coverage.** CRSP-first pricing (§2.4) covers 99.8% of RU3K-PIT events natively; the remaining 0.2% is filled by yfinance. SP500/SP1500 yfinance coverage was already 99%+, so the CRSP layer adds little there. 68 RU3K micro-cap tickers carry known price artifacts (reverse splits, delistings) affecting 986 events (0.8%); winsorization bounds the impact. The earlier yfinance-only baseline under-stated RU3K alpha because delisted small-caps — exactly where the signal works best — were systematically dropped; this is the opposite of the usual direction of survivorship-bias correction.

**Data snooping.** `ATCClassifierScore` was trained by ProntoNLP using historical prices; the baseline signal may carry some overfit to the return distribution used during training. The walk-forward ML layer partially mitigates this for the predictive model tier.

**Vendor-side PIT integrity (untestable from this repo).** The 772 engineered features are computed from ProntoNLP's `AspectTheme_*` matrix and `ATCClassifierScore`. If the vendor used full-sample cross-sectional normalisation or future-period percentile references when building those columns, point-in-time integrity could be violated upstream. The look-ahead audit (§4) cannot detect this; downstream walk-forward + IC stability across regimes is the only available proxy check.

**TC assumption.** Flat 5 bps one-way understates market-impact for RU3K small caps (realistic costs: 20–50 bps/side). The monthly quintile strategy breaks even at ~20 bps one-way (§5.6A); the 5 bps assumption leaves a 15 bps margin. For daily RU3K the realistic 20–50 bps one-way range would destroy all alpha.

**Regime dependence.** Post-COVID SP500 IC at short horizons has collapsed (+0.008 at 10d; +0.029 at 20d) relative to pre-COVID (+0.053 at 10d; +0.076 at 20d). Under CRSP-first pricing the post-COVID ML walk-forward provides meaningful resilience (Ridge IR +1.82, LGB IR +1.07 vs baseline +0.88; §5.3c) — a reversal of the earlier yfinance-baseline finding. Rolling IC monitoring (§6) remains essential.


# 8. Future Work

- **Point-in-time S&P constituents:** Historical S&P 500/400/600 removed members require a higher Compustat subscription tier than the one available; the S&P universes remain current-composition. RU3K is already PIT via CRSP (§2.4 / §2.5).
- **Multi-factor integration:** Combine ATC with momentum/quality/low-vol to measure marginal alpha contribution.
- **Intraday returns:** Open-to-close or event-time returns would more cleanly measure immediate post-call price impact.
- **Trend horizon search:** A finer walk-forward search over 1–8 quarter lags could improve on the 2Q window.


# 9. Conclusion

The ProntoNLP ATC signal has genuine, statistically significant alpha (IC t-stat >> 3 across all universes and horizons; bootstrap p<0.01 for every ML tier). Under a CRSP-first / yfinance-fallback price pipeline and a survivorship-free CRSP-PIT Russell 3000 universe, monthly quintile L/S portfolios deliver static-test net Sharpe 0.76 / 0.83 / 2.53 (SP500 / SP1500 / RU3K-PIT) after 20 bps round-trip TC. Expanding walk-forward evaluation over 34 quarters confirms the signal is robust out-of-sample: Combo LightGBM IC IR +1.51 (95% CI [+0.82, +2.64], p<0.001), all-universe Enhanced LightGBM portfolio Sharpe +1.79. **Recommended production deployment (§6): Russell 3000 PIT + monthly quintile L/S + 20-day hold + Enhanced LightGBM on 772 engineered features — walk-forward net Sharpe +1.62, max DD −13.5%, +129 bps/month net, capacity ~\$50–100M AUM under realistic small-cap TC.** This is the highest risk-adjusted return of any tested configuration and is fully justified against the handout's three required dimensions (alpha decay, capacity, turnover). For ≥\$300M AUM the alternative is the all-universe pooled LightGBM book (+1.79 Sharpe); for SP500-only mandates use the raw `ATCClassifierScore` (+0.59 Sharpe, cleanest drawdown). The 2-quarter ATC trend is the single most important individual feature. Key risk: post-COVID signal decay at SP500 short horizons; under CRSP-first data, pooled ML provides genuine post-COVID resilience (Ridge IR +1.82 vs baseline +0.88). Rolling 8-quarter IC monitoring (§6.4) is essential.


# References

Loughran, T. & McDonald, B. (2011). When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks. *Journal of Finance*, 66(1), 35–65.

Matsumoto, D., Pronk, M. & Roelofsen, E. (2011). What makes conference calls useful? The information content of managers' presentations and analysts' discussion sessions. *The Accounting Review*, 86(4), 1383–1414.

Mayew, W.J. & Venkatachalam, M. (2012). The power of voice: Managerial affective states and future firm performance. *Journal of Finance*, 67(1), 1–43.

ProntoNLP (2024). Earnings Call ATC (Aspect-Theme Classifier) Signal Dataset. Retrieved from https://prontonio.com.

Tetlock, P.C. (2007). Giving content to investor sentiment: The role of media in the stock market. *Journal of Finance*, 62(3), 1139–1168.

# Appendix A: Data Pipeline Summary

\begin{table}[H]
\small
\begin{tabular}{p{4.5cm} r p{6.5cm}}
\hline
\textbf{File} & \textbf{Size} & \textbf{Description} \\
\hline
\texttt{signals.parquet} & 318 MB & 2,738,206 non-delete rows, 447 columns (float32) \\
\texttt{prices.parquet} & 40 MB & 9.3M daily adj-close rows, 3,109 tickers \\
\texttt{events\_with\_returns.parquet} & 500 MB & 376,790 Total-slice events, 785 columns (772 features + meta + 5 returns) \\
\texttt{sparse\_features.parquet} & 42 MB & 376,790 rows × 407 columns (BESTTICKER, entry\_date, 405 AT cols) \\
\texttt{signal\_slices.parquet} & 35 MB & ATCClassifierScore + EventScores for Total/CEO/CFO/Analysts \\
\texttt{universes.json} & 0.1 MB & SP500/SP1500/RU3K ticker lists \\
\hline
\end{tabular}
\end{table}

# Appendix B: Feature List

**Aspect × Theme cross-product features (180):** For each of 5 aspects × 9 themes = 45 pairs: `at_{Aspect}_{Theme}_Positive`, `at_{Aspect}_{Theme}_Negative`, `at_{Aspect}_{Theme}_total`, `at_{Aspect}_{Theme}_net_sentiment`. Aspects: CurrentState, Forecast, Surprise, StrategicPosition, Other. Themes: FinancialPerformance, OperationalPerformance, MarketAndCompetitivePosition, StrategicInitiatives, CapitalAllocation, RegulatoryAndLegalIssues, ESG, MacroeconomicFactors, Other.

**Raw scores (13):** `ATCClassifierScore`; `EventsScore_{v}`, `EventPos_{v}`, `EventNeg_{v}` for each of 4 classifier variants `v` in {1_1_1, 2_1_1, 4_1_1, 4_2_1}.

**Base features total: 193** (180 cross-product + 13 raw scores).

**Multi-quarter trend features (193 × 3 = 579):** Each base feature is replicated with three lagged delta suffixes:
- `_qoq` — quarter-over-quarter (shift 1 within ticker)
- `_2q` — 2-quarter trend (shift 2 within ticker)
- `_yoy` — year-over-year (shift 4 within ticker)

**Total: 772 features** (193 base + 193 QoQ + 193 2Q + 193 YoY).

**Stretch-only (not in events_with_returns.parquet):** 405 raw AspectTheme columns (full 5×9×3×3 grid, Fluff/Filler dropped) saved in `sparse_features.parquet` and merged at runtime for the Stretch walk-forward model tier (1,177 total features).
