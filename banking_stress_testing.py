# banking_stress_testing.py
# 🏦 Banking Crises & Stress Testing (2024)
# SVB & Credit Suisse contagion, liquidity, and systemic risk simulation

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

os.makedirs("assets", exist_ok=True)

# ---------- Liquidity Stress Simulation ----------
durations = np.array([1, 2, 5, 10])
rate_shocks = np.linspace(-2, 2, 9)  # -2% to +2%
# Simulated price change ≈ -Duration × Δy × sensitivity factor
loss_matrix = np.outer(durations, rate_shocks) * -0.8

loss_df = pd.DataFrame(
    loss_matrix,
    index=[f"{d}Y" for d in durations],
    columns=[f"{r:+.1f}%" for r in rate_shocks],
)

# Plot — Liquidity Stress (lines)
plt.figure(figsize=(9, 5))
for i, d in enumerate(durations):
    plt.plot(rate_shocks, loss_matrix[i], label=f"{d}Y Duration", linewidth=2)
plt.axhline(0, color="gray", linestyle="--", linewidth=1)
plt.title("Liquidity Stress Simulation — Bond Value Sensitivity")
plt.xlabel("Interest Rate Shock (%)")
plt.ylabel("Portfolio Value Change (%)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("assets/stress_liquidity.png", bbox_inches="tight", facecolor="white")
plt.close()

# ---------- Contagion Simulation (reworked for visible propagation) ----------
banks = ["SVB", "Credit Suisse", "Deutsche", "HSBC", "JPM", "BNP", "UBS"]
np.random.seed(42)

# Heavier, column-normalized exposures so each bank is meaningfully exposed to others
raw = np.random.lognormal(mean= -0.1, sigma=0.5, size=(len(banks), len(banks)))
np.fill_diagonal(raw, 0.0)
# Normalize each column to a target exposure (e.g., 1.2) so "losses from a default of X" are comparable across lenders
target_col_sum = 1.2
col_sums = raw.sum(axis=0, keepdims=True)
col_sums[col_sums == 0] = 1.0
exposure = raw / col_sums * target_col_sum
exposure = pd.DataFrame(exposure, index=banks, columns=banks)

loss_given_default = 0.6   # 60% LGD
threshold = 0.5            # defaults if exposure-losses > 0.5

def contagion_round(exposure_df, defaults_set, lgd, threshold):
    """Loss to each lender from all currently defaulted borrowers."""
    if not defaults_set:
        return pd.Series(0.0, index=exposure_df.index), set()
    # Sum exposures to all names that have defaulted, then multiply by LGD
    losses = exposure_df[list(defaults_set)].sum(axis=1) * lgd
    # New defaults are those whose losses exceed threshold and are not already in default
    new_defaults = set(exposure_df.index[losses > threshold]) - defaults_set
    return losses, new_defaults

# Start with two failing institutions to kick off a cascade
defaults = {"SVB", "Credit Suisse"}
all_defaults = set(defaults)

rounds = []
cum_defaults = []

max_rounds = 8
for r in range(1, max_rounds + 1):
    losses, new = contagion_round(exposure, defaults, loss_given_default, threshold)
    rounds.append({
        "Round": r,
        "New Defaults": len(new),
        "Cumulative Defaults": len(defaults)
    })
    cum_defaults.append(len(defaults))
    if not new:
        break
    defaults |= new
    all_defaults |= new

contagion_summary = pd.DataFrame(rounds)

# Plot — Contagion Propagation (line with multiple points)
plt.figure(figsize=(9, 5))
x = contagion_summary["Round"]
y = contagion_summary["Cumulative Defaults"]
plt.plot(x, y, marker="o", linewidth=2)
plt.title("Systemic Contagion — Default Propagation")
plt.xlabel("Simulation Round")
plt.ylabel("Cumulative Defaults")
plt.xticks(x)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("assets/stress_contagion.png", bbox_inches="tight", facecolor="white")
plt.close()

# ---------- Excel Dashboard ----------
file = "Banking_Stress_Testing_2024.xlsx"
with pd.ExcelWriter(file, engine="xlsxwriter") as writer:
    loss_df.to_excel(writer, sheet_name="Liquidity Stress")
    exposure.to_excel(writer, sheet_name="Interbank Exposure")
    contagion_summary.to_excel(writer, sheet_name="Contagion Simulation", index=False)

    wb = writer.book

    # Liquidity Chart (line)
    ws_liq = writer.sheets["Liquidity Stress"]
    chart1 = wb.add_chart({"type": "line"})
    # Dates are not needed; x-axis is duration labels in column A
    for j, col in enumerate(loss_df.columns, start=1):
        chart1.add_series({
            "name":       ["Liquidity Stress", 0, j],
            "categories": ["Liquidity Stress", 1, 0, len(loss_df.index), 0],
            "values":     ["Liquidity Stress", 1, j, len(loss_df.index), j],
        })
    chart1.set_title({"name": "Liquidity Stress — Duration Sensitivity"})
    chart1.set_x_axis({"name": "Duration (Years)"})
    chart1.set_y_axis({"name": "Price Change (%)"})
    chart1.set_legend({"position": "bottom"})
    ws_liq.insert_chart("H2", chart1)

    # Contagion Chart (line of cumulative defaults)
    ws_con = writer.sheets["Contagion Simulation"]
    chart2 = wb.add_chart({"type": "line"})
    chart2.add_series({
        "name":       "Cumulative Defaults",
        "categories": ["Contagion Simulation", 1, 0, len(contagion_summary), 0],  # Round
        "values":     ["Contagion Simulation", 1, 2, len(contagion_summary), 2],  # Cumulative Defaults
        "marker":     {"type": "automatic"},
    })
    chart2.set_title({"name": "Systemic Contagion — Defaults Over Time"})
    chart2.set_x_axis({"name": "Simulation Round"})
    chart2.set_y_axis({"name": "Defaults"})
    chart2.set_legend({"position": "bottom"})
    ws_con.insert_chart("E2", chart2)

print("\n✅ Banking Stress Dashboard generated successfully!")
print("📘 Excel File:", file)
print("🖼️ Charts saved:")
print("   - assets/stress_liquidity.png")
print("   - assets/stress_contagion.png")
