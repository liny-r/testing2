"""
Standalone helper for §5.2 / §5.2b per-leg Sharpe reporting (handout §2.2:
"report long-only, short-only, and long-short cumulative returns and Sharpe").

Computes monthly quintile (Q5 vs Q1) and decile (D10 vs D1) portfolios on
`ATCClassifierScore`, reports gross + net Sharpe for the long leg, short leg,
and L/S spread per universe. Mirrors `quintile_portfolio()` in 01_analysis.ipynb
so numbers reconcile with §5.2's L/S row.

Reads `events_with_returns_wrds.parquet` if available (with `in_RU3K_PIT`),
otherwise falls back to `events_with_returns.parquet` (with `in_RU3K`).
Runtime: ~3 seconds.

Output:
  - reports/output/leg_sharpe_table.md   (paste-ready markdown)
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT_DIR = ROOT / "reports" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TC_BPS = 5  # one-way, per handout
ANN = 12    # monthly periods per year


def load_events() -> pd.DataFrame:
    wrds = DATA / "events_with_returns_wrds.parquet"
    base = DATA / "events_with_returns.parquet"
    if wrds.exists():
        df = pd.read_parquet(wrds)
        ru3k_col = "in_RU3K_PIT"
        for h in [1, 3, 5, 10, 20]:
            crsp = f"crsp_return_{h}d"
            yf = f"return_{h}d"
            if crsp in df.columns and yf in df.columns:
                m = df[crsp].notna()
                df.loc[m, yf] = df.loc[m, crsp]
        print(f"Loaded {len(df):,} rows from {wrds.name} (RU3K = {ru3k_col})")
    else:
        df = pd.read_parquet(base)
        ru3k_col = "in_RU3K"
        print(f"Loaded {len(df):,} rows from {base.name} (RU3K = {ru3k_col})")
    return df, ru3k_col


def cut_portfolio(df_sub: pd.DataFrame, n_buckets: int, ret_col: str = "return_20d") -> pd.DataFrame:
    """Monthly long-top-bucket / short-bottom-bucket book on ATCClassifierScore."""
    sub = df_sub[df_sub[ret_col].notna() & df_sub["ATCClassifierScore"].notna()].copy()
    sub["_period"] = sub["entry_date"].dt.to_period("M")

    records = []
    for period, grp in sub.groupby("_period"):
        if len(grp) < 2 * n_buckets:
            continue
        g = grp.copy()
        try:
            g["_b"] = pd.qcut(g["ATCClassifierScore"], n_buckets, labels=False, duplicates="drop")
        except ValueError:
            continue
        if g["_b"].nunique() < n_buckets:
            continue
        bm = g.groupby("_b")[ret_col].mean()
        top = bm.iloc[-1]
        bot = bm.iloc[0]
        records.append({
            "period": period.to_timestamp(),
            "top": top,
            "bot": bot,
            "long_net": top - 2 * TC_BPS / 1e4,
            "short_net": -bot - 2 * TC_BPS / 1e4,
            "ls": top - bot,
            "ls_net": top - bot - 4 * TC_BPS / 1e4,
            "n_events": len(grp),
        })
    return pd.DataFrame(records).set_index("period").sort_index()


def sharpe(series: pd.Series) -> float:
    if series.std() == 0 or len(series) < 2:
        return float("nan")
    return float(series.mean() / series.std() * np.sqrt(ANN))


def per_universe_legs(df: pd.DataFrame, universes: dict, n_buckets: int) -> pd.DataFrame:
    rows = []
    for uname, ucol in universes.items():
        pf = cut_portfolio(df[df[ucol].fillna(False)], n_buckets=n_buckets)
        if pf.empty:
            continue
        rows.append({
            "Universe": uname,
            "N periods": len(pf),
            "L-only Sharpe (net)": round(sharpe(pf["long_net"]), 2),
            "S-only Sharpe (net)": round(sharpe(pf["short_net"]), 2),
            "L/S Sharpe (net)": round(sharpe(pf["ls_net"]), 2),
            "L/S Sharpe (gross)": round(sharpe(pf["ls"]), 2),
        })
    return pd.DataFrame(rows).set_index("Universe")


def write_markdown(quintile: pd.DataFrame, decile: pd.DataFrame, path: Path) -> None:
    lines = ["**Quintile (Q5 long / Q1 short, monthly, 20d hold, 5 bps one-way TC):**", ""]
    lines.append("| Universe | L-only Sharpe (net) | S-only Sharpe (net) | L/S Sharpe (net) | L/S Sharpe (gross) | N periods |")
    lines.append("|---|---|---|---|---|---|")
    for u, r in quintile.iterrows():
        lines.append(
            f"| {u} | {r['L-only Sharpe (net)']:+.2f} | {r['S-only Sharpe (net)']:+.2f} | "
            f"{r['L/S Sharpe (net)']:+.2f} | {r['L/S Sharpe (gross)']:+.2f} | {int(r['N periods'])} |"
        )
    lines += ["", "**Decile (D10 long / D1 short, monthly, 20d hold, 5 bps one-way TC):**", ""]
    lines.append("| Universe | L-only Sharpe (net) | S-only Sharpe (net) | L/S Sharpe (net) | L/S Sharpe (gross) | N periods |")
    lines.append("|---|---|---|---|---|---|")
    for u, r in decile.iterrows():
        lines.append(
            f"| {u} | {r['L-only Sharpe (net)']:+.2f} | {r['S-only Sharpe (net)']:+.2f} | "
            f"{r['L/S Sharpe (net)']:+.2f} | {r['L/S Sharpe (gross)']:+.2f} | {int(r['N periods'])} |"
        )
    path.write_text("\n".join(lines))


def main():
    df, ru3k_col = load_events()
    universes = {
        "SP500": "in_SP500",
        "SP1500": "in_SP1500",
        "RU3K (PIT)": ru3k_col,
    }

    quintile = per_universe_legs(df, universes, n_buckets=5)
    decile = per_universe_legs(df, universes, n_buckets=10)

    print()
    print("=== Quintile (Q5 vs Q1) ===")
    print(quintile.to_string())
    print()
    print("=== Decile (D10 vs D1) ===")
    print(decile.to_string())

    out = OUT_DIR / "leg_sharpe_table.md"
    write_markdown(quintile, decile, out)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
