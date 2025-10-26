# -*- coding: utf-8 -*-
# fintech_pe_dashboard.py
# Fintech P/E Dashboard — with robust fallbacks (EPS from income stmt, else P/S proxy)

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# ---------- Setup ----------
os.makedirs("assets", exist_ok=True)
plt.rcParams.update({"figure.dpi": 160, "axes.grid": True})
pd.options.display.float_format = "{:,.2f}".format

TICKERS = ["PYPL", "SHOP", "WISE.L", "ADYEN.AS"]  # your set
YEARS_OF_PRICE = 3
OUT_XLSX = "Fintech_PE_Dashboard.xlsx"

print(f"📥 Downloading {YEARS_OF_PRICE} years of Adjusted Close prices...")
px = yf.download(TICKERS, period=f"{YEARS_OF_PRICE}y", auto_adjust=True)["Close"]
if isinstance(px, pd.Series):
    px = px.to_frame()
px = px.dropna(axis=1, how="all").ffill().bfill()

missing = [t for t in TICKERS if t not in px.columns]
if missing:
    print(f"⚠️ Dropped tickers (no price data): {', '.join(missing)}")
if px.empty:
    raise SystemExit("❌ No valid price series after cleaning.")

# ---------- Helper: EPS from yfinance earnings_dates ----------
def get_ttm_eps_from_earnings_dates(ticker: str) -> pd.DataFrame:
    """
    Tries yfinance's get_earnings_dates (needs lxml) -> 'EPS Actual'.
    Returns DataFrame index as DatetimeIndex, cols ['eps_actual','ttm_eps'].
    """
    try:
        t = yf.Ticker(ticker)
        ed = t.get_earnings_dates(limit=12)
        if ed is None or ed.empty:
            return pd.DataFrame()
        col = "EPS Actual" if "EPS Actual" in ed.columns else ("Earnings" if "Earnings" in ed.columns else None)
        if col is None:
            return pd.DataFrame()
        df = pd.DataFrame(
            {"eps_actual": pd.to_numeric(ed[col], errors="coerce")},
            index=pd.to_datetime(ed.index).tz_localize(None)
        ).sort_index()
        df["ttm_eps"] = df["eps_actual"].rolling(4).sum()
        df = df.dropna(subset=["ttm_eps"])
        return df
    except Exception as e:
        print(f"ℹ️ earnings_dates EPS unavailable for {ticker}: {e}")
        return pd.DataFrame()

# ---------- Helper: EPS/P/S from income statement (quarterly) ----------
def safe_get_income_stmt_quarterly(ticker: str) -> pd.DataFrame:
    """
    Uses new yfinance API (0.2.x): get_income_stmt(freq='quarterly').
    Returns a tidy DataFrame with DatetimeIndex, cols include:
      netincome, dilutedaverageShares (or basicAverageShares), totalrevenue
    """
    try:
        t = yf.Ticker(ticker)
        df = t.get_income_stmt(freq="quarterly")
        if df is None or df.empty:
            return pd.DataFrame()
        # yfinance returns items as rows, dates as columns; transpose to tidy
        df = df.T
        df.index = pd.to_datetime(df.index).tz_localize(None)

        # Best-effort column normalization
        def pick(*names):
            for n in names:
                if n in df.columns:
                    return n
            return None

        ni_col  = pick("NetIncome", "netIncome", "netincome", "Net Income", "net income")
        rev_col = pick("TotalRevenue", "totalRevenue", "totalrevenue", "Revenue", "revenue", "Total Revenue")
        dil_col = pick("DilutedAverageShares", "dilutedAverageShares", "weightedAverageShDiluted",
                       "WeightedAverageShDiluted", "weightedAverageSharesDiluted")
        bas_col = pick("BasicAverageShares", "basicAverageShares", "weightedAverageShBasic",
                       "WeightedAverageShBasic", "weightedAverageSharesBasic")

        out = pd.DataFrame(index=df.index)
        if ni_col is not None:
            out["net_income"] = pd.to_numeric(df[ni_col], errors="coerce")
        if rev_col is not None:
            out["revenue"] = pd.to_numeric(df[rev_col], errors="coerce")

        shares_series = None
        if dil_col is not None:
            shares_series = pd.to_numeric(df[dil_col], errors="coerce")
        elif bas_col is not None:
            shares_series = pd.to_numeric(df[bas_col], errors="coerce")
        if shares_series is not None:
            out["shares"] = shares_series

        return out.dropna(how="all")
    except Exception as e:
        print(f"ℹ️ income_stmt unavailable for {ticker}: {e}")
        return pd.DataFrame()

def build_ttm_eps_and_ps(ticker: str):
    """
    Returns two DataFrames, both indexed by quarter end:
      - eps_ttm_df: columns ['ttm_eps']  (from earnings_dates OR income stmt)
      - ps_ttm_df:  columns ['ttm_rev_per_sh'] (for P/S proxy)
    """
    # First try earnings_dates
    ed = get_ttm_eps_from_earnings_dates(ticker)
    eps_ttm_df = pd.DataFrame()
    if not ed.empty:
        eps_ttm_df = ed[["ttm_eps"]].copy()

    # Income statement fallback (for EPS and P/S)
    inc = safe_get_income_stmt_quarterly(ticker)
    ps_ttm_df = pd.DataFrame()
    if not inc.empty:
        # EPS from income_stmt if needed
        if eps_ttm_df.empty and {"net_income", "shares"}.issubset(inc.columns):
            eps_q = inc["net_income"] / inc["shares"]
            eps_ttm = eps_q.rolling(4).sum()
            eps_ttm_df = pd.DataFrame({"ttm_eps": eps_ttm.dropna()})

        # P/S proxy (revenue per share, trailing 4Q)
        if {"revenue", "shares"}.issubset(inc.columns):
            rps_q = inc["revenue"] / inc["shares"]
            rps_ttm = rps_q.rolling(4).sum()
            ps_ttm_df = pd.DataFrame({"ttm_rev_per_sh": rps_ttm.dropna()})

    return eps_ttm_df, ps_ttm_df

# ---------- Build P/E points (with proxy if needed) ----------
pe_points = []
proxy_points = []
for tk in px.columns:
    eps_ttm_df, ps_ttm_df = build_ttm_eps_and_ps(tk)

    # P/E from EPS if available
    if not eps_ttm_df.empty:
        for dt, row in eps_ttm_df.iterrows():
            price_series = px[tk].loc[:dt].dropna()
            if price_series.empty:
                continue
            price = float(price_series.iloc[-1])
            ttm_eps = float(row["ttm_eps"])
            if ttm_eps and np.isfinite(ttm_eps):
                pe = price / ttm_eps if ttm_eps != 0 else np.nan
                pe_points.append({"Ticker": tk, "Date": dt.date(), "Value": pe, "Metric": "P/E"})

    # P/S proxy if revenue/share available
    if not ps_ttm_df.empty:
        for dt, row in ps_ttm_df.iterrows():
            price_series = px[tk].loc[:dt].dropna()
            if price_series.empty:
                continue
            price = float(price_series.iloc[-1])
            rps_ttm = float(row["ttm_rev_per_sh"])
            if rps_ttm and np.isfinite(rps_ttm):
                ps = price / rps_ttm if rps_ttm != 0 else np.nan
                proxy_points.append({"Ticker": tk, "Date": dt.date(), "Value": ps, "Metric": "P/S (proxy)"})

pe_df = pd.DataFrame(pe_points)
proxy_df = pd.DataFrame(proxy_points)

# ---------- Summary (latest) ----------
def latest_valid(series: pd.Series):
    s = series.dropna()
    return s.iloc[-1] if not s.empty else np.nan

latest_px = px.apply(latest_valid, axis=0)

summary_rows = []
for tk in px.columns:
    price = latest_px.get(tk, np.nan)

    # Latest P/E
    last_pe = np.nan
    if not pe_df.empty:
        s = pe_df[(pe_df["Ticker"] == tk)]["Value"]
        if not s.empty:
            last_pe = s.iloc[-1]

    # 1Y perf
    s_px = px[tk].dropna()
    perf_1y = ((s_px.iloc[-1] / s_px.iloc[-252]) - 1) * 100 if len(s_px) >= 252 else np.nan

    summary_rows.append({"Ticker": tk, "Last Price": price, "Current P/E": last_pe, "1Y Return (%)": perf_1y})

summary = pd.DataFrame(summary_rows)

# ---------- Charts ----------
# Normalized price
norm = (px / px.iloc[0]) * 100.0
plt.figure(figsize=(11, 6))
for tk in norm.columns:
    plt.plot(norm.index, norm[tk], label=tk, linewidth=2)
plt.title("Fintech Price Performance — Indexed to 100")
plt.ylabel("Index (Start = 100)")
plt.xlabel("Date")
plt.legend(ncols=2, fontsize=8, loc="upper left")
plt.tight_layout()
plt.savefig("assets/fintech_prices_normalized.png", bbox_inches="tight", facecolor="white")
plt.close()

# Quarterly valuation chart: P/E if present, else P/S proxy (dashed)
have_any_lines = False
plt.figure(figsize=(11, 6))

# Plot P/E solid
if not pe_df.empty:
    for tk in pe_df["Ticker"].unique():
        sub = pe_df[pe_df["Ticker"] == tk].sort_values("Date")
        if not sub.empty:
            have_any_lines = True
            plt.plot(pd.to_datetime(sub["Date"]), sub["Value"], marker="o", linewidth=1.8, label=f"{tk} P/E")

# Plot P/S proxy dashed for tickers lacking P/E
if not proxy_df.empty:
    for tk in proxy_df["Ticker"].unique():
        had_pe = False
        if not pe_df.empty:
            had_pe = (pe_df["Ticker"] == tk).any()
        if not had_pe:
            sub = proxy_df[proxy_df["Ticker"] == tk].sort_values("Date")
            if not sub.empty:
                have_any_lines = True
                plt.plot(pd.to_datetime(sub["Date"]), sub["Value"], marker="o", linewidth=1.8, linestyle="--", label=f"{tk} P/S (proxy)")

plt.title("Fintech Valuation — Quarterly (P/E; dashed = P/S proxy)")
plt.ylabel("Multiple")
plt.xlabel("Earnings Date")
if have_any_lines:
    plt.legend(ncols=2, fontsize=8)
plt.tight_layout()
plt.savefig("assets/fintech_pe_quarterly.png", bbox_inches="tight", facecolor="white")
plt.close()

if not have_any_lines:
    print("ℹ️ Still no quarterly valuation lines (EPS and revenue/share both unavailable).")
    print("   Consider adding more US-listed tickers with richer fundamentals (e.g., INTU, V, MA, SQ, AFRM).")

# ---------- Excel dashboard ----------
with pd.ExcelWriter(OUT_XLSX, engine="xlsxwriter") as writer:
    px.to_excel(writer, sheet_name="Prices")
    norm.reset_index(names=["Date"]).to_excel(writer, sheet_name="Prices_Normalized", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

    # Long tables
    if not pe_df.empty:
        pe_df.sort_values(["Date", "Ticker"]).to_excel(writer, sheet_name="PE_Quarterly", index=False)
    if not proxy_df.empty:
        proxy_df.sort_values(["Date", "Ticker"]).to_excel(writer, sheet_name="PS_Quarterly", index=False)

    # Wide tables for charting in Excel
    pe_wide = None
    ps_wide = None
    if not pe_df.empty:
        pe_wide = pe_df.pivot(index="Date", columns="Ticker", values="Value").reset_index()
        pe_wide.to_excel(writer, sheet_name="PE_Wide", index=False)
    if not proxy_df.empty:
        ps_wide = proxy_df.pivot(index="Date", columns="Ticker", values="Value").reset_index()
        ps_wide.to_excel(writer, sheet_name="PS_Wide", index=False)

    wb = writer.book

    # Style Summary
    ws_sum = writer.sheets["Summary"]
    head = wb.add_format({"bold": True, "bg_color": "#DDEBF7", "font_color": "#1F4E79", "border": 1})
    for i, col in enumerate(summary.columns):
        ws_sum.write(0, i, col, head)
        ws_sum.set_column(i, i, 16)

    # Excel line chart for normalized prices
    ws_norm = writer.sheets["Prices_Normalized"]
    chart1 = wb.add_chart({"type": "line"})
    categories = ["Prices_Normalized", 1, 0, len(norm) + 1, 0]  # Date
    for j, tk in enumerate(norm.columns, start=1):
        chart1.add_series({
            "name":       ["Prices_Normalized", 0, j],
            "categories": categories,
            "values":     ["Prices_Normalized", 1, j, len(norm) + 1, j],
        })
    chart1.set_title({"name": "Fintech Prices (Indexed to 100)"})
    chart1.set_x_axis({"name": "Date"})
    chart1.set_y_axis({"name": "Index"})
    chart1.set_legend({"position": "bottom"})
    ws_norm.insert_chart("H2", chart1)

    # Excel chart for PE (if available) — use in-memory pe_wide for dimensions
    if pe_wide is not None and not pe_wide.empty:
        ws = writer.sheets["PE_Wide"]
        chart2 = wb.add_chart({"type": "line"})
        cat = ["PE_Wide", 1, 0, len(pe_wide), 0]
        for j in range(1, pe_wide.shape[1]):
            chart2.add_series({
                "name":       ["PE_Wide", 0, j],
                "categories": cat,
                "values":     ["PE_Wide", 1, j, len(pe_wide), j],
            })
        chart2.set_title({"name": "Fintech P/E — Quarterly"})
        chart2.set_x_axis({"name": "Earnings Date"})
        chart2.set_y_axis({"name": "P/E"})
        chart2.set_legend({"position": "bottom"})
        ws.insert_chart("H2", chart2)

    # Excel chart for PS proxy (if available) — use in-memory ps_wide
    if ps_wide is not None and not ps_wide.empty:
        ws = writer.sheets["PS_Wide"]
        chart3 = wb.add_chart({"type": "line"})
        cat = ["PS_Wide", 1, 0, len(ps_wide), 0]
        for j in range(1, ps_wide.shape[1]):
            chart3.add_series({
                "name":       ["PS_Wide", 0, j],
                "categories": cat,
                "values":     ["PS_Wide", 1, j, len(ps_wide), j],
            })
        chart3.set_title({"name": "Fintech P/S (Proxy) — Quarterly"})
        chart3.set_x_axis({"name": "Earnings Date"})
        chart3.set_y_axis({"name": "P/S"})
        chart3.set_legend({"position": "bottom"})
        ws.insert_chart("H2", chart3)

print(f"✅ Dashboard written to: {OUT_XLSX}")
print("🖼️ Charts saved:")
print("   - assets/fintech_prices_normalized.png")
print("   - assets/fintech_pe_quarterly.png")
