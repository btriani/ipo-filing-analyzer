#!/usr/bin/env python3
"""
setup-catalog.py -- Download S-1 filings from SEC EDGAR, create Unity Catalog resources.

Usage:
    pip install databricks-sdk
    export DATABRICKS_HOST=https://...
    export DATABRICKS_TOKEN=dapi...
    python scripts/setup-catalog.py
"""

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from databricks.sdk import WorkspaceClient

sys.path.insert(0, str(Path(__file__).parent))
from companies import COMPANIES

CATALOG = "ipo_analyzer"
SCHEMA = "default"
VOLUME = "sec_filings"
FILINGS_DIR = Path(__file__).parent.parent / "assets" / "sec-filings"

HEADERS = {"User-Agent": "IPOAnalyzer contact@example.com"}


def download_filings():
    """Download S-1 filings from SEC EDGAR using the FULL-TEXT search + submissions API."""
    FILINGS_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    failed = []

    for c in COMPANIES:
        ticker = c["ticker"]
        dest = FILINGS_DIR / f"{ticker}-S1.html"
        if dest.exists():
            print(f"  Already exists: {ticker}")
            downloaded += 1
            continue

        ipo_year = c["ipo_date"][:4]
        print(f"  {ticker} ({c['company']}): searching EDGAR...", end=" ")

        try:
            # Search EDGAR for S-1 filings by company name
            search_url = (
                f"https://efts.sec.gov/LATEST/search-index?"
                f"q=%22{c['company'].replace(' ', '%20')}%22"
                f"&forms=S-1"
                f"&dateRange=custom&startdt={ipo_year}-01-01&enddt={int(ipo_year)+1}-12-31"
            )
            req = urllib.request.Request(search_url, headers=HEADERS)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
                hits = data.get("hits", {}).get("hits", [])

            if not hits:
                print("NO HITS (may use F-1 or different form)")
                failed.append(ticker)
                time.sleep(0.5)
                continue

            # Get accession number from first hit
            adsh = hits[0]["_source"]["adsh"]
            adsh_clean = adsh.replace("-", "")
            cik_clean = c["cik"].lstrip("0")

            # Fetch the filing index to find the main S-1 document
            idx_url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{adsh_clean}/{adsh}-index.htm"
            req2 = urllib.request.Request(idx_url, headers=HEADERS)
            with urllib.request.urlopen(req2) as resp2:
                idx_content = resp2.read().decode("utf-8", errors="replace")

            # Find the main S-1 document link (look for s-1/s1 in filename)
            links = re.findall(r'href="(/Archives/edgar/data/[^"]+\.htm)"', idx_content)
            s1_link = None
            for link in links:
                if "s-1" in link.lower() or "s1" in link.lower():
                    s1_link = link
                    break
            if not s1_link:
                # Skip exhibits and index, take the first content document
                for link in links:
                    lower = link.lower()
                    if not any(x in lower for x in ["index", "exhibit", "ex-", "ex1", "ex2", "ex3", "ex4", "ex5"]):
                        s1_link = link
                        break

            if not s1_link:
                print(f"NO MAIN DOC in filing index")
                failed.append(ticker)
                time.sleep(0.5)
                continue

            # Download the actual S-1 filing
            doc_url = f"https://www.sec.gov{s1_link}"
            req3 = urllib.request.Request(doc_url, headers=HEADERS)
            with urllib.request.urlopen(req3) as resp3:
                content = resp3.read()

            dest.write_bytes(content)
            print(f"OK ({len(content) / 1024:.0f} KB)")
            downloaded += 1

        except Exception as e:
            print(f"ERROR: {str(e)[:80]}")
            failed.append(ticker)

        time.sleep(0.5)  # SEC fair access: max 10 req/sec

    return downloaded, failed


def main():
    print("=" * 60)
    print("IPO Filing Analyzer — Setup")
    print("=" * 60)
    print()

    # 1. Download filings
    print("Step 1: Downloading S-1 filings from SEC EDGAR...")
    downloaded, failed = download_filings()
    filings = sorted(FILINGS_DIR.glob("*-S1.html"))
    print(f"\n  {len(filings)} filings ready")
    if failed:
        print(f"  Failed: {failed} (may use F-1 form or different filing type)")
    print()

    # 2. Create catalog resources
    w = WorkspaceClient()
    warehouses = list(w.warehouses.list())
    if not warehouses:
        print("ERROR: No SQL warehouse found. Create one first.")
        sys.exit(1)
    wh_id = warehouses[0].id
    print(f"Step 2: Creating catalog resources (warehouse: {warehouses[0].name})...")

    for sql in [
        f"CREATE CATALOG IF NOT EXISTS {CATALOG}",
        f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}",
        f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}",
    ]:
        print(f"  {sql}")
        result = w.statement_execution.execute_statement(
            warehouse_id=wh_id, statement=sql, wait_timeout="30s",
        )
        print(f"    -> {result.status.state}")
    print()

    # 3. Upload filings to volume
    volume_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
    print(f"Step 3: Uploading {len(filings)} filings to {volume_path}...")
    for f in filings:
        print(f"  {f.name}")
        with open(f, "rb") as fh:
            w.files.upload(f"{volume_path}/{f.name}", fh, overwrite=True)
    print()

    # 4. Load stock performance data via yfinance
    print("Step 4: Loading stock performance data from Yahoo Finance...")
    try:
        import yfinance as yf
        import pandas as pd
        from datetime import datetime, timedelta

        rows = []
        for c in COMPANIES:
            ticker = c["ticker"]
            ipo_date = c["ipo_date"]
            ipo_year = ipo_date[:4]
            print(f"  {ticker}: ", end="", flush=True)
            try:
                stock = yf.Ticker(ticker)
                end_date = (datetime.strptime(ipo_date, "%Y-%m-%d") + timedelta(days=420)).strftime("%Y-%m-%d")
                hist = stock.history(start=ipo_date, end=end_date)
                if len(hist) < 2:
                    print("insufficient data")
                    continue
                hist.index = hist.index.tz_localize(None)
                ipo_price = float(hist.iloc[0]["Close"])
                ipo_dt = pd.Timestamp(ipo_date)

                def _price_at(months):
                    after = hist.index[hist.index >= ipo_dt + pd.DateOffset(months=months)]
                    return float(hist.loc[after[0]]["Close"]) if len(after) > 0 else None

                p3, p6, p12 = _price_at(3), _price_at(6), _price_at(12)
                ret = round(((p12 - ipo_price) / ipo_price * 100), 1) if p12 else None
                rows.append({"company": c["company"], "ticker": ticker, "sector": c["sector"],
                             "ipo_date": ipo_date, "ipo_price": round(ipo_price, 2),
                             "price_3m": round(p3, 2) if p3 else None,
                             "price_6m": round(p6, 2) if p6 else None,
                             "price_12m": round(p12, 2) if p12 else None,
                             "twelve_month_return_pct": float(ret) if ret else None})
                print(f"${ipo_price:.0f} → {ret:+.1f}%" if ret else "partial")
            except Exception as e:
                print(f"ERROR: {e}")

        if rows:
            # Upload as Delta table via SQL INSERT
            create_sql = f"""CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.stock_performance (
                company STRING, ticker STRING, sector STRING, ipo_date STRING,
                ipo_price DOUBLE, price_3m DOUBLE, price_6m DOUBLE, price_12m DOUBLE,
                twelve_month_return_pct DOUBLE)"""
            w.statement_execution.execute_statement(warehouse_id=wh_id, statement=create_sql, wait_timeout="30s")
            for row in rows:
                vals = []
                for col in ["company","ticker","sector","ipo_date","ipo_price","price_3m","price_6m","price_12m","twelve_month_return_pct"]:
                    v = row[col]
                    if v is None:
                        vals.append("NULL")
                    elif isinstance(v, str):
                        vals.append(f"'{v}'")
                    else:
                        vals.append(str(v))
                w.statement_execution.execute_statement(
                    warehouse_id=wh_id,
                    statement=f"INSERT INTO {CATALOG}.{SCHEMA}.stock_performance VALUES ({', '.join(vals)})",
                    wait_timeout="30s")
            print(f"\n  {len(rows)} companies loaded into {CATALOG}.{SCHEMA}.stock_performance")
        else:
            print("  WARNING: No stock data loaded. Install yfinance: pip install yfinance")
    except ImportError:
        print("  yfinance not installed — skipping stock data. Install with: pip install yfinance")
        print("  Lab 01 will still work if the stock_performance table is populated manually.")
    print()

    print("=" * 60)
    print("Setup complete!")
    print(f"  Catalog : {CATALOG}")
    print(f"  Volume  : {CATALOG}.{SCHEMA}.{VOLUME}")
    print(f"  Filings : {len(filings)}")
    print()
    print("Next: Open Lab 01 in your Databricks workspace.")
    print("=" * 60)


if __name__ == "__main__":
    main()
