# Prerequisites

Everything you need before starting the labs.

## 1. Databricks Workspace

You need a Databricks workspace with **pay-as-you-go** pricing. Community Edition will NOT work — it lacks Unity Catalog, Vector Search, and Model Serving.

Sign up: [https://www.databricks.com/try-databricks](https://www.databricks.com/try-databricks)

> **Important:** Choose the pay-as-you-go plan. You only pay for what you use. Total cost for all labs is ~$12-19.

### Required Features

Your workspace must have:
- **Unity Catalog** enabled (default on new workspaces)
- **Serverless compute** available
- **Foundation Model APIs** access — specifically `databricks-llama-4-maverick`

## 2. Foundation Model APIs

Labs use `databricks-llama-4-maverick` for all LLM calls (tool calling, scoring, evaluation). Verify it is available in your workspace:

1. Go to **Serving** in the left sidebar.
2. Search for `databricks-llama-4-maverick`.
3. If it appears with a green status, you're set.

Other endpoints available on trial workspaces (not required, but good to know):
- `databricks-meta-llama-3-3-70b-instruct` — good alternative for simple tasks
- `databricks-meta-llama-3-1-8b-instruct` — cheap, good for summarization

## 3. Python 3.10+

Required for running the setup scripts locally. Notebooks install their own dependencies via `%pip` — you don't need everything locally.

**macOS:**
```bash
brew install python@3.12
```

**Windows:**
```powershell
winget install Python.Python.3.12
```

**Linux:**
```bash
sudo apt install python3.12 python3.12-venv
```

### Python Packages (for setup scripts only)

```bash
pip install databricks-sdk
```

The notebooks install their own packages. The full set used across all labs:

```
databricks-sdk
sec-edgar-downloader
yfinance
langchain
langchain-community
langgraph
mlflow
databricks-agents
```

## 4. Compute

All labs run on **serverless compute** — no cluster setup needed. Serverless starts instantly and bills per-second of actual usage.

### What's Running (and What Costs Money)

| Compute Type | Used In | Cost | Action Required |
|---|---|---|---|
| Serverless Notebooks | All labs | ~$0.07/DBU, per-second | Nothing — auto-managed |
| Foundation Model APIs | Labs 01-08 | Pay-per-token | Uses `databricks-llama-4-maverick` |
| Vector Search Endpoint | Labs 01-07 | ~$0.50-1.00/hr | **Delete when done for the day** |
| Model Serving Endpoint | Labs 07-08 | Pay-per-token, scale-to-zero | Delete when done |

> **Important:** The Vector Search endpoint is the only resource that bills continuously. Lab 01 creates it. Keep it running through Lab 07, then delete it (or delete and recreate between sessions).

## 5. Catalog

The setup script creates everything in the `ipo_analyzer` catalog:

```
ipo_analyzer
└── default
    ├── filings_raw        (raw S-1 text, ~22 filings)
    ├── filing_chunks      (chunked text for Vector Search)
    ├── stock_returns      (price data from yfinance)
    └── clarity_scores     (populated in Lab 06)
```

Run the setup script before Lab 01:

```bash
python scripts/setup-catalog.py
```

This downloads ~22 S-1 filings via `sec-edgar-downloader`, loads stock return data, creates the Unity Catalog objects, and confirms the Vector Search endpoint exists (or creates it).

## Cost Estimate

| Resource | Estimated Cost |
|---|---|
| Serverless compute (all labs) | ~$3-5 |
| Foundation Model API calls (all labs) | ~$5-8 |
| Vector Search endpoint (one session) | ~$2-4 |
| Model Serving endpoint (Lab 07-08) | ~$2-3 |
| **Total** | **~$12-19** |

Costs vary based on how long you leave the Vector Search endpoint running between sessions. Delete it when you stop for the day.

## Next Step

Run the setup script, then open Lab 01:

```bash
python scripts/setup-catalog.py
```

Start with [Lab 01: Data Pipeline](labs/01-data-pipeline.ipynb).
