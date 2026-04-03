#!/usr/bin/env python3
"""
setup-catalog.py -- Download S-1 filings from SEC EDGAR, create Unity Catalog resources.

Usage:
    pip install sec-edgar-downloader databricks-sdk
    export DATABRICKS_HOST=https://...
    export DATABRICKS_TOKEN=dapi...
    python scripts/setup-catalog.py
"""

import os
import sys
import time
import shutil
from pathlib import Path

from databricks.sdk import WorkspaceClient
from sec_edgar_downloader import Downloader

sys.path.insert(0, str(Path(__file__).parent))
from companies import COMPANIES

CATALOG = "ipo_analyzer"
SCHEMA = "default"
VOLUME = "sec_filings"
FILINGS_DIR = Path(__file__).parent.parent / "assets" / "sec-filings"


def download_filings():
    """Download S-1 filings from SEC EDGAR for all companies."""
    FILINGS_DIR.mkdir(parents=True, exist_ok=True)

    dl = Downloader("IPOAnalyzer", "contact@example.com", str(FILINGS_DIR))

    for company in COMPANIES:
        ticker = company["ticker"]
        dest = FILINGS_DIR / f"{ticker}-S1.html"
        if dest.exists():
            print(f"  Already exists: {ticker}")
            continue

        print(f"  Downloading S-1 for {ticker} ({company['company']})...")
        try:
            dl.get("S-1", ticker, limit=1)
            # sec-edgar-downloader saves to nested dirs — find and move the file
            search_dir = FILINGS_DIR / "sec-edgar-filings" / ticker
            html_files = list(search_dir.rglob("*.htm*")) if search_dir.exists() else []

            if html_files:
                shutil.copy2(str(html_files[0]), str(dest))
                print(f"    OK: {dest.name}")
            else:
                # Try S-1/A (amendment) as fallback
                print(f"    No S-1 found, trying S-1/A...")
                dl.get("S-1/A", ticker, limit=1)
                html_files = list(search_dir.rglob("*.htm*")) if search_dir.exists() else []
                if html_files:
                    shutil.copy2(str(html_files[0]), str(dest))
                    print(f"    OK (S-1/A): {dest.name}")
                else:
                    print(f"    SKIPPED: No S-1 filing found for {ticker}")
        except Exception as e:
            print(f"    ERROR: {e}")

        time.sleep(0.5)  # SEC fair access

    # Clean up nested directory structure
    nested = FILINGS_DIR / "sec-edgar-filings"
    if nested.exists():
        shutil.rmtree(nested)


def main():
    print("=" * 60)
    print("IPO Filing Analyzer — Setup")
    print("=" * 60)
    print()

    # 1. Download filings
    print("Step 1: Downloading S-1 filings from SEC EDGAR...")
    download_filings()
    filings = sorted(FILINGS_DIR.glob("*-S1.html"))
    print(f"\n  {len(filings)} filings ready")
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
