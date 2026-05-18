"""
Standalone helper for two report items the main analysis notebook does not emit:

  (1) §5.1 EventScore IC table — 4 score variants × 5 return horizons × 3 universes.
      Handout §1.4(a) defines the family as {1_1_1, 4_2_1, 3_1_0, 1_1_0}.
  (2) §4.2 Per-quarter event counts per universe (with a <100-event flag).

Reads only `data/events_with_returns.parquet` (already filtered to SignalType=Total
in 00_data_prep). Writes:
  - reports/output/event_score_ic_table.md   (paste-ready markdown)
  - reports/output/events_per_quarter.png    (chart referenced by §4.2)
  - reports/output/events_per_quarter.md     (paste-ready summary table)

Runtime: ~3 seconds.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent
PARQUET = ROOT / "data" / "events_with_returns.parquet"
OUT_DIR = ROOT / "reports" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VARIANTS = ["EventsScore_1_1_1", "EventsScore_4_2_1", "EventsScore_3_1_0", "EventsScore_1_1_0"]
HORIZONS = [1, 3, 5, 10, 20]
UNIVERSES = [("SP500", "in_SP500"), ("SP1500", "in_SP1500"), ("RU3K (PIT)", "in_RU3K")]


def spearman_ic(x: pd.Series, y: pd.Series) -> float:
    m = x.notna() & y.notna()
    if m.sum() < 50:
        return np.nan
    rho, _ = spearmanr(x[m], y[m])
    return float(rho)


def build_event_score_ic(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for uname, flag in UNIVERSES:
        sub = df[df[flag] == True]
        n_20d = int((sub["return_20d"].notna() & sub[VARIANTS[0]].notna()).sum())
        for var in VARIANTS:
            row = {"Universe": uname, "Signal": var, "N": n_20d}
            for h in HORIZONS:
                row[f"IC_{h}d"] = spearman_ic(sub[var], sub[f"return_{h}d"])
            rows.append(row)
    return pd.DataFrame(rows)


def write_event_score_md(tbl: pd.DataFrame, path: Path) -> None:
    lines = []
    for uname, _ in UNIVERSES:
        sub = tbl[tbl["Universe"] == uname]
        lines.append(f"**{uname}** (N = {sub['N'].iloc[0]:,}):")
        lines.append("")
        lines.append("| Signal | IC_1d | IC_3d | IC_5d | IC_10d | IC_20d |")
        lines.append("|--------|-------|-------|-------|--------|--------|")
        for _, r in sub.iterrows():
            fmt = lambda v: f"{v:+.3f}" if pd.notna(v) else "—"
            lines.append(
                f"| `{r['Signal']}` | {fmt(r['IC_1d'])} | {fmt(r['IC_3d'])} | "
                f"{fmt(r['IC_5d'])} | {fmt(r['IC_10d'])} | {fmt(r['IC_20d'])} |"
            )
        lines.append("")
    path.write_text("\n".join(lines))


def build_per_quarter(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["quarter"] = pd.PeriodIndex(d["entry_date"], freq="Q")
    out = pd.DataFrame(index=sorted(d["quarter"].unique()))
    for uname, flag in UNIVERSES:
        col = d[d[flag] == True].groupby("quarter").size()
        out[uname] = col
    out = out.fillna(0).astype(int)
    return out


def plot_per_quarter(counts: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 4.2))
    x = np.arange(len(counts.index))
    width = 0.28
    for i, uname in enumerate(counts.columns):
        ax.bar(x + (i - 1) * width, counts[uname].values, width, label=uname)
    ax.axhline(100, color="red", linestyle="--", linewidth=0.8, label="N=100 floor")
    ax.set_xticks(x[::4])
    ax.set_xticklabels([str(q) for q in counts.index[::4]], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Events per quarter")
    ax.set_title("Events per quarter, by universe (SignalType=Total)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def write_per_quarter_summary(counts: pd.DataFrame, path: Path) -> None:
    first_q = counts.index.min()
    last_q = counts.index.max()
    lines = [
        f"Coverage: {first_q} → {last_q} ({len(counts)} quarters).",
        "",
        "| Universe | Median per quarter | Min | Max | Quarters with N<100 |",
        "|----------|--------------------|-----|-----|---------------------|",
    ]
    for u in counts.columns:
        thin_qs = counts.index[counts[u] < 100].tolist()
        thin_str = (
            ", ".join(str(q) for q in thin_qs) if thin_qs else "—"
        )
        lines.append(
            f"| {u} | {int(counts[u].median()):,} | {int(counts[u].min()):,} | "
            f"{int(counts[u].max()):,} | {len(thin_qs)} ({thin_str}) |"
        )
    path.write_text("\n".join(lines))


def main():
    df = pd.read_parquet(PARQUET)
    print(f"Loaded {len(df):,} rows from {PARQUET.name}")

    ic_tbl = build_event_score_ic(df)
    write_event_score_md(ic_tbl, OUT_DIR / "event_score_ic_table.md")
    print(f"Wrote {OUT_DIR / 'event_score_ic_table.md'}")

    counts = build_per_quarter(df)
    plot_per_quarter(counts, OUT_DIR / "events_per_quarter.png")
    write_per_quarter_summary(counts, OUT_DIR / "events_per_quarter.md")
    print(f"Wrote {OUT_DIR / 'events_per_quarter.png'}")
    print(f"Wrote {OUT_DIR / 'events_per_quarter.md'}")

    print()
    print("--- EventScore IC ---")
    print(ic_tbl.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
    print()
    print("--- Per-quarter summary ---")
    print(counts.describe().round(0).to_string())


if __name__ == "__main__":
    main()
