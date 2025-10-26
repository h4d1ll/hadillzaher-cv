# -*- coding: utf-8 -*-
"""
Banking Crises & Stress Testing (2024)
Includes:
- Rate shock losses on AFS/HTM portfolios (duration method)
- Deposit outflow liquidity runway (LCR-style)
- Simple interbank contagion toy model
- Combined Excel dashboard with Summary sheet

Outputs:
  assets/stress_liquidity.png
  assets/stress_contagion.png
  Banking_Stress_Testing_2024.xlsx
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------- Setup ----------
os.makedirs("assets", exist_ok=True)
plt.rcParams.update({"figure.dpi": 160, "axes.grid": True})
pd.options.display.float_format = "{:,.2f}".format

# ---------- Core Assumptions ----------
assumptions = {
    "Starting CET1 Capital": 25_000_000_000,
    "AFS Securities (market value)": 180_000_000_000,
    "HTM Securities (amortized cost)": 100_000_000_000,
    "AFS Duration (yrs)": 3.2,
    "HTM Duration (yrs)": 6.0,
    "Liquidity Buffer (HQLA)": 200_000_000_000,
    "Deposit Base": 800_000_000_000,
    "Liquidity Haircut (%)": 5.0,
    "Stress Horizon (days)": 30,
}

rate_shocks_bps = np.array([50, 100, 150, 200, 300, 400])
rate_shocks = rate_shocks_bps / 10_000.0
outflow_daily_pct = np.array([0.5, 1.0, 1.5, 2.0])

# Simple interbank network
exposure_bn = pd.DataFrame(
    [[0, 15, 5],
     [8, 0, 12],
     [6, 10, 0]],
    index=["Bank A", "Bank B", "Bank C"],
    columns=["Bank A", "Bank B", "Bank C"]
)
loss_given_default = 0.6
shock_default = "Bank B"

# ---------- 1. Rate Shock CET1 Impact ----------
afs_mv = assumptions["AFS Securities (market value)"]
htm_ac = assumptions["HTM Securities (amortized cost)"]
dur_afs = assumptions["AFS Duration (yrs)"]
dur_htm = assumptions["HTM Duration (yrs)"]
start_cet1 = assumptions["Starting CET1 Capital"]

rate_loss_tbl = []
for dr in rate_shocks:
    afs_loss = afs_mv * dur_afs * dr
    htm_loss = htm_ac * dur_htm * dr
    cet1_hit = afs_loss / start_cet1 * 100
    econ_hit = (afs_loss + htm_loss) / start_cet1 * 100
    rate_loss_tbl.append({
        "Rate Shock (bps)": int(dr * 10_000),
        "AFS Loss ($)": afs_loss,
        "HTM Econ Loss ($)": htm_loss,
        "CET1 Hit (%)": cet1_hit,
        "Econ CET1 Hit (%)": econ_hit
    })
rate_loss_tbl = pd.DataFrame(rate_loss_tbl)

# ---------- 2. Liquidity Runway ----------
def liquidity_runway(days, outflow_pct, buffer, haircut, base_dep):
    usable = buffer * (1 - haircut / 100)
    path = []
    for d in range(1, days + 1):
        out = outflow_pct / 100 * base_dep
        usable = max(0, usable - out)
        path.append({"Day": d, "HQLA Remaining": usable})
        if usable <= 0:
            break
    return pd.DataFrame(path)

runway_paths = {p: liquidity_runway(assumptions["Stress Horizon (days)"], p,
                                   assumptions["Liquidity Buffer (HQLA)"],
                                   assumptions["Liquidity Haircut (%)"],
                                   assumptions["Deposit Base"]) for p in outflow_daily_pct}

liq_summary = pd.DataFrame([{
    "Outflow / Day (%)": p,
    "Days Survived": len(df),
    "End HQLA ($)": df["HQLA Remaining"].iloc[-1]
} for p, df in runway_paths.items()])

# ---------- 3. Contagion Model ----------
def contagion_round(exposure_df, defaults, lgd=0.6, threshold=10.0):
    losses = exposure_df[list(defaults)].sum(axis=1) * lgd
    new_defaults = set(losses[losses > threshold].index) - set(defaults)
    return losses, new_defaults

defaults = {shock_default}
loss_history = []
for r in range(1, 4):
    losses, new_def = contagion_round(exposure_bn, defaults, loss_given_default, threshold=8.0)
    loss_history.append(pd.DataFrame({"Round": r, "Bank": losses.index, "Loss (bn)": losses.values}))
    defaults |= new_def
    if not new_def:
        break
spillover_tbl = pd.concat(loss_history, ignore_index=True)

# ---------- 4. PNG Charts ----------
plt.figure(figsize=(10, 6))
for p, df in runway_paths.items():
    plt.plot(df["Day"], df["HQLA Remaining"] / 1e9, label=f"{p:.1f}%/day", lw=2)
plt.title("Liquidity Runway — HQLA vs Outflows")
plt.xlabel("Day"); plt.ylabel("HQLA (bn)"); plt.legend(); plt.tight_layout()
plt.savefig("assets/stress_liquidity.png", bbox_inches="tight", facecolor="white")
plt.close()

if not spillover_tbl.empty:
    M = spillover_tbl.pivot(index="Bank", columns="Round", values="Loss (bn)").fillna(0)
    plt.figure(figsize=(7, 5))
    plt.imshow(M, cmap="Reds"); plt.colorbar(label="Loss (bn)")
    plt.xticks(range(len(M.columns)), [f"R{r}" for r in M.columns])
    plt.yticks(range(len(M.index)), M.index)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            plt.text(j, i, f"{M.values[i, j]:.1f}", ha="center", va="center")
    plt.title("Interbank Spillover Heatmap"); plt.tight_layout()
    plt.savefig("assets/stress_contagion.png", bbox_inches="tight", facecolor="white")
    plt.close()

# ---------- 5. Excel Workbook ----------
OUT = "Banking_Stress_Testing_2024.xlsx"
with pd.ExcelWriter(OUT, engine="xlsxwriter") as writer:
    pd.DataFrame.from_dict(assumptions, orient="index", columns=["Value"]).to_excel(writer, "Assumptions")
    rate_loss_tbl.to_excel(writer, "Rate_Shock_Losses", index=False)
    liq_summary.to_excel(writer, "Liquidity_Summary", index=False)
    exposure_bn.to_excel(writer, "Interbank_Exposure (bn)")
    spillover_tbl.to_excel(writer, "Spillover_Rounds", index=False)

    # Summary sheet
    summary_data = pd.DataFrame({
        "Metric": [
            "Max CET1 Hit (%)",
            "Avg Liquidity Days Survived",
            "Max Interbank Loss (bn)"
        ],
        "Value": [
            rate_loss_tbl["CET1 Hit (%)"].max(),
            liq_summary["Days Survived"].mean(),
            spillover_tbl["Loss (bn)"].max()
        ]
    })
    summary_data.to_excel(writer, "Summary", index=False)

    wb = writer.book
    ws = writer.sheets["Summary"]
    fmt_head = wb.add_format({"bold": True, "bg_color": "#DDEBF7", "border": 1})
    for i, c in enumerate(summary_data.columns):
        ws.write(0, i, c, fmt_head)
        ws.set_column(i, i, 28)

    # Chart 1: CET1 vs rate shock
    ws_rate = writer.sheets["Rate_Shock_Losses"]
    chart1 = wb.add_chart({"type": "line"})
    n = len(rate_loss_tbl)
    chart1.add_series({
        "name": "CET1 Hit (%)",
        "categories": ["Rate_Shock_Losses", 1, 0, n, 0],
        "values": ["Rate_Shock_Losses", 1, 3, n, 3],
    })
    chart1.set_title({"name": "CET1 Hit vs Rate Shock"})
    chart1.set_legend({"position": "bottom"})
    ws.insert_chart("H2", chart1)

    # Chart 2: Liquidity vs outflow
    ws_liq = writer.sheets["Liquidity_Summary"]
    chart2 = wb.add_chart({"type": "column"})
    m = len(liq_summary)
    chart2.add_series({
        "name": "Days Survived",
        "categories": ["Liquidity_Summary", 1, 0, m, 0],
        "values": ["Liquidity_Summary", 1, 1, m, 1],
    })
    chart2.set_title({"name": "Liquidity Survival vs Outflow Rate"})
    chart2.set_legend({"position": "bottom"})
    ws_liq.insert_chart("E2", chart2)

print(f"✅ Wrote: {OUT}")
print("🖼️ Saved: assets/stress_liquidity.png")
print("🖼️ Saved: assets/stress_contagion.png")
