# Handoff Note — Phase 2 Testing

**Date:** 2026-04-03
**Repo:** `/tmp/databricks-genai-lab-guide` (also on GitHub: btriani/databricks-genai-lab-guide)
**Databricks creds:** `/tmp/.databricks-env` (HOST + TOKEN)
**Workspace notebooks:** `/Users/btriani@gmail.com/genai-lab-guide/`

## Current Test Results

| Lab | Status | Notes |
|-----|--------|-------|
| 01 - Document Parsing & Chunking | PASS | Uses SQL for VARIANT types, collect-to-driver for chunking |
| 02 - Vector Search & Retrieval | PASS | VS endpoint already exists, index synced |
| 03 - Building a Retrieval Agent | PASS | Uses langgraph create_react_agent, params-only MLflow logging |
| 04 - UC Functions as Agent Tools | PASS | SQL CONCAT format_citation, DROP before CREATE |
| 05 - Single Agent with LangChain | FAIL | ChatAgent signature= param must be removed, uuid needed for message IDs |
| 06 - Tracing & Reproducible Agents | FAIL | autolog() log_models param removed; needs full retest |
| 07 - Guardrails & Governance | FAIL | databricks-connect serverless error; needs agent rebuild review |
| 08 - Evaluation & LLM-as-Judge | NOT TESTED | Depends on Labs 03-07 being clean |
| 09 - Deployment & Model Serving | NOT TESTED | Depends on a registered model from Lab 05 |
| 10 - Monitoring & Observability | NOT TESTED | Depends on serving endpoint from Lab 09 |

## Critical Issues Found and Fixed

1. **langchain 1.2.14** — `AgentExecutor` and `create_tool_calling_agent` removed. Fixed: use `langgraph.prebuilt.create_react_agent`
2. **VARIANT type** — `ai_parse_document()` returns VARIANT, not displayable via DataFrame API. Fixed: save to table, query via SQL
3. **MLflow models-from-code** — `mlflow.langchain.log_model(lc_model=object)` no longer works. Fixed: use `mlflow.pyfunc.log_model` with ChatAgent
4. **ChatAgentMessage requires id** — Pydantic validation now requires `id=str(uuid.uuid4())`
5. **ChatAgent sets own signature** — Remove `signature=` from `log_model()` calls
6. **UC function type mismatch** — Can't replace Python UDF with SQL function. Fixed: DROP first
7. **autolog() API change** — `log_models` parameter removed

## What Needs To Be Done

### Priority 1: Research before coding
Before fixing more notebooks, research the CURRENT APIs:
- `langgraph.prebuilt.create_react_agent` — exact parameters, invoke format
- `mlflow.pyfunc.log_model` with ChatAgent — what params are allowed
- `mlflow.langchain.autolog` — current valid parameters
- `databricks.agents` vs `mlflow.pyfunc` ChatAgent — which to use
- `unitycatalog-langchain` UCFunctionToolkit — current constructor params

### Priority 2: Fix and test Labs 05-10
- Lab 05: Remove signature=, add uuid to ChatAgentMessage, retest
- Lab 06: Fix autolog, ensure agent rebuild matches Lab 03 pattern
- Lab 07: Fix serverless compat, ensure no databricks-connect dependency
- Lab 08: Test after 05-07 pass (needs registered model)
- Lab 09: Test after 08 passes (needs model in UC registry)
- Lab 10: Test after 09 passes (needs serving endpoint)

### Priority 3: Remove cost profile
- Strip `COST_PROFILE`, `_LLM_ENDPOINTS` dict from ALL notebooks
- Use `databricks-llama-4-maverick` for agent tasks
- Use `databricks-meta-llama-3-1-8b-instruct` for simple tasks (Lab 01 cleaning)
- Update COST-GUIDE.md, cheatsheets to reflect single model choice

### Priority 4: Faster testing
Instead of submitting full notebooks as serverless jobs (~5 min each):
- Use SQL warehouse for SQL-heavy operations (instant)
- Use Command Execution API on an interactive cluster for Python
- Or create a single test notebook that runs key operations from all labs

### Priority 5: Push to GitHub
Commit all fixes and push to main.

## Workspace State
- Catalog: `genai_lab_guide` with schema `default`
- Volume: `genai_lab_guide.default.arxiv_papers` — 8 papers uploaded
- Table: `genai_lab_guide.default.arxiv_chunks` — chunks from Lab 01
- Table: `genai_lab_guide.default.parsed_docs` — parsed documents from Lab 01
- VS Endpoint: `genai_lab_guide_vs_endpoint` (ONLINE)
- VS Index: `genai_lab_guide.default.arxiv_chunks_index` (synced)
- UC Functions: `get_paper_metadata` (SQL), `format_citation` (SQL CONCAT)
- No serving endpoints deployed yet
- No models registered in UC yet

## Available LLM Endpoints (accessible on trial)
- `databricks-llama-4-maverick` — best for tool calling (recommended)
- `databricks-meta-llama-3-3-70b-instruct` — good but sometimes misfires on tools
- `databricks-meta-llama-3-1-8b-instruct` — cheap, good for simple tasks
- `databricks-qwen3-next-80b-a3b-instruct` — large, capable
- `databricks-gpt-5-*` — all return 403 (trial restriction)
