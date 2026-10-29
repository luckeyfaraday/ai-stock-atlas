#!/usr/bin/env python3
"""Bundle universe + live market data into one self-contained site/index.html."""
import csv
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VENDOR = ROOT / "vendor"
TEMPLATE = ROOT / "scripts" / "template.html"
OUT = ROOT / "site" / "index.html"

LAYERS = [
    ("equip", "Equipment, EDA & materials", "Tools, design software and materials every chip starts from"),
    ("foundry", "Foundry & packaging", "Wafer manufacturing, CoWoS-style packaging, substrates and test"),
    ("compute", "Compute silicon", "GPUs, accelerators, custom ASICs, CPUs and edge AI chips"),
    ("memory", "Memory & storage", "HBM, DRAM, NAND, drives and storage systems"),
    ("network", "Networking & optics", "Switches, optical modules, interconnect chips, cables and PCBs"),
    ("systems", "Servers & hardware", "AI server ODMs/OEMs, rack integration and thermal parts"),
    ("power", "Power, cooling & build-out", "Electrical gear, cooling, power semis, generation and construction"),
    ("datacenter", "Data centers & GPU clouds", "Neoclouds, AI hosting campuses and data-center operators"),
    ("hyperscale", "Hyperscalers & frontier labs", "Cloud giants and the listed owners of frontier models"),
    ("models", "AI platforms & models", "Listed AI-native platforms, model labs, training data and AI-bio"),
    ("software", "Software & services", "Enterprise software and IT services monetising AI"),
    ("robotics", "Robotics & autonomy", "Self-driving, humanoids, industrial robots and their parts"),
    ("devices", "Devices & edge", "Phones, PCs and wearables running AI on-device"),
]

# Short tile labels for non-US listings whose tickers are numeric or cryptic.
SHORT = {
    "2330.TW": "TSMC", "000660.KS": "SK hynix", "005930.KS": "Samsung", "8035.T": "Tokyo Electron",
    "6857.T": "Advantest", "0700.HK": "Tencent", "2317.TW": "Foxconn", "601138.SS": "FII",
    "2382.TW": "Quanta", "2454.TW": "MediaTek", "9984.T": "SoftBank", "SU.PA": "Schneider",
    "ENR.DE": "Siemens Energy", "SIE.DE": "Siemens", "SAP.DE": "SAP", "IFX.DE": "Infineon",
    "ABBN.SW": "ABB", "300308.SZ": "Innolight", "300502.SZ": "Eoptolink", "688256.SS": "Cambricon",
    "688041.SS": "Hygon", "0981.HK": "SMIC", "2308.TW": "Delta", "6669.TW": "Wiwynn",
    "1810.HK": "Xiaomi", "285A.T": "Kioxia", "5803.T": "Fujikura", "3711.TW": "ASE",
    "4063.T": "Shin-Etsu", "6501.T": "Hitachi", "7011.T": "MHI", "002230.SZ": "iFlytek",
    "0020.HK": "SenseTime", "035420.KS": "NAVER", "3661.TW": "Alchip", "3443.TW": "GUC",
    "042700.KS": "Hanmi", "267260.KS": "HD Hyundai Elec", "010120.KS": "LS Electric",
    "298040.KS": "Hyosung Heavy", "2345.TW": "Accton", "3231.TW": "Wistron", "2356.TW": "Inventec",
    "2376.TW": "Gigabyte", "3017.TW": "AVC", "2383.TW": "EMC", "2368.TW": "Gold Circuit",
    "002463.SZ": "WUS PCB", "300476.SZ": "Victory Giant", "000977.SZ": "Inspur", "6146.T": "Disco",
    "6920.T": "Lasertec", "4062.T": "Ibiden", "0522.HK": "ASMPT", "002371.SZ": "Naura",
    "688012.SS": "AMEC", "NOKIA.HE": "Nokia", "PRY.MI": "Prysmian", "LR.PA": "Legrand",
    "CAP.PA": "Capgemini", "DSY.PA": "Dassault Sys", "EL.PA": "EssilorLux", "6954.T": "Fanuc",
    "6506.T": "Yaskawa", "6861.T": "Keyence", "9880.HK": "UBTech", "9660.HK": "Horizon Rob.",
    "TCS.NS": "TCS", "INFY.NS": "Infosys", "HCLTECH.NS": "HCLTech", "6702.T": "Fujitsu",
    "6701.T": "NEC", "0992.HK": "Lenovo", "3896.HK": "Kingsoft Cloud", "1024.HK": "Kuaishou",
    "035720.KS": "Kakao", "ASML.AS": "ASML", "ASM.AS": "ASMI", "BESI.AS": "BESI",
    "688825.SS": "CXMT", "688836.SS": "Unitree", "2513.HK": "Zhipu AI", "0100.HK": "MiniMax",
    "688795.SS": "Moore Threads", "688802.SS": "MetaX", "6082.HK": "Biren", "9903.HK": "Iluvatar",
    "7769.TW": "Hon Precision", "688820.SS": "SJ Semi", "1810.HK": "Xiaomi", "2228.HK": "XtalPi",
    "3696.HK": "Insilico", "002384.SZ": "Dongshan", "5016.T": "JX Metals", "064400.KS": "LG CNS",
}

COUNTRIES = {
    "US": ("United States", "us", -98, 39), "CA": ("Canada", "row", -106, 56),
    "CN": ("China", "cn", 104, 34), "HK": ("Hong Kong", "cn", 114.2, 22.3),
    "TW": ("Taiwan", "tw", 121, 23.7), "JP": ("Japan", "jp", 138.5, 36.5),
    "KR": ("South Korea", "kr", 127.8, 36.3), "NL": ("Netherlands", "eu", 5.3, 52.1),
    "DE": ("Germany", "eu", 10.4, 51.1), "FR": ("France", "eu", 2.4, 46.6),
    "GB": ("United Kingdom", "eu", -2, 53.5), "CH": ("Switzerland", "eu", 8.2, 46.8),
    "FI": ("Finland", "eu", 26, 63.5), "IT": ("Italy", "eu", 12.5, 42.8),
    "AT": ("Austria", "eu", 14.5, 47.6), "IE": ("Ireland", "eu", -8, 53.2),
    "SE": ("Sweden", "eu", 16, 62), "ES": ("Spain", "eu", -3.7, 40.4),
    "DK": ("Denmark", "eu", 10, 56), "NO": ("Norway", "eu", 9, 61), "BE": ("Belgium", "eu", 4.5, 50.6),
    "IL": ("Israel", "row", 35, 31.4), "IN": ("India", "row", 79, 22),
    "AU": ("Australia", "row", 134, -25), "SG": ("Singapore", "row", 103.8, 1.35),
    "AE": ("UAE", "row", 54, 24), "SA": ("Saudi Arabia", "row", 45, 24), "BR": ("Brazil", "row", -52, -10),
}


def short_label(t, name):
    if t in SHORT:
        return SHORT[t]
    if "." not in t:
        return t
    base = t.split(".")[0]
    if base.isalpha() and len(base) <= 6:
        return base
    s = re.sub(r"\b(Technolog(y|ies)|Holdings?|Group|Electronics?|Inc|Corp|International|Industries|Co|Ltd|Precision)\b\.?", "", name)
    return re.sub(r"\s+", " ", s).strip()[:16]


def main():
    universe = list(csv.DictReader(open(DATA / "universe.csv", newline="")))
    market = json.loads((DATA / "market.json").read_text())
    quotes = market["quotes"]

    companies, missing = [], []
    for r in universe:
        q = quotes.get(r["ticker"])
        if r["country"] not in COUNTRIES:
            raise SystemExit(f"unknown country {r['country']} for {r['ticker']}")
        if not q:
            missing.append({"t": r["ticker"], "n": r["name"]})
            continue
        companies.append({
            "t": r["ticker"], "n": r["name"], "lab": short_label(r["ticker"], r["name"]),
            "c": r["country"], "l": r["layer"], "s": r["segment"], "tier": r["tier"], "note": r["note"],
            "p": q["price"], "cur": q["currency"], "mc": q["mcap_usd"], "ex": q["exchange"],
            "lb": q["last_bar"], "ipo": q["listed_since"], "r": q["ret"], "sp": q["spark"],
            "listed": r.get("listed") or None,
        })

    payload = {
        "asof": market["asof"], "source": market["source"], "fx": market["fx_to_usd"],
        "layers": [{"id": i, "name": n, "desc": d} for i, n, d in LAYERS],
        "countries": {k: {"name": v[0], "region": v[1], "lon": v[2], "lat": v[3]} for k, v in COUNTRIES.items()},
        "companies": companies, "missing": missing,
        "pipeline": list(csv.DictReader(open(DATA / "pipeline.csv", newline=""))),
        "stale": [p for p in market["problems"] if p["issue"].startswith("stale")],
    }
    html = TEMPLATE.read_text()

    def inline(s):  # keep "</script>" inside data from closing the tag
        return s.replace("</", "<\\/")

    html = (html.replace("/*__D3__*/", (VENDOR / "d3.min.js").read_text())
                .replace("/*__TOPOJSON__*/", (VENDOR / "topojson-client.min.js").read_text())
                .replace("/*__WORLD__*/", inline((VENDOR / "countries-110m.json").read_text()))
                .replace("/*__DATA__*/", inline(json.dumps(payload, separators=(",", ":")))))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    for f in (ROOT / "static").glob("*"):  # social card etc.
        shutil.copy(f, OUT.parent / f.name)
    total = sum(c["mc"] for c in companies)
    print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.1f} MB): {len(companies)} companies, "
          f"${total/1e12:.1f}T, {len(missing)} missing")


if __name__ == "__main__":
    main()
