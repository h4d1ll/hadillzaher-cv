import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- Ensure assets/ exists for chart images ---
os.makedirs("assets", exist_ok=True)

# --- Define tickers ---
fintech_tickers = ["PYPL", "ADYEY", "WISE.L"]
bank_tickers = ["JPM", "GS", "HSBC"]
tickers = fintech_tickers + bank_tickers

print("📥 Downloading 3 years of adjusted close data for fintech and banking stocks...")
data = yf.download(tickers, period="3y", auto_adjust=True, progress=True)["Close"]

# Drop any columns that are completely empty (e.g., unavailable tickers)
data = data.dropna(axis=1, how="all")

if data.empty:
    raise ValueError("No valid price data retrieved. Check tickers or internet connection.")

# --- Compute daily returns ---
returns = data.pct_change().dropna()
rf = 0.04  # annual risk-free rate assumption

# --- Annualized performance metrics ---
# (Use price start/end with trading-day scaling)
annual_return = (data.iloc[-1] / data.iloc[0]) ** (252 / len(data)) - 1
volatility = returns.std() * np.sqrt(252)
sharpe_ratio = (annual_return - rf) / np.where(volatility.eq(0), np.nan, volatility)

# --- Drawdown (from cumulative returns of daily returns) ---
cum = (1 + returns).cumprod()
roll_max = cum.cummax()
drawdown = (cum - roll_max) / roll_max
max_dd = drawdown.min()

# --- Summary metrics ---
summary = pd.DataFrame({
    "Ticker": data.columns,
    "Category": ["Fintech" if t in fintech_tickers else "Bank" for t in data.columns],
    "Annual Return (%)": (annual_return.reindex(data.columns) * 100).round(2),
    "Volatility (%)": (volatility.reindex(data.columns) * 100).round(2),
    "Sharpe Ratio": sharpe_ratio.reindex(data.columns).round(2),
    "Max Drawdown (%)": (max_dd.reindex(data.columns) * 100).round(2)
}).sort_values("Sharpe Ratio", ascending=False, na_position="last")

# --- Rolling 6-month Sharpe ratios ---
rolling_window = 126  # ~6 months of trading days
rolling_mean = returns.rolling(rolling_window).mean()
rolling_std = returns.rolling(rolling_window).std()
rolling_sharpe = ((rolling_mean * 252) - rf) / (rolling_std * np.sqrt(252))

# --- Group averages (Fintech vs Banks) ---
# Only average over columns that actually exist in 'returns'
existing_fintech = [t for t in fintech_tickers if t in returns.columns]
existing_banks   = [t for t in bank_tickers if t in returns.columns]

returns["Fintech Avg"] = returns[existing_fintech].mean(axis=1)
returns["Bank Avg"]    = returns[existing_banks].mean(axis=1)

rolling_sharpe["Fintech Avg"] = rolling_sharpe[existing_fintech].mean(axis=1)
rolling_sharpe["Bank Avg"]    = rolling_sharpe[existing_banks].mean(axis=1)

avg_metrics = summary.groupby("Category")[["Annual Return (%)", "Volatility (%)", "Sharpe Ratio"]].mean().round(2)

# --- Save to Excel ---
file = "Fintech_vs_Banks_3Y_Report.xlsx"
with pd.ExcelWriter(file, engine="xlsxwriter") as writer:
    summary.to_excel(writer, sheet_name="Summary", index=False)
    avg_metrics.to_excel(writer, sheet_name="Category Averages")
    # Normalize cumulative returns to 100 for readability in Excel too
    cum_norm = cum.copy()
    cum_norm = cum_norm / cum_norm.iloc[0] * 100
    cum_norm.to_excel(writer, sheet_name="Cumulative Returns (Idx=100)")
    rolling_sharpe.to_excel(writer, sheet_name="Rolling Sharpe")

    wb = writer.book
    ws_summary = writer.sheets["Summary"]

    fmt_head = wb.add_format({"bold": True, "bg_color": "#DDEBF7", "font_color": "#1F4E79", "border": 1})
    for col_num, value in enumerate(summary.columns.values):
        ws_summary.write(0, col_num, value, fmt_head)

    # Chart — Sharpe Ratio Comparison
    chart = wb.add_chart({"type": "column"})
    # categories = Summary!A2:A{n}, values = Summary!E2:E{n} (Sharpe Ratio column index)
    n = len(summary) + 1
    chart.add_series({
        "categories": ["Summary", 1, 0, n-1, 0],  # Ticker names
        "values":     ["Summary", 1, summary.columns.get_loc("Sharpe Ratio"), n-1, summary.columns.get_loc("Sharpe Ratio")],
        "name": "Sharpe Ratio",
        "gap": 150,
    })
    chart.set_title({"name": "Sharpe Ratios — Fintech vs Banks"})
    chart.set_y_axis({"major_gridlines": {"visible": True}})
    ws_summary.insert_chart("H2", chart)

print(f"\n✅ Excel report saved as: {file}")
print("\n🏦 Fintech vs Banks — Ticker Summary:")
print(summary.to_string(index=False))
print("\n📊 Category Averages:")
print(avg_metrics)

# ======================
# === SAVE THE FIGS ====
# ======================

# --- Plot cumulative returns (indexed to 100) ---
cum_plot = (data / data.iloc[0] * 100).dropna()
plt.figure(figsize=(11, 6))
for col in cum_plot.columns:
    plt.plot(cum_plot.index, cum_plot[col], label=col)
plt.title("Cumulative Returns — Fintech vs Banks (3 Years)")
plt.xlabel("Date"); plt.ylabel("Cumulative Return (Indexed to 100)")
plt.legend(); plt.grid(True); plt.tight_layout()
plt.savefig("assets/fintech_banks_cumulative.png", dpi=160, bbox_inches="tight")
plt.close()

# --- Plot rolling Sharpe ratios (6-month) group averages ---
rs_plot = rolling_sharpe[["Fintech Avg", "Bank Avg"]].dropna(how="all")
plt.figure(figsize=(11, 6))
if "Fintech Avg" in rs_plot.columns:
    plt.plot(rs_plot.index, rs_plot["Fintech Avg"], label="Fintech (6-month Sharpe)")
if "Bank Avg" in rs_plot.columns:
    plt.plot(rs_plot.index, rs_plot["Bank Avg"], label="Banks (6-month Sharpe)")
plt.title("Rolling 6-Month Sharpe Ratios — Fintech vs Banks")
plt.xlabel("Date"); plt.ylabel("Sharpe Ratio")
plt.legend(); plt.grid(True); plt.tight_layout()
plt.savefig("assets/rolling_sharpe.png", dpi=160, bbox_inches="tight")
plt.close()

print("\n🖼️ Saved figures:")
print(" - assets/fintech_banks_cumulative.png")
print(" - assets/rolling_sharpe.png")
