# financial_analysis.py
# Robust fintech vs banks analysis with clean charts & Excel

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Optional but nice for heatmap:
try:
    import seaborn as sns
    SEABORN_OK = True
except Exception:
    SEABORN_OK = False

import yfinance as yf

# ---------- Setup ----------
os.makedirs("assets", exist_ok=True)
plt.rcParams.update({"figure.dpi": 160, "axes.grid": True})

# Use reliable tickers
fintech_tickers = ["PYPL", "SQ", "WISE.L", "ADYEY"]   # PayPal, Block, Wise (London), Adyen ADR
bank_tickers    = ["JPM", "GS", "HSBA.L"]             # JPMorgan, Goldman, HSBC (London)
tickers = fintech_tickers + bank_tickers

print("📥 Downloading 3 years of adjusted close data...")
raw = yf.download(tickers, period="3y", auto_adjust=True)["Close"]

# Drop tickers that are mostly missing, then fill small gaps
min_presence = 0.80  # keep columns with >= 80% non-NaN
keep_cols = [c for c in raw.columns if raw[c].notna().mean() >= min_presence]
data = raw[keep_cols].copy()

# Forward/backward fill remaining gaps (weekends/holidays mismatch)
data = data.ffill().bfill()

# Align to the FIRST date where all remaining columns are non-null
common = data.dropna().index.min()
if common is None:
    raise ValueError("All series are too sparse; try different tickers.")
data = data.loc[common:].copy()

# If less than ~6 months of data survive, warn
if len(data) < 130:
    print("⚠️ Very short common history; charts may be less informative.")

# ---------- Returns & Metrics ----------
returns = data.pct_change().dropna()

# Annualized stats
rf_annual = 0.04
ann_return = (data.iloc[-1] / data.iloc[0]) ** (252 / len(data)) - 1
ann_vol    = returns.std() * np.sqrt(252)
sharpe     = (returns.mean() * 252 - rf_annual) / (returns.std() * np.sqrt(252))

# Drawdown
cum = (1 + returns).cumprod()
roll_max = cum.cummax()
drawdown = (cum - roll_max) / roll_max
max_dd   = drawdown.min()

summary = pd.DataFrame({
    "Ticker": ann_return.index,
    "Category": ["Fintech" if t in fintech_tickers else "Bank" for t in ann_return.index],
    "Annual Return (%)": (ann_return * 100).round(2),
    "Volatility (%)":    (ann_vol    * 100).round(2),
    "Sharpe Ratio":      sharpe.round(2),
    "Max Drawdown (%)":  (max_dd     * 100).round(2),
}).sort_values(["Category", "Sharpe Ratio"], ascending=[True, False])

# Rolling 6-month Sharpe (robustly computed)
window = 126
rolling_mean = returns.rolling(window).mean()
rolling_std  = returns.rolling(window).std()
rolling_sharpe = (rolling_mean * 252 - rf_annual) / (rolling_std * np.sqrt(252))
rolling_sharpe = rolling_sharpe.replace([np.inf, -np.inf], np.nan).dropna(how="all")

# Group averages
returns["Fintech Avg"] = returns[[c for c in returns.columns if c in fintech_tickers and c in data.columns]].mean(axis=1)
returns["Bank Avg"]    = returns[[c for c in returns.columns if c in bank_tickers and c in data.columns]].mean(axis=1)
rolling_sharpe["Fintech Avg"] = rolling_sharpe[[c for c in rolling_sharpe.columns if c in fintech_tickers and c in data.columns]].mean(axis=1)
rolling_sharpe["Bank Avg"]    = rolling_sharpe[[c for c in rolling_sharpe.columns if c in bank_tickers and c in data.columns]].mean(axis=1)

avg_metrics = (
    summary.groupby("Category")[["Annual Return (%)", "Volatility (%)", "Sharpe Ratio"]]
    .mean().round(2)
)

# ---------- Charts ----------

# --- CUMULATIVE RETURNS (%), robust + visible ---
cum_pct = (cum / cum.iloc[0]) - 1.0
cum_pct = cum_pct.replace([np.inf, -np.inf], np.nan).dropna(how="all")
valid_cols = [c for c in cum_pct.columns if cum_pct[c].dropna().shape[0] >= 2]
cum_pct = cum_pct[valid_cols]

plt.figure(figsize=(11, 6))
ax = plt.gca()
ax.set_facecolor("white")
for col in cum_pct.columns:
    y = cum_pct[col] * 100.0
    if y.dropna().shape[0] >= 2:
        plt.plot(cum_pct.index, y, label=col, linewidth=2)
plt.title("Cumulative Returns — Fintech vs Banks (3 Years)")
plt.xlabel("Date"); plt.ylabel("Cumulative Return (%)")
plt.legend(loc="upper left", ncols=2, fontsize=8)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("assets/fintech_banks_cumulative.png", bbox_inches="tight", facecolor="white")
plt.close()

# --- ROLLING SHARPE (6M), robust + visible ---
plt.figure(figsize=(11, 6))
ax = plt.gca()
ax.set_facecolor("white")
if "Fintech Avg" in rolling_sharpe.columns and rolling_sharpe["Fintech Avg"].dropna().shape[0] >= 2:
    plt.plot(rolling_sharpe.index, rolling_sharpe["Fintech Avg"], label="Fintech (6M Sharpe)", linewidth=2)
if "Bank Avg" in rolling_sharpe.columns and rolling_sharpe["Bank Avg"].dropna().shape[0] >= 2:
    plt.plot(rolling_sharpe.index, rolling_sharpe["Bank Avg"], label="Banks (6M Sharpe)", linewidth=2)
plt.title("Rolling 6-Month Sharpe Ratios — Fintech vs Banks")
plt.xlabel("Date"); plt.ylabel("Sharpe Ratio")
plt.legend(loc="best"); plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("assets/rolling_sharpe.png", bbox_inches="tight", facecolor="white")
plt.close()

# --- CORRELATION HEATMAP ---
corr = returns.corr()
plt.figure(figsize=(8, 6))
if SEABORN_OK:
    sns.heatmap(corr, annot=True, cmap="coolwarm", center=0, fmt=".2f")
else:
    plt.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    plt.colorbar()
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=90)
    plt.yticks(range(len(corr.index)), corr.index)
    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            plt.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", color="black")
plt.title("Correlation Heatmap — Fintech & Banks (3 Years)")
plt.tight_layout()
plt.savefig("assets/correlation_heatmap.png", bbox_inches="tight", facecolor="white")
plt.close()

# ---------- Excel Report ----------

# Cleaned data for Excel export
cum_pct_excel = cum_pct.copy() * 100.0
rolling_excel = rolling_sharpe[["Fintech Avg", "Bank Avg"]].dropna(how="all")

file = "Fintech_vs_Banks_3Y_Report.xlsx"
with pd.ExcelWriter(file, engine="xlsxwriter") as writer:
    summary.to_excel(writer, sheet_name="Summary", index=False)
    avg_metrics.to_excel(writer, sheet_name="Category Averages")
    cum_pct_excel.to_excel(writer, sheet_name="Cumulative Returns (%)")
    rolling_excel.to_excel(writer, sheet_name="Rolling Sharpe (6M)")
    corr.to_excel(writer, sheet_name="Correlation Heatmap")

    wb = writer.book
    ws_sum = writer.sheets["Summary"]

    # Header styling
    fmt_head = wb.add_format({"bold": True, "bg_color": "#DDEBF7", "font_color": "#1F4E79", "border": 1})
    for col_num, value in enumerate(summary.columns):
        ws_sum.write(0, col_num, value, fmt_head)

    # Accurate Sharpe Ratio bar chart
    nrows = len(summary)
    if nrows > 0:
        chart = wb.add_chart({"type": "column"})
        chart.add_series({
            "name": "Sharpe Ratio",
            "categories": ["Summary", 1, 0, nrows, 0],
            "values":     ["Summary", 1, 3, nrows, 3],
        })
        chart.set_title({"name": "Sharpe Ratios — Fintech vs Banks"})
        chart.set_x_axis({"name": "Ticker"})
        chart.set_y_axis({"name": "Sharpe"})
        chart.set_legend({"position": "bottom"})
        ws_sum.insert_chart("H2", chart)

print("\n✅ Charts saved to assets/ and Excel report written.")
print("   - assets/fintech_banks_cumulative.png")
print("   - assets/rolling_sharpe.png")
print("   - assets/correlation_heatmap.png")
print(f"   - {file}\n")

print("🏦 Summary:")
print(summary.to_string(index=False))
print("\n📊 Category Averages:")
print(avg_metrics.to_string())
