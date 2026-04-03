# Handoff Note — IPO Analyzer Redesign

**Date:** 2026-04-03
**Repo:** `/tmp/databricks-genai-lab-guide`
**Branch:** `feature/ipo-analyzer-redesign`
**Databricks creds:** `/tmp/.databricks-env` (HOST + TOKEN)
**Workspace notebooks:** `/Users/btriani@gmail.com/genai-lab-guide/`

## What Was Done

The course was redesigned from a 10-lab arXiv research assistant to an 8-lab IPO Filing Analyzer. All notebooks have been created and committed. Documentation has been updated to match.

### New 8-Lab Structure

| Lab | File | Status |
|-----|------|--------|
| 01 - Data Pipeline | `labs/01-data-pipeline.ipynb` | Created |
| 02 - IPO Research Agent | `labs/02-ipo-research-agent.ipynb` | Created |
| 03 - Clarity Scoring Engine | `labs/03-clarity-scoring-engine.ipynb` | Created |
| 04 - Tracing & Reproducibility | `labs/04-tracing-reproducibility.ipynb` | Created |
| 05 - Guardrails & Compliance | `labs/05-guardrails-compliance.ipynb` | Created |
| 06 - Evaluation & Batch Scoring | `labs/06-evaluation-batch-scoring.ipynb` | Created |
| 07 - Deployment | `labs/07-deployment.ipynb` | Created |
| 08 - Monitoring & Insights | `labs/08-monitoring-insights.ipynb` | Created |

All notebooks follow the same structure:
- Business context header with exam domain, key skills, time, and cost
- Incremental build — each lab extends the previous one
- ChatAgent interface used from Lab 03 onward (required for Model Serving)
- MLflow logging throughout

### The Product

The analyzer scores S-1 filing clarity on a 1–100 scale using LLM-as-judge, batch-processes all 25 filings with `ai_query()`, and joins clarity scores against stock return data. The signature query:

```sql
SELECT company, ticker, clarity_score, six_month_return
FROM ipo_analyzer.default.clarity_scores
JOIN ipo_analyzer.default.stock_returns USING (ticker)
WHERE sector = 'Technology'
ORDER BY six_month_return DESC
LIMIT 10;
```

## Next Steps

1. Run the setup script to create the `ipo_analyzer` catalog and load data:
   ```bash
   python scripts/setup-catalog.py
   ```
2. Upload notebooks from `labs/` to the Databricks workspace.
3. Test sequentially: Lab 01 through Lab 08. Each lab depends on the previous.
4. Verify the signature query runs correctly in Lab 07.
5. Merge `feature/ipo-analyzer-redesign` → `main` when testing passes.

## Workspace Needs

| Resource | Notes |
|---|---|
| Catalog | `ipo_analyzer` (created by setup script) |
| Schema | `ipo_analyzer.default` |
| Vector Search endpoint | ~$0.50-1.00/hr; created in Lab 01, needed through Lab 07 |
| S-1 filings | ~22 filings downloaded via `sec-edgar-downloader` |
| Stock data | Loaded from `yfinance` in setup script |
| Model Serving endpoint | Created in Lab 07, used in Lab 08 |

## Available LLM Endpoints

All labs use `databricks-llama-4-maverick` (best for tool calling). These are all accessible on the trial workspace:

- `databricks-llama-4-maverick` — primary endpoint, used everywhere
- `databricks-meta-llama-3-3-70b-instruct` — fallback if maverick is unavailable
- `databricks-meta-llama-3-1-8b-instruct` — cheap option for simple summarization tasks

## Branch State

All 8 notebooks and updated documentation are committed on `feature/ipo-analyzer-redesign`. The branch is ahead of `main` (which still has the old 10-lab arXiv structure). Do not merge until end-to-end testing on the workspace passes.
