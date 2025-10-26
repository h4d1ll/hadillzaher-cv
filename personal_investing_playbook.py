# -*- coding: utf-8 -*-
# 💰 Personal Investing Playbook — DCA, Rebalancing, and Excel Dashboard

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- Setup ---
os.makedirs("assets", exist_ok=True)
plt.rcParams.update({"figure.dpi": 160, "axes.grid": True})
pd.options.display.float_format = "{:,.2f}".format

OUT_XLSX = "Personal_Investing_Playbook.xlsx"
np.random.seed(42)

# --- Portfolio Parameters ---
years = 10
months = years * 12
monthly_contribution = 500
initial_weights = np.array([0.7, 0.3])  # 70% equities, 30% bonds
rebalance_threshold = 0.05

# Simulated returns (monthly)
mu = np.array([0.07, 0.03])  # annual means
sigma = np.array([0.15, 0.05])
rho = 0.2
cov = np.outer(sigma, sigma) * rho
np.fill_diagonal(cov, sigma ** 2)
returns = np.random.multivariate_normal(mu / 12, cov / np.sqrt(12), months)

# --- Simulate portfolio with DCA + rebalancing ---
values = np.zeros((months, 2))
total_portfolio = np.zeros(months)
rebalances = []

for i in range(months):
    if i == 0:
        values[i] = monthly_contribution * initial_weights
    else:
        values[i] = values[i - 1] * (1 + returns[i]) + monthly_contribution * initial_weights

    total = values[i].sum()
    total_portfolio[i] = total
    weights_now = values[i] / total

    if np.any(np.abs(weights_now - initial_weights) > rebalance_threshold):
        rebalances.append(i)
        values[i] = total * initial_weights  # rebalance

# --- Build projection table ---
total_invested = np.cumsum(np.full(months, monthly_contribution))
growth = pd.DataFrame({
    "Month": np.arange(1, months + 1),
    "Equity": values[:, 0],
    "Bond": values[:, 1],
    "Total Portfolio": total_portfolio,
    "Total Invested": total_invested,
    "Net Gain": total_portfolio - total_invested,
})
growth["Year"] = np.ceil(growth["Month"] / 12).astype(int)

# --- Summary stats ---
final_value = total_portfolio[-1]
final_invested = total_invested[-1]
total_gain = final_value - final_invested
annual_cagr = (final_value / final_invested) ** (1 / years) - 1

summary = pd.DataFrame({
    "Metric": ["Years", "Total Invested (£)", "Final Value (£)", "Net Gain (£)", "CAGR (%)"],
    "Value": [years, final_invested, final_value, total_gain, annual_cagr * 100]
})

# --- Charts ---
# Growth Projection
plt.figure(figsize=(10, 6))
plt.plot(growth["Month"], growth["Total Portfolio"], label="Portfolio Value", linewidth=2)
plt.plot(growth["Month"], growth["Total Invested"], "--", label="Total Invested")
plt.title("💰 Portfolio Growth Projection (10Y DCA £500/month)")
plt.xlabel("Month")
plt.ylabel("Value (£)")
plt.legend()
plt.tight_layout()
plt.savefig("assets/playbook_projection.png", bbox_inches="tight", facecolor="white")
plt.close()

# Allocation Drift + Rebalancing
plt.figure(figsize=(10, 5))
plt.plot(growth["Month"], values[:, 0] / total_portfolio, label="Equity Weight (70%)")
plt.plot(growth["Month"], values[:, 1] / total_portfolio, label="Bond Weight (30%)")
for r in rebalances:
    plt.axvline(r, color="gray", linestyle=":", alpha=0.5)
plt.title("⚖️ Allocation Drift and Rebalancing Points")
plt.xlabel("Month")
plt.ylabel("Portfolio Weight")
plt.legend()
plt.tight_layout()
plt.savefig("assets/playbook_rebalance.png", bbox_inches="tight", facecolor="white")
plt.close()

# --- Excel Dashboard ---
with pd.ExcelWriter(OUT_XLSX, engine="xlsxwriter") as writer:
    growth.to_excel(writer, sheet_name="Projection", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

    wb = writer.book

    # Styling
    fmt_head = wb.add_format({"bold": True, "bg_color": "#DDEBF7", "border": 1, "font_color": "#1F4E79"})
    ws_sum = writer.sheets["Summary"]
    for i, col in enumerate(summary.columns):
        ws_sum.write(0, i, col, fmt_head)
        ws_sum.set_column(i, i, 22)

    # Chart in Excel
    ws_proj = writer.sheets["Projection"]
    chart = wb.add_chart({"type": "line"})
    chart.add_series({
        "name": "Portfolio Value",
        "categories": ["Projection", 1, 0, months, 0],
        "values": ["Projection", 1, 3, months, 3],
    })
    chart.add_series({
        "name": "Total Invested",
        "categories": ["Projection", 1, 0, months, 0],
        "values": ["Projection", 1, 4, months, 4],
    })
    chart.set_title({"name": "Portfolio Growth Projection"})
    chart.set_x_axis({"name": "Month"})
    chart.set_y_axis({"name": "£ Value"})
    chart.set_legend({"position": "bottom"})
    ws_proj.insert_chart("H2", chart)

print(f"✅ Excel dashboard written to: {OUT_XLSX}")
print("🖼️ Charts saved:")
print("   - assets/playbook_projection.png")
print("   - assets/playbook_rebalance.png")
