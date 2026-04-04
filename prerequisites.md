# Prerequisites

Everything you need before running the notebooks.

## 1. Databricks Workspace

You need a Databricks workspace with **pay-as-you-go** pricing. Community Edition will NOT work — it lacks Unity Catalog, Vector Search, and Model Serving.

Sign up: [https://www.databricks.com/try-databricks](https://www.databricks.com/try-databricks)

### Required Features

Your workspace must have:
- **Unity Catalog** enabled (default on new workspaces)
- **Serverless compute** available
- **Foundation Model APIs** access

## 2. Foundation Model APIs

The notebooks use `databricks-meta-llama-3.1-405b-instruct` for all LLM calls. See the [README](README.md#newer-isnt-always-better-for-agents) for why we chose this over newer models.

Other endpoints that work on trial workspaces:
- `databricks-meta-llama-3-3-70b-instruct` — cheaper, slightly less capable
- `databricks-meta-llama-3-1-8b-instruct` — cheapest, good for simple tasks

> **Note:** `databricks-gpt-5-*` endpoints appear in trial workspaces but are rate-limited to 0 (blocked). `databricks-llama-4-maverick` has unreliable tool calling — not recommended for agents.

## 3. Python 3.10+

Required for running the setup scripts locally. Notebooks install their own dependencies via `%pip`.

```bash
pip install databricks-sdk yfinance beautifulsoup4
```

## 4. Compute

All notebooks run on **serverless compute** — no cluster setup needed.

| Compute Type | Used In | Cost | Action Required |
|---|---|---|---|
| Serverless Notebooks | All notebooks | ~$0.07/DBU, per-second | Auto-managed |
| Foundation Model APIs | Notebooks 01-08 | Pay-per-token | Nothing |
| Vector Search Endpoint | Notebooks 01-07 | ~$0.50-1.00/hr | **Delete when done** |
| Model Serving Endpoint | Notebooks 07-08 | Pay-per-token | Delete when done |

> **Important:** The Vector Search endpoint bills continuously. Delete it between sessions.

## 5. Setup

```bash
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi...
python scripts/setup-catalog.py
```

This downloads 19 S-1 filings from SEC EDGAR, loads stock data via yfinance, creates Unity Catalog objects, and uploads filings to a Volume.

## Cost Estimate

| Resource | Estimated Cost |
|---|---|
| Serverless compute | ~$3-5 |
| Foundation Model API calls | ~$5-10 |
| Vector Search endpoint | ~$2-4 |
| Model Serving endpoint | ~$2-3 |
| **Total** | **~$15-25** |

Delete the Vector Search endpoint when you stop for the day to minimize costs.
