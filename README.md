# IPO Filing Analyzer — Databricks GenAI Lab Guide

Hands-on lab series for the **Databricks Generative AI Engineer Associate** certification. You build one coherent product across 8 labs: an analyzer that scores S-1 filing clarity, deploys as a REST API, and correlates messaging quality with post-IPO stock performance.

## The Product

Equity analysts at a fund have a hypothesis: companies that can't explain themselves clearly in their S-1 filing tend to underperform. The IPO Filing Analyzer tests that hypothesis at scale — scoring 25 filings with an LLM-as-judge engine, batch-processing them with `ai_query()`, and joining clarity scores against stock return data in a single SQL statement.

**The signature query the whole series builds toward:**

```sql
SELECT company, ticker, clarity_score, six_month_return
FROM ipo_analyzer.default.clarity_scores
JOIN ipo_analyzer.default.stock_returns USING (ticker)
WHERE sector = 'Technology'
ORDER BY six_month_return DESC
LIMIT 10;
```

*"Show me the clarity scores of the top 10 performing tech IPO stocks."*

## Why Databricks — and Not Just ChatGPT?

|  | ChatGPT / Claude | What you're building |
|---|---|---|
| What is it? | Consumer tool — each user has a login | Product — end users interact with your API |
| Who pays? | Each user pays OpenAI/Anthropic | You pay for infra, users pay you |
| Scales how? | One user, one chat window | One endpoint, 10,000 users |
| Batch processing? | Upload one filing manually | `ai_query()` scores all filings in one SQL statement |
| Cross-data queries? | Can't join text against stock prices | SQL join: clarity scores + stock returns |

ChatGPT is a great tool for exploration. Databricks is where you build a product that can run in production, serve many users, and query across data sources — all governed by Unity Catalog.

## The 8 Labs

| # | Title | What It Builds | Business Outcome |
|---|-------|---------------|-----------------|
| 01 | [Data Pipeline](labs/01-data-pipeline.ipynb) | Parse S-1 filings, load stock data, create Vector Search index | Unified data foundation — filings and returns in one catalog |
| 02 | [IPO Research Agent](labs/02-ipo-research-agent.ipynb) | RAG agent with retrieval + UC function tools | Analysts can ask: "What did Snowflake say about competition, and how did SNOW perform?" |
| 03 | [Clarity Scoring Engine](labs/03-clarity-scoring-engine.ipynb) | LLM-as-judge scorer registered as ChatAgent in UC | Each S-1 section gets a 1–100 clarity score |
| 04 | [Tracing & Reproducibility](labs/04-tracing-reproducibility.ipynb) | MLflow autologging, span tagging, rubric versioning | Every score is auditable: "Why did Coinbase get a 43?" |
| 05 | [Guardrails & Compliance](labs/05-guardrails-compliance.ipynb) | PII detection, topic classifier, AI Gateway policy | Legal sign-off: no investment advice, no PII leaks, mandatory disclaimers |
| 06 | [Evaluation & Batch Scoring](labs/06-evaluation-batch-scoring.ipynb) | `mlflow.evaluate`, batch `ai_query()` over all 25 filings | Formal quality score + populated `clarity_scores` table |
| 07 | [Deployment](labs/07-deployment.ipynb) | Model Serving endpoint, REST API, signature query | Analyzer is live; signature query returns first results |
| 08 | [Monitoring & Insights](labs/08-monitoring-insights.ipynb) | Inference table logging, Lakehouse Monitor, drift detection | Correlation answer: does clarity predict returns? |

**Total estimated cost: ~$12-19** | **Total time: ~4.5 hours**

## Prerequisites

See [prerequisites.md](prerequisites.md) for full setup details.

**Summary:** Databricks pay-as-you-go workspace, Foundation Model APIs enabled, Python 3.10+.

## Quick Start

1. Run the setup script (creates catalog, schema, volumes, loads ~22 S-1 filings):
   ```bash
   python scripts/setup-catalog.py
   ```
2. Upload the notebooks in `labs/` to your Databricks workspace.
3. Open Lab 01 and run cells top-to-bottom.
4. Continue through Lab 08 sequentially — each lab depends on the previous.

## Exam Domain Coverage

| Domain | Weight | Labs |
|--------|--------|------|
| Application Development | 30% | Lab 02, 03, 04 |
| Assembling and Deploying Apps | 22% | Lab 07, 08 |
| Data Preparation | 14% | Lab 01 |
| Design Applications | 14% | Concepts woven throughout every lab |
| Evaluation and Monitoring | 12% | Lab 06, 08 |
| Governance | 8% | Lab 05 |

## Cost

~$12-19 total across all labs. The only resource that bills continuously is the Vector Search endpoint (~$0.50-1.00/hr) — delete it when not actively working, and recreate it when you resume. Everything else is pay-per-use.

Run the cleanup script when you're done:
```bash
python scripts/cleanup.py
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup-catalog.py` | Create Unity Catalog objects, load S-1 filings and stock data |
| `scripts/cleanup.py` | Delete all Databricks resources when done |

## Official Databricks Resources

- [Generative AI Engineer Associate Exam Page](https://www.databricks.com/learn/certification/genai-engineer-associate)
- [Databricks GenAI Documentation](https://docs.databricks.com/aws/en/generative-ai/guide)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [LangChain + Databricks](https://python.langchain.com/docs/integrations/providers/databricks/)

## License

[MIT](LICENSE)
