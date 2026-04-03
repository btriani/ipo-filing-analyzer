# Prerequisites

Everything you need before starting the labs.

## 1. Databricks Workspace

You need a Databricks workspace with **pay-as-you-go** pricing. Community Edition will NOT work — it lacks Unity Catalog, Vector Search, and Model Serving.

Sign up: [https://www.databricks.com/try-databricks](https://www.databricks.com/try-databricks)

> **Important:** Choose the pay-as-you-go plan. You only pay for what you use. Total cost for all labs is ~$15-25.

### Required Features

Your workspace must have:
- **Unity Catalog** enabled (default on new workspaces)
- **Serverless compute** available
- **Foundation Model APIs** access (DBRX, Meta Llama, etc.)

## 2. Databricks CLI

Used by setup and cleanup scripts.

**macOS:**
```bash
brew tap databricks/tap
brew install databricks
```

**Windows / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
```

Full install docs: [https://docs.databricks.com/en/dev-tools/cli/install.html](https://docs.databricks.com/en/dev-tools/cli/install.html)

### Authenticate

```bash
databricks configure
```

Enter your workspace URL (e.g., `https://adb-1234567890.12.azuredatabricks.net`) and a personal access token.

Alternatively, use OAuth:
```bash
databricks auth login --host https://your-workspace-url
```

## 3. Python 3.10+

Required for notebooks and setup scripts.

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

### Python Packages

Install locally (for running setup scripts):
```bash
pip install databricks-sdk mlflow langchain langchain-community
```

> **Note:** Notebooks install their own dependencies via `%pip` — you don't need to install everything locally.

## 4. Git

For cloning this repo and version control.

```bash
git --version
# Should show 2.40+ (or latest)
```

## 5. Compute

All labs run on **serverless compute** by default — no cluster setup needed. Serverless starts instantly and bills per-second of actual usage.

### What's Running (and What Costs Money)

| Compute Type | Used In | Cost | You Need To... |
|---|---|---|---|
| Serverless Notebooks | All labs | ~$0.07/DBU, per-second | Nothing — auto-managed |
| Foundation Model APIs | Labs 01-08 | Pay-per-token | Choose cost profile in notebook |
| Vector Search Endpoint | Labs 02-09 | ~$0.50-1.00/hr | **Delete when done for the day** |
| Model Serving Endpoint | Labs 09-10 | Pay-per-token, scale-to-zero | Delete when done |

> **Important:** The Vector Search endpoint is the only resource that bills continuously. Create it in Lab 02, keep it running through Lab 09, then delete it. If you stop between sessions, delete it and recreate it when you resume.

### Alternative: Classic Clusters

If your workspace supports classic clusters (pay-as-you-go accounts), you can create one instead:
- **Runtime:** DBR 15.4 LTS ML (or newer)
- **Node type:** Single node, i3.xlarge (or equivalent)
- **Auto-termination:** 30 minutes

Serverless is recommended for these labs — it's simpler and often cheaper for short sessions.

## Verification

Run the prerequisites check:
```bash
./scripts/check-prerequisites.sh
```

## Next Step

Run the setup script, then start Lab 01:
```bash
python scripts/setup-catalog.py
```

Start with [Lab 01: Document Parsing & Chunking](labs/01-document-parsing-chunking/workbook.md).
