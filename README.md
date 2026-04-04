# IPO Filing Analyzer — What Works (and What Doesn't) When Building GenAI on Databricks

A fully functional multi-agent system analyzing 19 tech IPO filings — with an honest assessment of platform capabilities and limitations. Built to show what enterprise GenAI actually looks like in practice.

## What It Does

Equity analysts at a fund have a hypothesis: **companies that can't explain themselves clearly in their S-1 filing tend to underperform.** This system tests that hypothesis at scale:

1. **Parses** 19 S-1 filings from SEC EDGAR (Snowflake, Coinbase, Robinhood, DoorDash, etc.)
2. **Indexes** them with Vector Search for semantic retrieval
3. **Scores** each section for messaging clarity using LLM-as-judge (1-100 scale)
4. **Correlates** clarity scores with 12-month stock returns
5. **Deploys** as a multi-tool agent that analysts query in natural language

The signature query: *"Show me the clarity scores of the top 10 performing tech IPO stocks in their first year."*

## Architecture

```
SEC EDGAR (HTML) → BeautifulSoup → Delta Table → Vector Search Index
                                                        ↓
Yahoo Finance → Stock Performance Table          LangGraph ReAct Agent
                                                   ├── search_filings (two-stage retrieval)
                                                   ├── get_stock_performance (UC function)
                                                   ├── score_clarity (LLM-as-judge UC function)
                                                   └── query_scored_database (UC function)
                                                        ↓
                                              Model Serving Endpoint
                                                        ↓
                                              Lakehouse Monitor
```

**Stack:** Databricks (Unity Catalog, Vector Search, Model Serving, Lakehouse Monitor), LangGraph, LangChain, MLflow, BeautifulSoup

## The 8 Notebooks

Each notebook builds on the previous, progressively assembling the full system:

| # | Notebook | What It Builds | Key Engineering Decision |
|---|----------|---------------|------------------------|
| 01 | [Data Pipeline](labs/01-data-pipeline.ipynb) | HTML parsing, chunking, Vector Search index | 3000-char chunks (not 1000) — [why this matters](#chunk-size-matters-more-than-model-choice) |
| 02 | [Research Agent](labs/02-ipo-research-agent.ipynb) | Multi-tool RAG agent with UC functions | Two-stage retrieval: SQL keyword filter + vector search |
| 03 | [Clarity Scoring](labs/03-clarity-scoring-engine.ipynb) | LLM-as-judge scorer, ChatAgent, UC registration | Code-based MLflow logging for complex agents |
| 04 | [Tracing](labs/04-tracing-reproducibility.ipynb) | MLflow autologging, run tagging, version comparison | Traces make "why did Coinbase score 43?" answerable |
| 05 | [Guardrails](labs/05-guardrails-compliance.ipynb) | PII detection, topic classifier, safety policies | LLM-based classifiers vs regex for different threat types |
| 06 | [Evaluation](labs/06-evaluation-batch-scoring.ipynb) | `mlflow.evaluate`, batch scoring, custom metrics | `make_genai_metric` for domain-specific evaluation |
| 07 | [Deployment](labs/07-deployment.ipynb) | Model Serving endpoint, A/B traffic config | Complex agents may fail to deploy — [see limitations](#model-serving-limitations) |
| 08 | [Monitoring](labs/08-monitoring-insights.ipynb) | Inference logging, Lakehouse Monitor, drift detection | Monitor setup is straightforward; getting data into it is the hard part |

## What Actually Worked

### Chunk Size Matters More Than Model Choice

We tested three LLM endpoints on the same retrieval task ("What did Snowflake say about competition?"):

| Model | Tool Calling | Analysis Quality | Cost |
|-------|-------------|-----------------|------|
| Llama 4 Maverick | Broken (narrated tool calls as text) | N/A | ~$0.02/query |
| Llama 3.3 70B | Reliable | Shallow but correct | ~$0.01/query |
| Llama 3.1 405B | Reliable | Good structured analysis | ~$0.05/query |

But switching from 70B to 405B barely improved results. **The real breakthrough was changing chunk_size from 1000 to 3000 characters.** Snowflake's competition section (~1200 chars) was being split across 6 tiny fragments — no model could synthesize what it couldn't see.

| Chunk Size | Total Chunks | Competition section in one chunk? | Agent found AWS/Azure/GCP? |
|-----------|-------------|----------------------------------|--------------------------|
| 1000 chars | 20,898 | No (split across 6 chunks) | No |
| 3000 chars | 6,527 | Yes | Yes |

**Lesson:** Before upgrading your model, check your chunking. A $0.01/query model with good chunks beats a $0.05/query model with bad chunks.

### Two-Stage Retrieval Beats Pure Vector Search

Vector search alone returned irrelevant chunks even with company filtering. The embedding model ranked SEC boilerplate (underwriter info, legal disclaimers) higher than actual competition content.

The fix: **SQL keyword pre-filter first, then vector search to supplement.**

```python
# Stage 1: SQL keyword search — guarantees topic-relevant chunks
sql = f"""SELECT chunk_text FROM filing_chunks
          WHERE path LIKE '%{ticker}%'
          AND (LOWER(chunk_text) LIKE '%{keyword}%')"""

# Stage 2: Vector search — adds semantic matches
results = index.similarity_search(query, filters={"path LIKE": f"%{ticker}%"})
```

This ensures the competition section (which contains the word "competition") is always in context, even if the embedding model doesn't rank it highly.

### HTML Parsing: BeautifulSoup Over ai_parse_document

`ai_parse_document()` is designed for PDFs and images — it returned empty elements for HTML files. BeautifulSoup's `get_text()` extracts clean text from SEC EDGAR HTML filings reliably. Simple but effective.

### Code-Based MLflow Logging for Complex Agents

`mlflow.pyfunc.log_model(python_model=MyAgent())` fails when the agent contains non-serializable objects (Vector Search clients, LangGraph agents, UC toolkit instances). The fix: write the agent class to a `.py` file and use code-based logging:

```python
mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model="/path/to/agent_model.py",  # file path, not object
)
```

## What Didn't Work (and Why)

### Model Serving Limitations

The ChatAgent deploys successfully to Unity Catalog, but **Model Serving fails to load it** on trial workspaces. The agent's `__init__` method connects to Vector Search and UC functions — these external dependencies aren't available during the serving container's model loading phase.

**Impact:** Labs 07-08 demonstrate the deployment *pattern* (endpoint creation, A/B traffic, inference logging) but the endpoint doesn't serve live traffic.

**What production would need:** Environment variables for endpoint URLs, lazy initialization of external clients, or Databricks' managed agent deployment (which handles dependency injection).

### Llama 4 Maverick: Newer Isn't Always Better for Agents

Llama 4 Maverick (the default Databricks foundation model) has good general capabilities but **narrates tool calls as text instead of executing them**:

```
# What Maverick produces (wrong):
"Let me look up the stock data: [get_stock_performance(ticker_symbol=SNOW)]"

# What it should do:
Actually calls get_stock_performance → gets real data → synthesizes answer
```

Llama 3.3 70B and 3.1 405B — older models — handle structured tool calling reliably.

### GPT-5 Models: Listed but Blocked on Trial

All `databricks-gpt-5-*` endpoints appear in the workspace but return `rate_limit=0` on trial accounts. The Llama models are the only pay-per-token options that actually work.

### Vector Search Index Sync Timing

After rebuilding chunks and creating a new VS index, there's a **multi-minute sync period** where queries return stale or incomplete results. One of our test runs produced "Snowflake did not mention competitors" because the index hadn't finished syncing the new 3000-char chunks.

**Lesson:** Always verify `index.describe()["status"]["ready"] == True` before querying, and build wait loops into pipelines.

## Quick Start

### Prerequisites

- Databricks workspace (pay-as-you-go or trial)
- Foundation Model APIs enabled
- Python 3.10+ locally (for setup script)
- `pip install databricks-sdk yfinance beautifulsoup4`

### Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/ipo-filing-analyzer.git
cd ipo-filing-analyzer

# Configure
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi...

# Run setup (downloads S-1 filings, creates catalog, loads stock data)
python scripts/setup-catalog.py

# Upload notebooks to workspace
# Then open Lab 01 in Databricks and run sequentially through Lab 08
```

### Validation

```bash
python scripts/test-labs.py              # all labs
python scripts/test-labs.py --labs 1 2 3  # specific labs
```

## Companies Analyzed

19 tech IPOs from 2020-2024: Snowflake, Palantir, DoorDash, Coinbase, Rivian, Unity, Roblox, Bumble, Affirm, Robinhood, Toast, Confluent, GitLab, HashiCorp, Duolingo, Instacart, Klaviyo, Arm Holdings, Reddit.

## Cost

~$15-25 total across all notebooks. The Vector Search endpoint (~$0.50-1.00/hr) is the main cost — delete it when not working. Run `python scripts/cleanup.py` when done.

## License

[MIT](LICENSE)
