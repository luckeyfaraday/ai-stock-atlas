#!/usr/bin/env python3
"""Pull live market data for every ticker in data/universe.csv.

Writes data/market.json: per-ticker price, market cap (local + USD), returns
(1D/1W/1M/YTD/1Y) and a weekly sparkline, plus a problems list for tickers
that came back empty or stale. Source: Yahoo Finance via yfinance.
"""
import csv
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "data" / "universe.csv"
OUT = ROOT / "data" / "market.json"
STALE_DAYS = 7


def load_universe():
    with open(UNIVERSE, newline="") as f:
        rows = list(csv.DictReader(f))
    seen = set()
    for r in rows:
        if r["ticker"] in seen:
            sys.exit(f"duplicate ticker in universe: {r['ticker']}")
        seen.add(r["ticker"])
    return rows


def quote_info(ticker):
    """Market cap + currency. Yahoo's quoted marketCap first, fast_info as fallback."""
    t = yf.Ticker(ticker)
    out = {"currency": None, "mcap": None, "name": None, "exchange": None}
    for attempt in range(3):
        try:
            info = t.info or {}
            out.update(
                currency=info.get("currency"),
                mcap=info.get("marketCap"),
                name=info.get("longName") or info.get("shortName"),
                exchange=info.get("fullExchangeName") or info.get("exchange"),
            )
            break
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    if not out["mcap"] or not out["currency"]:
        try:
            fi = t.fast_info
            out["currency"] = out["currency"] or fi.get("currency")
            out["mcap"] = out["mcap"] or fi.get("marketCap")
        except Exception:
            pass
    return ticker, out


def pct(a, b):
    if a is None or b is None or not b or math.isnan(a) or math.isnan(b):
        return None
    return round((a / b - 1) * 100, 2)


def close_on_or_before(series, when):
    s = series[series.index <= when]
    return float(s.iloc[-1]) if len(s) else None


def main():
    rows = load_universe()
    tickers = [r["ticker"] for r in rows]
    now = datetime.now(timezone.utc)
    print(f"{len(tickers)} tickers")

    with ThreadPoolExecutor(max_workers=8) as ex:
        quotes = dict(ex.map(quote_info, tickers))
    print("quotes done")

    start = (now - timedelta(days=400)).strftime("%Y-%m-%d")
    hist = yf.download(tickers, start=start, interval="1d", auto_adjust=True,
                       progress=False, threads=True, group_by="column")["Close"]
    hist.index = pd.to_datetime(hist.index).tz_localize(None)
    print("history done")

    currencies = sorted({q["currency"] for q in quotes.values() if q["currency"]} - {"USD"})
    fx = {"USD": 1.0}
    for cur in currencies:
        # Yahoo quotes minor units for some markets (GBp, ZAc, ILA) — normalise.
        base, scale = {"GBp": ("GBP", 0.01), "ZAc": ("ZAR", 0.01), "ILA": ("ILS", 0.01)}.get(cur, (cur, 1.0))
        rate = yf.Ticker(f"{base}USD=X").fast_info.get("lastPrice")
        if not rate:
            sys.exit(f"no FX rate for {cur}")
        fx[cur] = rate * scale
    print("fx", {k: round(v, 6) for k, v in fx.items()})

    today = pd.Timestamp(now.date())
    ytd_base = pd.Timestamp(year=today.year - 1, month=12, day=31)
    out, problems = {}, []
    for ticker in tickers:
        q = quotes[ticker]
        s = hist[ticker].dropna() if ticker in hist else pd.Series(dtype=float)
        if s.empty or not q["mcap"] or not q["currency"]:
            problems.append({"ticker": ticker, "issue": "no data", "quote": q, "bars": len(s)})
            continue
        last_date = s.index[-1]
        last = float(s.iloc[-1])
        if (today - last_date).days > STALE_DAYS:
            problems.append({"ticker": ticker, "issue": f"stale: last bar {last_date.date()}"})
        prev = float(s.iloc[-2]) if len(s) > 1 else None
        weekly = s.resample("W-FRI").last().dropna().iloc[-53:]
        first_date = s.index[0]
        out[ticker] = {
            "price": round(last, 4),
            "currency": q["currency"],
            "mcap_local": q["mcap"],
            "mcap_usd": round(q["mcap"] * fx[q["currency"]]),
            "yahoo_name": q["name"],
            "exchange": q["exchange"],
            "last_bar": str(last_date.date()),
            "listed_since": str(first_date.date()) if (first_date - pd.Timestamp(start)).days > 10 else None,
            "ret": {
                "1d": pct(last, prev),
                "1w": pct(last, close_on_or_before(s, last_date - pd.Timedelta(days=7))),
                "1m": pct(last, close_on_or_before(s, last_date - pd.DateOffset(months=1))),
                "ytd": pct(last, close_on_or_before(s, ytd_base)),
                "1y": pct(last, close_on_or_before(s, last_date - pd.DateOffset(years=1))),
                "ipo": pct(last, float(s.iloc[0])) if (first_date - pd.Timestamp(start)).days > 10 else None,
            },
            "spark": [round(float(v), 4) for v in weekly.values],
        }

    ok_share = len(out) / len(tickers)
    if ok_share < 0.9:  # Yahoo throttled or broken: fail so CI keeps the last good deploy
        sys.exit(f"only {len(out)}/{len(tickers)} tickers returned data; refusing to publish")
    OUT.write_text(json.dumps({
        "asof": now.strftime("%Y-%m-%dT%H:%MZ"),
        "source": "Yahoo Finance via yfinance",
        "fx_to_usd": fx,
        "quotes": out,
        "problems": problems,
    }, indent=1))
    total = sum(v["mcap_usd"] for v in out.values())
    print(f"wrote {OUT} — {len(out)} ok, {len(problems)} problems, total ${total/1e12:.2f}T")
    for p in problems:
        print("  PROBLEM", p["ticker"], p["issue"])


if __name__ == "__main__":
    main()
