#!/usr/bin/env python3
"""
setup-catalog.py -- Download arXiv papers, create Unity Catalog objects, and upload.

Usage:
    python scripts/setup-catalog.py

Downloads arXiv papers to assets/arxiv-papers/, then creates:
    - Catalog: genai_lab_guide
    - Schema: genai_lab_guide.default
    - Volume: genai_lab_guide.default.arxiv_papers
    - Uploads all PDFs to the volume
"""

import os
import sys
import urllib.request
from pathlib import Path
from databricks.sdk import WorkspaceClient

CATALOG = "genai_lab_guide"
SCHEMA = "default"
VOLUME = "arxiv_papers"
PAPERS_DIR = Path(__file__).parent.parent / "assets" / "arxiv-papers"

# arXiv papers used across all labs
PAPERS = {
    "attention-is-all-you-need.pdf": "https://arxiv.org/pdf/1706.03762",
    "bert.pdf": "https://arxiv.org/pdf/1810.04805",
    "rag.pdf": "https://arxiv.org/pdf/2005.11401",
    "lora.pdf": "https://arxiv.org/pdf/2106.09685",
    "chain-of-thought.pdf": "https://arxiv.org/pdf/2201.11903",
    "llama.pdf": "https://arxiv.org/pdf/2302.13971",
    "constitutional-ai.pdf": "https://arxiv.org/pdf/2212.08073",
    "toolformer.pdf": "https://arxiv.org/pdf/2302.04761",
}


def download_papers():
    """Download arXiv papers to assets/arxiv-papers/."""
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(PAPERS)} papers to {PAPERS_DIR}...")
    for filename, url in PAPERS.items():
        filepath = PAPERS_DIR / filename
        if filepath.exists():
            print(f"  Already exists: {filename}")
            continue
        print(f"  Downloading: {filename}")
        urllib.request.urlretrieve(url, filepath)
    print()


def main():
    print("Setting up Databricks resources for GenAI Lab Guide...")
    print()

    # 1. Download papers from arXiv
    download_papers()

    w = WorkspaceClient()

    # 2. Find a SQL warehouse to execute DDL statements
    warehouses = list(w.warehouses.list())
    if not warehouses:
        print("ERROR: No SQL warehouse found. Create one in your Databricks workspace first.")
        sys.exit(1)
    wh_id = warehouses[0].id
    print(f"Using warehouse: {warehouses[0].name} ({wh_id})")
    print()

    # 3. Create catalog, schema, and volume via SQL (works on Default Storage workspaces)
    full_schema = f"{CATALOG}.{SCHEMA}"
    full_volume = f"{CATALOG}.{SCHEMA}.{VOLUME}"

    print("Creating Unity Catalog resources...")
    for sql in [
        f"CREATE CATALOG IF NOT EXISTS {CATALOG}",
        f"CREATE SCHEMA IF NOT EXISTS {full_schema}",
        f"CREATE VOLUME IF NOT EXISTS {full_volume}",
    ]:
        print(f"  Running: {sql}")
        result = w.statement_execution.execute_statement(
            warehouse_id=wh_id,
            statement=sql,
            wait_timeout="30s",
        )
        print(f"    Result: {result.status.state}")
    print()

    # 4. Upload PDFs
    volume_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))

    print(f"Uploading {len(pdf_files)} papers to {volume_path}...")
    for pdf_path in pdf_files:
        remote_path = f"{volume_path}/{pdf_path.name}"
        print(f"  Uploading: {pdf_path.name}")
        with open(pdf_path, "rb") as f:
            w.files.upload(remote_path, f, overwrite=True)

    print()
    print("============================================")
    print("  Setup complete!")
    print(f"  Catalog:  {CATALOG}")
    print(f"  Schema:   {full_schema}")
    print(f"  Volume:   {full_volume}")
    print(f"  Papers:   {len(pdf_files)} uploaded")
    print()
    print("  Next: Open Lab 01 notebook in your Databricks workspace.")
    print("============================================")


if __name__ == "__main__":
    main()
