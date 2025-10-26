# -*- coding: utf-8 -*-
# 💰 Personal Investing Playbook — DCA & Rebalancing Simulation

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("assets", exist_ok=True)
plt.rcParams.update({"figure.dpi": 160, "axes.grid": True})

OUT_XLSX = "Personal_Investing_Playbook.xlsx"
np.random.seed(42)

# ---- Parameters ----
years = 10
months = years * 12
initial_investment = 0
monthly_contribution = 500
rebalance_threshold = 0.05  # 5% drift trigger

# Simulated assets: ETF A (equity), ETF B (bond)
mu = np.array([0.07, 0.03])  # annual return
sigma = np.array([0.15, 0.05])
rho = 0.2  # correlation

cov = np.outer(sigma, sigma) * rho
np.fill_diagonal(cov, sigma ** 2)

returns = np.random.multivariate_normal(mu / 12, cov / np.sqrt(12), months)
weights = np.array([0.7, 0.3])  # starting allocation

# ---- Simulation ----
values = np.zeros((months, 2))
portfolio = np.zeros(months)
cash_flows = []

for i in range(months):
    # monthly contribution split by weights
    if i == 0:
        values[i] = weights * monthly_contribution
    else:
        values[i] = values[i-1] * (1 + returns[i]) + weights * monthly_contribution

    total = values[i].sum()
    portfolio[i] = total
    cash_flows.append(monthly_contribution)

    # rebalancing
    current_w = values[i] / total
    drift = np.abs(current_w - weights)
    if (drift > rebalance_threshold).any():
        values[i] = total * weights  # rebalance to target

# ---- Summary ----
total_invested = np.cumsum(cash_flows)
gain = portfolio - total_invested
growth_df = pd.DataFrame({
    "Month": np.arange(1, months + 1),
    "Portfolio Value": portfolio,
    "Total Invested": total_invested,
    "Net Gain": gain,
})
growth_df["Year"] = np.ceil(growth_df["Month"] / 12).astype(int)

# ---- Rebalance timeline ----
rebalance_points = []
for i in range(1, months):
    w = values[i] / values[i].sum()
    if np.abs(w[0] - weights[0]) > rebalance_threshold:
        rebalance_points.append(i)
rebalance_df = pd.DataFrame({
    "Month": rebalance_points,
    "Rebalanced To 70/30": [True] * len(rebalance_points)
})

# ---- Charts ----
# Projection Chart
plt.figure(figsize=(10, 6))
plt.plot(growth_df["Month"], growth_df["Portfolio Value"], label="Portfolio Value", linewidth=2)
plt.plot(growth_df["Month"], growth_df["Total Invested"], label="Total Invested", linestyle="--")
plt.title("💰 Portfolio Growth Projection (10Y, Monthly DCA £500)")
plt.xlabel("Month")
plt.ylabel("Value (£)")
plt.legend()
plt.tight_layout()
plt.savefig("assets/playbook_projection.png", bbox_inches="tight", facecolor="white")
plt.close()

# Rebalancing View
plt.figure(figsize=(10, 5))
plt.plot(growth_df["Month"], values[:, 0] / values.sum(axis=1), label="Equity Weight")
plt.plot(growth_df["Month"], values[:, 1] / values.sum(axis=1), label="Bond Weight")
for r in rebalance_points:
    plt.axvline(r, color="gray", linestyle=":", alpha=0.5)
plt.title("⚖️ Portfolio Allocation & Rebalancing Events")
plt.xlabel("Month")
plt.ylabel("Weight")
plt.legend()
plt.tight_layout()
plt.savefig("assets/playbook_rebalance.png", bbox_inches="tight", facecolor="white")
plt.close()

# ---- Excel Export ----
with pd.ExcelWriter(OUT_XLSX, engine="xlsxwriter") as writer:
    growth_df.to_excel(writer, sheet_name="Projection", index=False)
    rebalance_df.to_excel(writer, sheet_name="Rebalance", index=False)

    wb = writer.book
    ws = writer.sheets["Projection"]
    chart = wb.add_chart({"type": "line"})
    chart.add_series({
        "name": "Portfolio Value",
        "categories": ["Projection", 1, 0, months, 0],
        "values": ["Projection", 1, 1, months, 1],
    })
    chart.add_series({
        "name": "Total Invested",
        "categories": ["Projection", 1, 0, months, 0],
        "values": ["Projection", 1, 2, months, 2],
    })
    chart.set_title({"name": "Portfolio Growth Projection"})
    chart.set_x_axis({"name": "Month"})
    chart.set_y_axis({"name": "£ Value"})
    chart.set_legend({"position": "bottom"})
    ws.insert_chart("G2", chart)

print(f"✅ Excel dashboard written to: {OUT_XLSX}")
print("🖼️ Charts saved:")
print("   - assets/playbook_projection.png")
print("   - assets/playbook_rebalance.png")
