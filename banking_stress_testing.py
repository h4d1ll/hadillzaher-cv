# banking_stress_testing.py
# 🏦 Banking Crises & Stress Testing (2024)
# SVB & Credit Suisse contagion, liquidity, and systemic risk simulation

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

os.makedirs("assets", exist_ok=True)

# ---------- Liquidity Stress Test ----------
durations = np.array([1, 2, 5, 10])
rate_shocks = np.linspace(0, 3, 7)  # 0% to 3%

# Price change ≈ -Duration × Δy
loss_matrix = np.outer(durations, rate_shocks) * -1
loss_df = pd.DataFrame(
    loss_matrix,
    index=[f"{d}Y" for d in durations],
    columns=[f"{r:.1f}%" for r in rate_shocks],
)

# Save PNG for website modal
plt.figure(figsize=(7, 5))
plt.imshow(loss_df, cmap="Reds", aspect="auto")
plt.title("Liquidity Stress Test — Bond Loss Sensitivity")
plt.xlabel("Rate Shock (%)")
plt.ylabel("Duration (Years)")
plt.colorbar(label="Price Change (%)")
plt.tight_layout()
plt.savefig("assets/stress_liquidity.png", bbox_inches="tight", facecolor="white")
plt.close()

# ---------- Contagion Simulation ----------
banks = ["SVB", "Credit Suisse", "Deutsche", "HSBC", "JPM", "BNP", "UBS"]
np.random.seed(42)
exposure = pd.DataFrame(
    np.random.uniform(0, 1, (len(banks), len(banks))), index=banks, columns=banks
)
np.fill_diagonal(exposure.values, 0)

loss_given_default = 0.5
threshold = 8.0

def contagion_round(exposure_df, defaults, lgd, threshold):
    losses = exposure_df[list(defaults)].sum(axis=1) * lgd
    new_defaults = set(exposure_df.index[losses > threshold]) - defaults
    return losses, new_defaults

defaults = {"SVB"}
all_defaults = set(defaults)
rounds = []

for i in range(6):
    losses, new = contagion_round(exposure, defaults, loss_given_default, threshold)
    rounds.append({"Round": i + 1, "Defaults": list(defaults), "New Defaults": list(new)})
    if not new:
        break
    defaults |= new
    all_defaults |= new

contagion_summary = pd.DataFrame(rounds)

# Save PNG for website modal
plt.figure(figsize=(7, 5))
plt.bar(contagion_summary["Round"], contagion_summary["Defaults"].apply(len), color="indianred")
plt.title("Systemic Contagion Simulation — Default Spread Over Rounds")
plt.xlabel("Simulation Round")
plt.ylabel("Cumulative Defaults")
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

    # Liquidity Chart (Line)
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

    # Contagion Chart (Column)
    ws_con = writer.sheets["Contagion Simulation"]
    chart2 = wb.add_chart({"type": "column"})
    chart2.add_series({
        "categories": ["Contagion Simulation", 1, 0, len(contagion_summary), 0],
        "values":     ["Contagion Simulation", 1, 1, len(contagion_summary), 1],
        "name":       "Defaults per Round",
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
