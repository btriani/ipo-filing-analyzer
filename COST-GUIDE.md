# Cost Guide

Realistic cost estimates for completing all 10 labs. Total: **~$15-25** depending on how quickly you work and whether you shut down resources between sessions.

## Per-Lab Cost Breakdown

| # | Lab | Compute | Model/API Calls | Other | Est. Total |
|---|-----|---------|-----------------|-------|------------|
| 01 | Document Parsing & Chunking | Serverless ~$0.50 | ai_parse_document ~$0.50 | Storage ~$0.01 | ~$1-2 |
| 02 | Vector Search & Retrieval | Serverless ~$0.50 | Embeddings ~$0.50 | VS endpoint ~$1 | ~$2-3 |
| 03 | Building a Retrieval Agent | Serverless ~$0.50 | LLM tokens ~$0.50 | -- | ~$1-2 |
| 04 | UC Functions as Agent Tools | Serverless ~$0.50 | LLM tokens ~$0.50 | -- | ~$1-2 |
| 05 | Single Agent with LangChain | Serverless ~$0.50 | LLM tokens ~$0.50 | -- | ~$1-2 |
| 06 | Tracing & Reproducible Agents | Serverless ~$0.50 | LLM tokens ~$0.50 | -- | ~$1 |
| 07 | Guardrails & Governance | Serverless ~$0.50 | LLM tokens ~$0.50 | -- | ~$1-2 |
| 08 | Evaluation & LLM-as-Judge | Serverless ~$0.50 | LLM judge ~$1-2 | -- | ~$2-3 |
| 09 | Deployment & Model Serving | Serverless ~$0.50 | LLM tokens ~$1 | Serving endpoint ~$2 | ~$3-5 |
| 10 | Monitoring & Observability | Serverless ~$0.50 | LLM tokens ~$0.50 | Serving endpoint ~$1 | ~$2-3 |

## Per-Service Pricing Reference

Prices as of early 2026. Always verify at [Databricks Pricing](https://www.databricks.com/product/pricing).

### Compute

| Service | Price | Notes |
|---------|-------|-------|
| Serverless Compute | ~$0.07/DBU | Auto-starts, per-second billing, no idle cost |
| Interactive Cluster (DS3_v2) | ~$0.75/hr | Must be manually stopped |

> **Recommendation:** Use serverless compute whenever possible. It starts in seconds, scales automatically, and has no idle cost.

### Understanding Compute Types

Your Databricks workspace uses several types of compute. Here's what matters for cost:

| Type | How It Works | Cost Risk |
|------|-------------|-----------|
| **Serverless Notebooks** | Starts instantly, stops when idle. Per-second billing. | Low — auto-managed |
| **Serverless SQL Warehouse** | Auto-starts for SQL queries, auto-stops after 10 min idle. | Low — auto-managed |
| **Foundation Model APIs** | Pay-per-token. No idle cost. | Low — proportional to usage |
| **Vector Search Endpoint** | Always-on dedicated compute. Bills continuously until deleted. | **High — must delete manually** |
| **Model Serving Endpoint** | Scale-to-zero available. Bills per-token when active. | Medium — can scale to zero |

> **The #1 cost mistake:** Forgetting to delete the Vector Search endpoint. At ~$0.50-1.00/hr, an overnight endpoint costs ~$12. Always run `python scripts/cleanup.py` when done.

### Foundation Model APIs (Pay-per-token)

| Model | Input | Output |
|-------|-------|--------|
| Meta Llama 3.1 70B | $0.90 / 1M tokens | $0.90 / 1M tokens |
| DBRX Instruct | $0.75 / 1M tokens | $2.25 / 1M tokens |
| BGE Large (embeddings) | $0.10 / 1M tokens | -- |

For lab exercises, typical usage is a few thousand tokens per call. A full lab session rarely exceeds $1 in model costs.

### Vector Search

| Resource | Price | Notes |
|----------|-------|-------|
| Vector Search Endpoint | ~$0.50-1.00/hr | Must be manually deleted when done |
| Delta Sync Index | Included | No separate charge beyond endpoint |

> **Cost tip:** The Vector Search endpoint is the most expensive ongoing resource. Create it in Lab 02, keep it running through Lab 09, then delete it immediately in cleanup.

### Model Serving

| Resource | Price | Notes |
|----------|-------|-------|
| Serverless Serving | Pay-per-token | Same as Foundation Model API pricing |
| Provisioned Throughput | ~$5-10/hr | Only needed for production workloads |

## Stop the Billing Clock

### After Each Session

```bash
# Check for running endpoints
databricks serving-endpoints list

# Delete serving endpoints when done (recreate in minutes)
databricks serving-endpoints delete genai-lab-agent-endpoint

# Delete Vector Search endpoint when done for the day
databricks vector-search endpoints delete genai_lab_guide_vs_endpoint
```

### When Completely Done

```bash
python scripts/cleanup.py
```

This removes everything: catalog, tables, volumes, endpoints.

## Tips to Minimize Cost

1. **Use serverless compute** — no idle charges
2. **Delete the Vector Search endpoint** between multi-day sessions (~$0.50-1.00/hr)
3. **Delete serving endpoints** as soon as you finish Labs 09-10
4. **Run labs in order** — later labs reuse resources from earlier ones
5. **Use the smallest embedding model** (BGE Small) for experiments, BGE Large only for final index
