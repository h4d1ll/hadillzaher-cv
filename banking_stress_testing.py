# -*- coding: utf-8 -*-
"""
🏦 Banking Crises & Stress Testing (2024)
Simulates liquidity stress, contagion, and bond markdown impacts.
Generates charts and an Excel dashboard.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

os.makedirs("assets", exist_ok=True)
plt.rcParams.update({"figure.dpi": 160, "axes.grid": True})

OUT_XLSX = "Banking_Stress_Testing_2024.xlsx"

# -----------------------------
# 1️⃣ Liquidity Stress Simulation
# -----------------------------
np.random.seed(42)
days = np.arange(1, 31)
banks = ["SVB", "Credit Suisse", "Regional Avg"]

# simulate daily deposit outflows (% of total)
outflows = {
    "SVB": np.clip(np.cumsum(np.random.normal(2.0, 0.6, len(days))), 0, 100),
    "Credit Suisse": np.clip(np.cumsum(np.random.normal(1.2, 0.5, len(days))), 0, 100),
    "Regional Avg": np.clip(np.cumsum(np.random.normal(0.4, 0.2, len(days))), 0, 100),
}
liq_df = pd.DataFrame(outflows, index=days)
liq_df.index.name = "Day"

# -----------------------------
# 2️⃣ Bond Portfolio Losses
# -----------------------------
durations = np.array([1, 2, 5, 10])
rate_shocks = np.linspace(0, 2, 9)

# Compute PV loss as a matrix (duration × shock)
loss_matrix = np.outer(durations, rate_shocks) * -1 / 100
loss_df = pd.DataFrame(loss_matrix, index=[f"{d}Y" for d in durations],
                       columns=[f"{r:.2f}%" for r in rate_shocks])

loss_df.index.name = "Rate Shock (%)"

# -----------------------------
# 3️⃣ Contagion Simulation
# -----------------------------
banks_network = ["A", "B", "C", "D", "E"]
exposures = np.random.uniform(0, 1, size=(5, 5))
np.fill_diagonal(exposures, 0)
exposure_df = pd.DataFrame(exposures, index=banks_network, columns=banks_network)

threshold = 1.2
loss_given_default = 0.6

def contagion_round(exposure_df, defaults, lgd=0.6, threshold=1.2):
    losses = exposure_df[list(defaults)].sum(axis=1) * lgd
    new_defaults = set(exposure_df.index[losses > threshold])
    return losses, new_defaults

defaults = {"A"}  # initial failing bank
rounds = []
for r in range(1, 6):
    losses, new_defaults = contagion_round(exposure_df, defaults, loss_given_default, threshold)
    rounds.append(pd.DataFrame({
        "Round": r,
        "Bank": exposure_df.index,
        "Losses": losses,
        "Defaulted": exposure_df.index.isin(defaults)
    }))
    if not new_defaults or new_defaults.issubset(defaults):
        break
    defaults |= new_defaults

contagion_df = pd.concat(rounds)

# -----------------------------
# 4️⃣ Chart: Liquidity Stress
# -----------------------------
plt.figure(figsize=(10, 6))
for b in liq_df.columns:
    plt.plot(liq_df.index, liq_df[b], label=b, linewidth=2)
plt.title("Liquidity Stress — Cumulative Deposit Outflows")
plt.xlabel("Days")
plt.ylabel("Cumulative Outflows (% of Deposits)")
plt.legend()
plt.tight_layout()
plt.savefig("assets/stress_liquidity.png", bbox_inches="tight", facecolor="white")
plt.close()

# -----------------------------
# 5️⃣ Chart: Contagion Map
# -----------------------------
pivot = contagion_df.pivot(index="Bank", columns="Round", values="Losses")
plt.figure(figsize=(7, 5))
plt.imshow(pivot, cmap="Reds", aspect="auto")
plt.colorbar(label="Exposure Loss")
plt.xticks(np.arange(len(pivot.columns)), pivot.columns)
plt.yticks(np.arange(len(pivot.index)), pivot.index)
plt.title("Contagion Simulation — Loss Propagation by Round")
plt.tight_layout()
plt.savefig("assets/stress_contagion.png", bbox_inches="tight", facecolor="white")
plt.close()

# -----------------------------
# 6️⃣ Excel Dashboard
# -----------------------------
with pd.ExcelWriter(OUT_XLSX, engine="xlsxwriter") as writer:
    liq_df.to_excel(writer, sheet_name="Liquidity_Stress")
    loss_df.to_excel(writer, sheet_name="Bond_Losses")
    contagion_df.to_excel(writer, sheet_name="Contagion_Simulation", index=False)

    wb = writer.book

    # Add liquidity chart
    ws_liq = writer.sheets["Liquidity_Stress"]
    chart_liq = wb.add_chart({"type": "line"})
    for i, b in enumerate(banks):
        chart_liq.add_series({
            "name": ["Liquidity_Stress", 0, i+1],
            "categories": ["Liquidity_Stress", 1, 0, len(liq_df), 0],
            "values": ["Liquidity_Stress", 1, i+1, len(liq_df), i+1]
        })
    chart_liq.set_title({"name": "Liquidity Stress — Deposit Outflows"})
    chart_liq.set_legend({"position": "bottom"})
    ws_liq.insert_chart("G2", chart_liq)

    # Add bond loss chart
    ws_bond = writer.sheets["Bond_Losses"]
    chart_loss = wb.add_chart({"type": "line"})
    for i, d in enumerate(loss_df.columns):
        chart_loss.add_series({
            "name": ["Bond_Losses", 0, i+1],
            "categories": ["Bond_Losses", 1, 0, len(loss_df), 0],
            "values": ["Bond_Losses", 1, i+1, len(loss_df), i+1]
        })
    chart_loss.set_title({"name": "Bond Portfolio Losses vs Rate Shocks"})
    chart_loss.set_x_axis({"name": "Rate Shock (%)"})
    chart_loss.set_y_axis({"name": "Portfolio Loss (%)"})
    chart_loss.set_legend({"position": "bottom"})
    ws_bond.insert_chart("G2", chart_loss)

print(f"✅ Dashboard written to: {OUT_XLSX}")
print("🖼️ Charts saved:")
print("   - assets/stress_liquidity.png")
print("   - assets/stress_contagion.png")
