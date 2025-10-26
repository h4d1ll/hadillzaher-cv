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

# Plot — Liquidity Stress Lines
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

# ---------- Contagion Simulation ----------
banks = ["SVB", "Credit Suisse", "Deutsche", "HSBC", "JPM", "BNP", "UBS"]
np.random.seed(42)

# Create denser interbank exposures for realism
exposure = pd.DataFrame(
    np.random.uniform(0.3, 1.0, (len(banks), len(banks))), index=banks, columns=banks
)
np.fill_diagonal(exposure.values, 0)

# Parameters — tune to ensure propagation
loss_given_default = 0.7     # how much loss if a counterparty defaults
threshold = 0.3              # threshold of losses before a bank fails

def contagion_round(exposure_df, defaults, lgd, threshold):
    """Compute contagion round given defaults."""
    if not defaults:
        return pd.Series(0, index=exposure_df.index), set()
    losses = exposure_df[list(defaults)].sum(axis=1) * lgd
    new_defaults = set(exposure_df.index[losses > threshold]) - defaults
    return losses, new_defaults

defaults = {"SVB"}
all_defaults = set(defaults)
rounds = []
defaults_count = []

# Simulate up to 6 contagion rounds
for i in range(6):
    losses, new = contagion_round(exposure, defaults, loss_given_default, threshold)
    rounds.append({
        "Round": i + 1,
        "Defaults": list(defaults),
        "New Defaults": list(new),
        "Triggered Banks": len(defaults),
    })
    defaults_count.append(len(defaults))
    if not new:
        break
    defaults |= new
    all_defaults |= new

contagion_summary = pd.DataFrame(rounds)

# Plot — Contagion Propagation Line (visible curve)
plt.figure(figsize=(9, 5))
plt.plot(range(1, len(defaults_count) + 1), defaults_count,
         marker="o", linewidth=2.5, color="#ef4444")
plt.title("Systemic Contagion — Default Propagation")
plt.xlabel("Simulation Round")
plt.ylabel("Cumulative Defaults")
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

    # Liquidity Chart
    ws_liq = writer.sheets["Liquidity Stress"]
    chart1 = wb.add_chart({"type": "line"})
    for i, col in enumerate(loss_df.columns):
        chart1.add_series({
            "name":       ["Liquidity Stress", 0, i + 1],
            "categories": ["Liquidity Stress", 1, 0, len(loss_df.index), 0],
            "values":     ["Liquidity Stress", 1, i + 1, len(loss_df.index), i + 1],
        })
    chart1.set_title({"name": "Liquidity Stress — Duration Sensitivity"})
    chart1.set_x_axis({"name": "Duration (Years)"})
    chart1.set_y_axis({"name": "Price Change (%)"})
    chart1.set_legend({"position": "bottom"})
    ws_liq.insert_chart("H2", chart1)

    # Contagion Chart
    ws_con = writer.sheets["Contagion Simulation"]
    chart2 = wb.add_chart({"type": "line"})
    chart2.add_series({
        "categories": ["Contagion Simulation", 1, 0, len(contagion_summary), 0],
        "values":     ["Contagion Simulation", 1, 3, len(contagion_summary), 3],
        "name":       "Cumulative Defaults",
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
