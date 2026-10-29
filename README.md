# AI Stock Atlas: the worldwide AI industry, mapped

A curated universe of ~360 listed companies across the AI value chain in 20 countries, with live market data and a self-contained interactive map.

**Live:** https://luckeyfaraday.github.io/ai-stock-atlas/ (prices refresh hourly on weekdays via GitHub Actions).

## Views
- **Map**: Finviz-style treemap. Companies are grouped into 13 value-chain layers, sized by USD market cap and colored by return over 1D/1W/1M/YTD/1Y. "√ Market cap" sizing makes small caps visible.
- **Value chain**: the 13 layers from upstream to downstream, each with total cap, return, region split and largest names.
- **World**: bubble map and ranking of AI market cap by headquarters country.
- **New & upcoming listings**: the IPO pipeline (`data/pipeline.csv`, with sources) and every company in the universe that listed since 2025.
- **Table**: every company; sortable and filterable.
- **Method**: definitions, data notes, and known gaps.

## How it updates
`.github/workflows/deploy.yml` runs hourly on weekdays (UTC). Each run fetches prices, builds the page and deploys it to GitHub Pages. If Yahoo returns data for fewer than 90% of tickers, the run fails and the last good deploy stays up.

Run it locally:
```sh
pip install -r requirements.txt
python3 scripts/fetch_market.py   # Yahoo Finance via yfinance → data/market.json (~3 min)
python3 scripts/build_site.py     # bundles data + d3 + world atlas → site/index.html (works from file://)
```

## Files
| Path | What |
|---|---|
| `data/universe.csv` | Source of truth: ticker (Yahoo format), name, HQ country, layer, segment, AI-exposure tier (core/high/partial), note, listing month if 2025+ |
| `data/pipeline.csv` | Filed, pending or withdrawn AI IPOs, with source links |
| `data/market.json` | Generated (not committed): prices, USD market caps, returns, weekly sparklines, problems |
| `static/` | Copied into the site as-is (social preview image) |
| `scripts/template.html` | Page template (D3, no build step) |
| `vendor/` | d3 7.9.0, topojson-client 3.1.0, world-atlas 110m |

## Contributing
Missing a company, wrong layer, stale IPO status? Open an issue or PR against `data/universe.csv` / `data/pipeline.csv`.

## Notes
- Each company has one primary layer (e.g. Samsung → memory). Tiers are editorial.
- Market caps are Yahoo's quoted figures converted at spot FX. Returns are in local currency, adjusted for splits and dividends.
- Not investment advice.
