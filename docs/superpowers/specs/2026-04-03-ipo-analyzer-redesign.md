# Design Spec: IPO Filing Analyzer — Lab Redesign

**Date:** 2026-04-03
**Author:** Bruno Triani + Claude
**Status:** Draft — awaiting review

---

## 1. Product Vision

An IPO Filing Analyzer that scores the messaging clarity of tech company S-1 filings and correlates those scores with first-year stock performance. Built on Databricks, deployed as a REST API, monitored in production.

**The "why not ChatGPT?" answer:** You could analyze one S-1 with ChatGPT. But scoring 25+ filings with a versioned rubric, joining clarity scores against stock returns in a governed Delta table, serving the results via API, and monitoring scoring drift — that's a data platform problem.

**Signature query the system must handle:**
> "Show me the clarity scores of the top 10 performing tech IPO stocks in their first year."

This query requires: pre-computed clarity scores (batch LLM-as-judge) + stock returns table (structured data) + SQL join + ranked output. No chat tool can do it.

---

## 2. Data

### 2.1 S-1 Filings (Unstructured)

- **Source:** SEC EDGAR FULL-TEXT search API (efts.sec.gov)
- **Scope:** ~25-30 tech IPOs from 2019-2024
- **Format:** HTML filings from EDGAR, converted to PDF during setup, stored in a UC Volume
- **Candidate companies:** Snowflake, Palantir, DoorDash, Coinbase, Rivian, Unity, Roblox, Bumble, Affirm, Robinhood, Toast, Confluent, GitLab, HashiCorp, Braze, Couchbase, ForgeRock, Sweetgreen, Duolingo, Instacart, Klaviyo, Arm Holdings, Birkenstock, Reddit, Astera Labs, Rubrik, Ibotta

### 2.2 Stock Performance (Structured)

- **Source:** Yahoo Finance (yfinance Python library, free)
- **Metrics per company:**
  - Ticker symbol
  - IPO date
  - IPO price
  - Price at 3, 6, 12 months post-IPO
  - 12-month return (%)
  - S&P 500 return over same period (for relative comparison)
  - Sector/sub-sector
- **Format:** Delta table in Unity Catalog, pre-loaded during setup
- **Table:** `ipo_analyzer.default.stock_performance`

### 2.3 Clarity Scores (AI-Generated, Structured)

- **Generated in:** Lab 08 (batch scoring with `ai_query()`)
- **Scores per filing section:**
  - Business description clarity (1-100)
  - Risk factors clarity (1-100)
  - Competitive landscape clarity (1-100)
  - Revenue model clarity (1-100)
  - Overall clarity (weighted average)
- **Table:** `ipo_analyzer.default.clarity_scores`
- **Each row:** company, section, score, plain-English justification

---

## 3. Architecture

```
Setup Script
  └── Download S-1 filings from EDGAR → UC Volume
  └── Download stock data via yfinance → stock_performance Delta table

Lab 01: Parse & Chunk
  S-1 files (Volume) → ai_parse_document() → parsed_filings table
  parsed_filings → element extraction → chunking → ipo_filing_chunks table (with CDF)

Lab 02: Vector Search
  ipo_filing_chunks → Delta Sync Index (managed embeddings, databricks-bge-large-en)
  VS Endpoint: ipo_analyzer_vs_endpoint

Lab 03: Q&A Agent
  Vector Search + ChatDatabricks → ReAct agent
  "What are Snowflake's key risk factors?" → grounded answer with source citations

Lab 04: UC Functions as Tools
  get_filing_metadata(company) → SQL UDF over ipo_filing_chunks (section counts, filing size)
  get_stock_performance(ticker) → SQL UDF over stock_performance table
  format_comparison(ticker1, ticker2) → SQL UDF joining stock + filing data

Lab 05: Clarity Scorer + ChatAgent
  score_clarity(text, section_type) → LLM-as-judge with rubric (UC function wrapping ai_query)
  Intent routing: RESEARCH / STOCK_LOOKUP / CLARITY_SCORE / COMPARISON
  ArxivResearchAgent → IpoAnalyzerAgent (ChatAgent)
  Register in UC: ipo_analyzer.default.ipo_filing_agent

Lab 06: Tracing & Reproducibility
  MLflow tracing on all agent invocations
  Tags: rubric_version, llm_endpoint, scoring_model, chunk_size
  Compare rubric v1 vs v2 scoring consistency

Lab 07: Guardrails
  Contextual: Only IPO/financial analysis questions (not investment advice)
  Safety: PII detection + mandatory disclaimer ("This is not investment advice")
  Adversarial test suite: off-topic, PII, jailbreak, "should I buy this stock?"

Lab 08: Evaluation + Batch Scoring
  Evaluate agent Q&A quality (relevance, groundedness, citation quality)
  Batch-score ALL filings: ai_query() across ipo_filing_chunks → clarity_scores table
  Custom LLM-as-judge metric: clarity rubric (1-100 per section)

Lab 09: Deployment
  Deploy ChatAgent as Model Serving endpoint
  Test via REST API
  Batch inference: ai_query() over stock_performance joined with clarity_scores
  The signature query: "top 10 performing stocks with their clarity scores"

Lab 10: Monitoring
  Inference tables on the serving endpoint
  Lakehouse Monitor for scoring drift
  Feedback loop: monitor → re-evaluate → improve rubric → redeploy
  Final correlation analysis: clarity vs performance scatter/table
```

---

## 4. Shared Utilities (`shared/lab_utils.py`)

```python
def build_agent(llm_endpoint, catalog, schema):
    """Connect to existing workspace resources and assemble the IPO analyzer agent.
    
    Returns (agent, tools, llm) by:
    - Connecting to the Vector Search index (not recreating it)
    - Loading UC function tools via UCFunctionToolkit
    - Creating a ReAct agent with intent-routing system prompt
    
    Takes ~3-5 seconds. No data is recreated.
    """

def get_vs_index(catalog, schema):
    """Return a VectorSearchClient index for direct retrieval queries."""

def get_scorecard(catalog, schema):
    """Run standard test queries and return a progress summary dict.
    
    Test queries (consistent across all labs):
    - 5 Q&A questions about S-1 filings
    - 4 adversarial queries (off-topic, PII, investment advice, jailbreak)
    - 1 cross-cutting query (the signature query)
    
    Returns dict with: answers_correct, adversarial_blocked, 
    clarity_score_available, stock_lookup_works, signature_query_works
    """
```

---

## 5. Notebook Structure (each lab)

Each notebook follows this template:

### Opening (2 cells)
```
[Markdown] Business Context
  "The team needs X. Today the system can do Y. After this lab, it will do Z."
  Includes a concrete before/after example.

[Code] Setup
  %pip install ... --quiet
  dbutils.library.restartPython()
  from shared.lab_utils import build_agent  # where applicable
```

### Teaching Content (60-70% of cells)
New concepts only. Each code cell has a clear purpose visible in its output. No dead boilerplate.

### Before/After Demo (1-2 cells)
```
[Code] Concrete demonstration
  Runs the same query/scenario with and without the lab's addition.
  E.g., Lab 07: same 4 queries with guardrails ON vs OFF → side-by-side table.
```

### Running Scorecard (1 cell)
```
[Code] Cumulative progress check
  from shared.lab_utils import get_scorecard
  scorecard = get_scorecard("ipo_analyzer", "default")
  # Prints: "Agent: 4/5 Q&A correct | 3/4 adversarial blocked | 
  #          Clarity scoring: available | Stock lookup: available |
  #          Signature query: PASS"
```

### Exam Prep (collapsed section at end)
```
[Markdown] --- Exam Preparation ---
  Key Concepts table
  5 multiple-choice practice questions with answers
  Cost breakdown
```

---

## 6. Before/After Demos Per Lab

| Lab | Before | After | Demo |
|---|---|---|---|
| **01** | S-1 filings as PDFs in a volume | Searchable chunks in Delta | Show a parsed section vs raw PDF text side by side |
| **02** | Chunks in a table (full scan) | Instant semantic retrieval | Same query: SQL LIKE scan (slow, misses synonyms) vs Vector Search (fast, semantic) |
| **03** | Raw retrieved passages | Agent-synthesised answer | Show passages alone vs agent answer with citations |
| **04** | Agent can only search text | Agent answers structured questions | "How many chunks for Snowflake?" — fails before, works after |
| **05** | Notebook-only agent | Registered model + intent routing | Same 3 queries: routed by intent, wrapped in ChatAgent, ready to deploy |
| **06** | Agent runs, no visibility | Full trace with spans and timing | Show trace tree: LLM call (200ms) → tool call (150ms) → retrieval (80ms) |
| **07** | Agent answers anything | Agent blocks off-topic + PII | "Should I buy SNOW stock?" — answered before, blocked after. "My SSN is 123-45-6789" — blocked. |
| **08** | "It seems good" (vibes) | Quantified: relevance 4.2/5, clarity consistency 87% | Eval table showing per-question scores. Batch clarity scores across all filings. |
| **09** | Notebook-only | REST API endpoint | `curl` the endpoint. `ai_query()` batch scoring from SQL. |
| **10** | Deployed but blind | Full monitoring + correlation analysis | Dashboard showing scoring drift. **The signature query:** top 10 stocks with clarity scores. |

---

## 7. The Signature Query

Lab 10 culminates with the query that proves the whole pipeline works:

> "Show me the clarity scores of the top 10 performing tech IPO stocks in their first year."

The agent handles this by calling `query_scored_database`, which executes:

```sql
SELECT 
    s.company,
    s.ticker,
    s.ipo_date,
    s.twelve_month_return_pct,
    c.business_clarity,
    c.risk_factors_clarity,
    c.competitive_clarity,
    c.revenue_model_clarity,
    c.overall_clarity
FROM ipo_analyzer.default.stock_performance s
JOIN ipo_analyzer.default.clarity_scores c 
    ON s.company = c.company
ORDER BY s.twelve_month_return_pct DESC
LIMIT 10
```

The student sees a table like:

| Company | Ticker | 12mo Return | Business Clarity | Risk Clarity | Overall |
|---|---|---|---|---|---|
| Snowflake | SNOW | +112% | 78 | 65 | 72 |
| DoorDash | DASH | +89% | 82 | 71 | 76 |
| ... | ... | ... | ... | ... | ... |

Then the student can explore: "Now show me the bottom 10." Compare. Draw conclusions. Is there a pattern?

---

## 8. Catalog & Naming

| Resource | Name |
|---|---|
| Catalog | `ipo_analyzer` |
| Schema | `default` |
| Volume | `ipo_analyzer.default.sec_filings` |
| Parsed table | `ipo_analyzer.default.parsed_filings` |
| Chunks table | `ipo_analyzer.default.filing_chunks` |
| Stock table | `ipo_analyzer.default.stock_performance` |
| Clarity scores | `ipo_analyzer.default.clarity_scores` |
| VS Endpoint | `ipo_analyzer_vs_endpoint` |
| VS Index | `ipo_analyzer.default.filing_chunks_index` |
| UC Functions | `get_filing_metadata`, `get_stock_performance`, `format_comparison`, `score_clarity`, `query_scored_database` |
| Registered model | `ipo_analyzer.default.ipo_filing_agent` |
| Serving endpoint | `ipo-analyzer-endpoint` |
| MLflow experiments | `/Users/{username}/ipo-analyzer/lab-XX-...` |

---

## 9. Setup Script (`scripts/setup-catalog.py`)

Pre-lab setup downloads data and creates catalog resources:

1. Download ~25-30 S-1 filings from SEC EDGAR API
2. Download stock price data via yfinance for each company
3. Create catalog `ipo_analyzer`, schema `default`, volume `sec_filings`
4. Upload S-1 files to volume
5. Write stock performance data to `stock_performance` Delta table

Estimated setup time: ~5 minutes
Estimated setup cost: ~$0 (EDGAR and yfinance are free)

---

## 10. Cost Estimate (Full Lab Sequence)

| Resource | Usage | Est. Cost |
|---|---|---|
| Serverless compute | ~4 hours total across all labs | ~$5-8 |
| LLM tokens (agent queries) | ~200 queries across labs | ~$2-3 |
| LLM tokens (batch scoring) | ~25 filings x 4 sections x scoring prompt | ~$3-5 |
| Vector Search endpoint | ~4 hours runtime | ~$2-4 |
| Model Serving endpoint | ~1 hour (Labs 09-10) | ~$1-2 |
| **Total** | | **~$13-22** |

---

## 11. EU AI Act Framing

The "not investment advice" guardrail in Lab 07 ties to a real regulatory context:

- Under the **EU AI Act**, an AI system that influences financial decisions could be classified as **high-risk** (Annex III, Section 5b: "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score")
- Even if the IPO analyzer is informational, deploying it without guardrails and audit logging creates regulatory exposure
- The labs progressively build every compliance requirement: audit trail (Lab 06), guardrails (Lab 07), evaluation (Lab 08), monitoring (Lab 10)

This framing makes governance labs feel necessary, not bureaucratic.

---

## 12. Exam Domain Coverage

| Exam Domain | % of Exam | Covered In |
|---|---|---|
| Data Preparation | 14% | Labs 01-02 (parsing, chunking, embeddings, Delta Sync) |
| Application Development | 30% | Labs 03-05 (RAG, tool calling, agents, ChatAgent, intent routing) |
| Governance | 8% | Lab 07 (guardrails, data licensing, AI Gateway) + Lab 06 (reproducibility) |
| Evaluation & Monitoring | 12% | Labs 08, 10 (LLM-as-judge, custom metrics, drift detection) |
| Assembling & Deploying | 22% | Labs 09-10 (serving, A/B testing, batch inference, monitoring) |
| GenAI Fundamentals | 14% | Throughout (embeddings, tokenization, prompt engineering) |
| **Total** | **100%** | **All domains covered** |

---

## 13. Resolved Design Decisions

1. **EDGAR format (HTML vs PDF):** S-1 filings on EDGAR are HTML. We convert to PDF during setup (using `weasyprint` or `pdfkit`) so Lab 01 can use `ai_parse_document()` — which is an exam topic. The setup script handles the HTML→PDF conversion; students work with PDFs in the volume. This matches real-world pipelines where documents arrive in mixed formats.
2. **Stock data freshness:** Include only companies with complete 12-month post-IPO data. This means the latest IPOs included will be from early 2025. Companies with less than 12 months of data are excluded from the dataset.
3. **Clarity rubric:** Pre-defined in the spec (see Section 14 below). Students use rubric v1 in Lab 05, then modify it in Lab 06 to demonstrate version comparison.
4. **Catalog name:** New catalog `ipo_analyzer` — clean separation from the old `genai_lab_guide` labs. Students create it during setup.
5. **`query_scored_database` tool:** Implemented as a UC SQL function that accepts a natural-language-to-SQL intent (e.g., "top 10 by return with clarity") and runs a parameterized query against the joined `stock_performance` + `clarity_scores` tables. Listed in Section 8 UC Functions.

---

## 14. Clarity Scoring Rubric (v1)

Used by the `score_clarity` UC function (Lab 05) and batch scoring (Lab 08):

```
Score 1-20:  Impenetrable. Dense jargon, circular definitions, no concrete specifics.
             A reader cannot explain what the company does after reading this section.
Score 21-40: Unclear. Heavy jargon with occasional concrete details. A domain expert
             could piece it together, but a general investor would struggle.
Score 41-60: Adequate. The core message is present but buried in boilerplate.
             Key details (numbers, timelines, specifics) are sparse.
Score 61-80: Clear. A general investor can understand the main point. Concrete
             details are present. Some jargon remains but doesn't obscure meaning.
Score 81-100: Exceptional. Plain language, specific numbers, clear cause-and-effect.
              A non-expert could explain this section to someone else accurately.
```

Four section types are scored independently:
- **Business Description:** What does the company do? For whom? How do they make money?
- **Risk Factors:** Are the risks specific to this company, or generic boilerplate?
- **Competitive Landscape:** Does the filing name competitors and explain differentiation?
- **Revenue Model:** Is the revenue breakdown clear (segments, growth drivers, unit economics)?
