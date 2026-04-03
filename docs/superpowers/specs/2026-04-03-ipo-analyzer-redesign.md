# Design Spec: IPO Filing Analyzer — Lab Redesign

**Date:** 2026-04-03
**Author:** Bruno Triani + Claude
**Status:** Draft — awaiting review

---

## 1. Product Vision

An IPO Filing Analyzer that scores the messaging clarity of tech company S-1 filings and correlates those scores with first-year stock performance. Built on Databricks, deployed as a REST API, monitored in production.

**You're building a product, not giving people a chatbot login.** End users never touch Databricks, ChatGPT, or any AI tool directly. They interact with a finished system — an API, an app, a dashboard. The Databricks infrastructure is invisible to them.

**Signature query the system must handle:**
> "Show me the clarity scores of the top 10 performing tech IPO stocks in their first year."

This query requires: pre-computed clarity scores (batch LLM-as-judge) + stock returns table (structured data) + SQL join + ranked output. No chat tool can do it.

---

## 2. Why Databricks (Not ChatGPT / Claude + MCP)

The comparison isn't "Databricks vs ChatGPT for answering questions." It's: **you're building a product. ChatGPT and Claude are consumer tools, not product infrastructure.**

|  | ChatGPT / Claude + MCP | What you're building |
|---|---|---|
| **What is it?** | A consumer tool. Each user has a login and asks questions. | A product. End users interact with your app/API. They don't know Databricks exists. |
| **Who pays?** | Each user pays OpenAI/Anthropic directly for their own seat | You pay for infrastructure. Users pay you (or access it internally). |
| **Who controls it?** | OpenAI/Anthropic control the model, data retention, terms of service | You control everything — model choice, data, guardrails, logging |
| **Data stays where?** | On OpenAI/Anthropic's servers. You hope their privacy policy holds. | In your cloud VPC. Unity Catalog governance. Your audit trail. |
| **Scales how?** | One user, one chat window. 10 users = 10 subscriptions asking the same questions. | One endpoint. 10 or 10,000 users. Same infrastructure. |
| **Reproducible?** | User got a great answer last Tuesday. Can you recreate it? No. | Every query logged. Every model version tracked. Every scoring rubric versioned. |
| **Batch processing?** | Upload one filing, ask one question. Repeat 25 times manually. | `ai_query()` scores all 25 filings in one SQL statement. |
| **Cross-data queries?** | Can't join S-1 text against stock prices at scale. | SQL join: clarity scores + stock returns + filing chunks. Native. |

**The narrative line:** "Anyone can ask ChatGPT about one S-1 filing. You're building a system that scores every tech IPO filing, correlates clarity with stock performance, serves it via API, and proves it works — with guardrails, versioning, and monitoring. That's a product, not a chat session."

---

## 3. Data

### 3.1 S-1 Filings (Unstructured)

- **Source:** SEC EDGAR FULL-TEXT search API (efts.sec.gov)
- **Scope:** ~25-30 tech IPOs from 2019-2024
- **Format:** HTML filings from EDGAR, converted to PDF during setup, stored in a UC Volume
- **Candidate companies:** Snowflake, Palantir, DoorDash, Coinbase, Rivian, Unity, Roblox, Bumble, Affirm, Robinhood, Toast, Confluent, GitLab, HashiCorp, Braze, Couchbase, ForgeRock, Sweetgreen, Duolingo, Instacart, Klaviyo, Arm Holdings, Birkenstock, Reddit, Astera Labs, Rubrik, Ibotta

### 3.2 Stock Performance (Structured)

- **Source:** Yahoo Finance (yfinance Python library, free)
- **Loaded in:** Lab 01, Section B (students see the ingestion, not hidden in setup)
- **Metrics per company:**
  - Ticker symbol
  - IPO date
  - IPO price
  - Price at 3, 6, 12 months post-IPO
  - 12-month return (%)
  - S&P 500 return over same period (for relative comparison)
  - Sector/sub-sector
- **Table:** `ipo_analyzer.default.stock_performance`

### 3.3 Clarity Scores (AI-Generated, Structured)

- **Generated in:** Lab 06 (batch scoring with `ai_query()`)
- **Scores per filing section:**
  - Business description clarity (1-100)
  - Risk factors clarity (1-100)
  - Competitive landscape clarity (1-100)
  - Revenue model clarity (1-100)
  - Overall clarity (weighted average)
- **Table:** `ipo_analyzer.default.clarity_scores`
- **Each row:** company, section, score, plain-English justification

---

## 4. Architecture (8 Labs)

```
Setup Script
  └── Download S-1 filings from EDGAR (HTML → PDF conversion)
  └── Create catalog, schema, volume
  └── Upload PDFs to volume

Lab 01: Data Pipeline
  Section A: Parse S-1 filings
    S-1 PDFs (Volume) → ai_parse_document() → parsed_filings table
  Section B: Load stock performance data
    yfinance API → IPO prices + 12-month returns → stock_performance Delta table
  Section C: Extract text and chunk
    parsed_filings → element extraction → chunking → filing_chunks table (with CDF)
  Section D: Create Vector Search index
    filing_chunks → Delta Sync Index (managed embeddings, databricks-bge-large-en)
    VS Endpoint: ipo_analyzer_vs_endpoint
  Business outcome: "All 25 filings and their stock performance are searchable and queryable"

Lab 02: IPO Research Agent
  Section A: Build retrieval tool (Vector Search)
  Section B: Create UC functions
    get_filing_metadata(company) → SQL UDF over filing_chunks
    get_stock_performance(ticker) → SQL UDF over stock_performance table
  Section C: Build multi-tool ReAct agent
  Business outcome: First real query — "What did Snowflake say about competition,
                     and how did the stock do?" Agent answers with citations + data.

Lab 03: Clarity Scoring Engine
  Section A: Design clarity scoring rubric (LLM-as-judge)
  Section B: Create score_clarity UC function wrapping ai_query
  Section C: Intent routing (RESEARCH / STOCK_LOOKUP / CLARITY_SCORE / COMPARISON)
  Section D: Wrap in ChatAgent + register in UC
  Business outcome: Score any S-1 section on demand. Agent handles research,
                     stock, AND scoring queries. Registered model ready to deploy.

Lab 04: Tracing & Reproducibility
  Section A: Enable MLflow tracing (autolog)
  Section B: Tag runs for reproducibility (rubric_version, llm_endpoint, etc.)
  Section C: Modify rubric → v2, compare scoring consistency across versions
  Business outcome: "We can prove why the scorer gave Coinbase a 43 on risk
                     factor clarity, and compare how rubric v1 vs v2 score differently."

Lab 05: Guardrails & Compliance
  Section A: Contextual guardrail — only IPO/financial analysis (not investment advice)
  Section B: Safety guardrail — PII detection + mandatory disclaimer
  Section C: Adversarial test suite (off-topic, PII, jailbreak, "should I buy SNOW?")
  Section D: AI Gateway configuration (infrastructure-level enforcement)
  Business outcome: "Legal signed off. The system blocks investment advice requests
                     and never leaks PII. 8/8 adversarial tests pass."

Lab 06: Evaluation & Batch Scoring
  Section A: Evaluate agent Q&A quality (relevance, groundedness, citation quality)
  Section B: Custom LLM-as-judge metric for clarity scoring consistency
  Section C: Batch-score ALL filings — ai_query() across filing_chunks → clarity_scores table
  Section D: Preview: clarity scores vs stock performance (first cross-reference)
  Business outcome: "The full clarity scores database exists. We can see that
                     Snowflake scored 78 on business clarity and returned +112%."

Lab 07: Deployment
  Section A: Deploy ChatAgent as Model Serving endpoint
  Section B: Test via REST API
  Section C: A/B testing with traffic split (rubric v1 vs v2)
  Section D: Batch inference — ai_query() over joined stock + clarity data
  Section E: The signature query via the deployed endpoint
  Business outcome: "Top 10 performing stocks with their clarity scores" — served via API.

Lab 08: Monitoring & Insights
  Section A: Enable inference tables (auto_capture_config)
  Section B: Generate traffic (send representative queries)
  Section C: Create Lakehouse Monitor for scoring drift
  Section D: Final correlation analysis — clarity vs stock performance
  Section E: The feedback loop (monitor → re-evaluate → improve → redeploy)
  Business outcome: "Is there a pattern between how clearly a company explains
                     itself and how the stock performs? Here's the data."
```

---

## 5. Shared Utilities (`shared/lab_utils.py`)

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

## 6. Notebook Structure (each lab)

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
  E.g., Lab 05: same 4 queries with guardrails ON vs OFF → side-by-side table.
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

## 7. Before/After Demos Per Lab

| Lab | Before | After | Demo |
|---|---|---|---|
| **01** | S-1 PDFs in a volume + stock data on Yahoo Finance | Searchable chunks + stock_performance table + VS index | Query: "Find sections about competition" — SQL LIKE (slow, misses synonyms) vs Vector Search (fast, semantic). Preview stock returns alongside chunk counts. |
| **02** | Retrieved passages + stock table, but no agent | Agent answers cross-data questions | "What did Snowflake say about competition, and how did SNOW perform?" — fails before (no agent), works after (grounded answer + stock data). |
| **03** | Agent can answer questions but can't score clarity | Agent scores any section 1-100 with justification | "Score Coinbase's risk factors for clarity" — fails before, returns "43/100: Heavy jargon, generic risks..." after. |
| **04** | Agent works but no visibility into decisions | Full trace with spans, timing, and rubric version tags | Show trace tree: LLM call (200ms) → tool call (150ms) → retrieval (80ms). Compare rubric v1 vs v2 scores. |
| **05** | Agent answers anything, including "should I buy SNOW?" | Blocks off-topic + PII, adds disclaimer | "Should I buy SNOW stock?" — answered before, blocked after. "My SSN is 123-45-6789" — blocked. |
| **06** | "The scorer seems good" (vibes) | Quantified: relevance 4.2/5, clarity consistency 87%. Full clarity_scores table. | Eval table + first preview: Snowflake (78 clarity, +112% return) vs Coinbase (43 clarity, -75% return). |
| **07** | Notebook-only agent | REST API endpoint + batch results | `curl` the endpoint. The signature query: "Top 10 performing stocks with their clarity scores." |
| **08** | Deployed but blind | Full monitoring + correlation analysis | Scoring drift dashboard. Final insight: "Is there a pattern between clarity and performance?" |

---

## 8. The Signature Query

Lab 07 delivers the signature query via the deployed endpoint, and Lab 08 adds the monitoring and final analysis:

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

## 9. Catalog & Naming

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
| UC Functions | `get_filing_metadata`, `get_stock_performance`, `score_clarity`, `query_scored_database` |
| Registered model | `ipo_analyzer.default.ipo_filing_agent` |
| Serving endpoint | `ipo-analyzer-endpoint` |
| MLflow experiments | `/Users/{username}/ipo-analyzer/lab-XX-...` |

---

## 10. Setup Script (`scripts/setup-catalog.py`)

Pre-lab setup downloads filings and creates catalog resources:

1. Download ~25-30 S-1 filings from SEC EDGAR API (HTML)
2. Convert HTML filings to PDF (using `weasyprint` or `pdfkit`)
3. Create catalog `ipo_analyzer`, schema `default`, volume `sec_filings`
4. Upload PDF files to volume

Stock price data is loaded in **Lab 01, Section B** (not during setup) so students see the full data preparation workflow.

Estimated setup time: ~5 minutes
Estimated setup cost: ~$0 (EDGAR API is free)

---

## 11. Cost Estimate (Full Lab Sequence)

| Resource | Usage | Est. Cost |
|---|---|---|
| Serverless compute | ~3 hours total across all labs | ~$4-6 |
| LLM tokens (agent queries) | ~150 queries across labs | ~$2-3 |
| LLM tokens (batch scoring) | ~25 filings x 4 sections x scoring prompt | ~$3-5 |
| Vector Search endpoint | ~3 hours runtime | ~$1.50-3 |
| Model Serving endpoint | ~1 hour (Labs 07-08) | ~$1-2 |
| **Total** | | **~$12-19** |

---

## 12. EU AI Act Framing

The "not investment advice" guardrail in Lab 05 ties to a real regulatory context:

- Under the **EU AI Act**, an AI system that influences financial decisions could be classified as **high-risk** (Annex III, Section 5b: "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score")
- Even if the IPO analyzer is informational, deploying it without guardrails and audit logging creates regulatory exposure
- The labs progressively build every compliance requirement: audit trail (Lab 04), guardrails (Lab 05), evaluation (Lab 06), monitoring (Lab 08)

This framing makes governance labs feel necessary, not bureaucratic.

---

## 13. Exam Domain Coverage

| Exam Domain | % of Exam | Covered In |
|---|---|---|
| Data Preparation | 14% | Lab 01 (parsing, chunking, embeddings, Delta Sync, structured data ingestion) |
| Application Development | 30% | Labs 02-03 (RAG, tool calling, agents, ChatAgent, intent routing, UC functions) |
| Governance | 8% | Lab 05 (guardrails, data licensing, AI Gateway) + Lab 04 (reproducibility) |
| Evaluation & Monitoring | 12% | Labs 06, 08 (LLM-as-judge, custom metrics, batch scoring, drift detection) |
| Assembling & Deploying | 22% | Labs 07-08 (serving, A/B testing, batch inference, monitoring) |
| GenAI Fundamentals | 14% | Throughout (embeddings, tokenization, prompt engineering) |
| **Total** | **100%** | **All domains covered** |

---

## 14. Resolved Design Decisions

1. **EDGAR format (HTML vs PDF):** S-1 filings on EDGAR are HTML. We convert to PDF during setup (using `weasyprint` or `pdfkit`) so Lab 01 can use `ai_parse_document()` — which is an exam topic. The setup script handles the HTML→PDF conversion; students work with PDFs in the volume. This matches real-world pipelines where documents arrive in mixed formats.
2. **Stock data freshness:** Include only companies with complete 12-month post-IPO data. This means the latest IPOs included will be from early 2025. Companies with less than 12 months of data are excluded from the dataset.
3. **Clarity rubric:** Pre-defined in the spec (see Section 15 below). Students use rubric v1 in Lab 03, then modify it in Lab 04 to demonstrate version comparison.
4. **Catalog name:** New catalog `ipo_analyzer` — clean separation from the old `genai_lab_guide` labs. Students create it during setup.
5. **`query_scored_database` tool:** Implemented as a UC SQL function that accepts a natural-language-to-SQL intent (e.g., "top 10 by return with clarity") and runs a parameterized query against the joined `stock_performance` + `clarity_scores` tables. Listed in Section 9 UC Functions.
6. **8 labs instead of 10:** Compressed parsing + indexing + agent into fewer labs so students reach business value by Lab 02. Infrastructure labs (old Labs 01-03) merged into Lab 01 (data pipeline) and Lab 02 (agent). Every lab from Lab 02 onward answers a business question.
7. **Product framing:** The system is a product, not a chatbot login. End users never touch Databricks. This is the core "why not ChatGPT?" argument — you're building infrastructure for a service, not giving individuals a chat tool.

---

## 15. Clarity Scoring Rubric (v1)

Used by the `score_clarity` UC function (Lab 03) and batch scoring (Lab 06):

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

---

## 16. Business Narrative Arc

**Setting:** You're building an IPO Filing Analyzer for a financial research firm. The firm's analysts currently read S-1 filings manually and form opinions about "how clear is this company's story?" They suspect that companies who can't explain themselves clearly tend to underperform — but they have no data to prove it.

**Three milestones:**

- **Milestone 1 (Labs 01-02):** Working prototype — "Can it answer questions about filings AND pull stock data?"
- **Milestone 2 (Labs 03-05):** Production-ready — "Can it score clarity, prove its reasoning, and pass compliance?"
- **Milestone 3 (Labs 06-08):** Operationalized — "Can we batch-score everything, deploy it, monitor it, and find the pattern?"

**Per-lab business context:**

| Lab | Opening context |
|---|---|
| **01** | The firm has 25 S-1 filings as PDFs and stock return data scattered across Yahoo Finance. Before the analyzer can do anything, both data sources need to be in one place — parsed, chunked, indexed, and queryable. |
| **02** | The data is ready. Now build the research agent — the first version that can answer "What did Snowflake say about competition, and how did SNOW perform?" This is the prototype the analysts will test. |
| **03** | The analysts' core hypothesis is about *clarity*. Build the scoring engine: an LLM-as-judge that rates each S-1 section on a 1-100 clarity scale. Wrap everything in a ChatAgent and register it for deployment. |
| **04** | The CTO asks: "How do we know the scorer is consistent? Can you prove why it gave Coinbase a 43?" Enable tracing, tag every run with the rubric version, and compare scoring consistency across rubric versions. |
| **05** | Before the analyzer goes to clients, legal requires: no investment advice, no PII leaks, and a disclaimer on every response. Add guardrails and run an adversarial test suite. |
| **06** | The VP asks: "Is the agent actually good?" Run a formal evaluation. Then batch-score all 25 filings to populate the clarity database. First preview: does clarity correlate with returns? |
| **07** | Evaluation looks solid. Deploy the agent as a REST API. Run the signature query for the first time: "Top 10 performing stocks with their clarity scores." |
| **08** | The analyzer is live. Now you need to know when it breaks. Enable monitoring, detect drift, and close the feedback loop. Final analysis: is there a pattern between how clearly a company explains itself and how the stock performs? |
