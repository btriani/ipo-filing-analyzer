# Handoff Note — Phase 2 Testing (Updated)

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
| 05 - Single Agent with LangChain | FIXED | Removed unused signature code, added uuid to ChatAgentMessage, ChatAgent auto-infers signature |
| 06 - Tracing & Reproducible Agents | FIXED | Added agent rebuild cell, defined AGENT_VERSION, added UC toolkit to pip install, removed python_model=None log_model |
| 07 - Guardrails & Governance | FIXED | Added agent rebuild cell, added UC toolkit to pip install |
| 08 - Evaluation & LLM-as-Judge | FIXED | Changed model name to `arxiv_chat_agent`, dynamic version discovery |
| 09 - Deployment & Model Serving | FIXED | Changed model name to `arxiv_chat_agent` |
| 10 - Monitoring & Observability | FIXED | Added WorkspaceClient init |

## Test Script

Run `scripts/test-labs.py` for fast validation using the Command Execution API:
```bash
export DATABRICKS_HOST=https://dbc-3cd549f9-402b.cloud.databricks.com
export DATABRICKS_TOKEN=dapi...
python scripts/test-labs.py           # all labs
python scripts/test-labs.py --labs 5 6 7  # specific labs
```

Test results (2026-04-03): Labs 05-07 all code tests PASS. Labs 08-10 have expected sequential dependencies (need model registered from Lab 05 on workspace).

## Fixes Applied

### Lab 05 — Single Agent with LangChain
- Removed unused `ModelSignature`, `Schema`, `ColSpec` imports and `signature` variable from cell-11
- Removed `input_example=` from `log_model()` — ChatAgent provides its own
- Added `langgraph` to pip_requirements
- Added `id=str(uuid.uuid4())` to test `ChatAgentMessage` in cell-09

### Lab 06 — Tracing & Reproducible Agents
- Added agent rebuild cell after cell-03 (tools, LLM, create_react_agent, AGENT_VERSION)
- Added UC toolkit packages to pip install
- Removed `python_model=None` log_model call from cell-11 (was a placeholder that wouldn't work)
- `AGENT_VERSION = "v1"` defined in rebuild cell

### Lab 07 — Guardrails & Governance
- Added agent rebuild cell after cell-03 (same pattern as Lab 06)
- Added UC toolkit packages to pip install

### Lab 08 — Evaluation & LLM-as-Judge
- Changed `MODEL_NAME` from `arxiv_research_agent` to `arxiv_chat_agent` (matches Lab 05 registration)
- Changed version comparison to dynamically discover available versions

### Lab 09 — Deployment & Model Serving
- Changed `MODEL_NAME` from `arxiv_research_agent` to `arxiv_chat_agent`

### Lab 10 — Monitoring & Observability
- Added `WorkspaceClient` import and init in cell-03

### Other Fixes
- Updated `cheatsheets/agent-framework-cheatsheet.md`: all `arxiv_research_agent` → `arxiv_chat_agent`
- Updated `prerequisites.md`: removed "Choose cost profile" → uses `databricks-llama-4-maverick`
- Updated Lab 03 key takeaways: removed stale `arxiv_research_agent` reference

## What Needs To Be Done

### To complete testing on Databricks workspace:
1. Upload updated notebooks to workspace
2. Run Lab 05 to register the model in UC
3. Run Lab 06 to verify tracing
4. Run Lab 07 to verify guardrails
5. Run Lab 08 (depends on registered model from Lab 05)
6. Run Lab 09 (depends on registered model from Lab 05)
7. Run Lab 10 (depends on serving endpoint from Lab 09)

### Push to GitHub
Commit all fixes and push to main.

## Workspace State
- Catalog: `genai_lab_guide` with schema `default`
- Volume: `genai_lab_guide.default.arxiv_papers` — 8 papers uploaded
- Table: `genai_lab_guide.default.arxiv_chunks` — chunks from Lab 01
- Table: `genai_lab_guide.default.parsed_docs` — parsed documents from Lab 01
- VS Endpoint: `genai_lab_guide_vs_endpoint` (ONLINE)
- VS Index: `genai_lab_guide.default.arxiv_chunks_index` (synced)
- UC Functions: `get_paper_metadata` (SQL), `format_citation` (SQL CONCAT)
- Model: `genai_lab_guide.default.arxiv_chat_agent` — not yet registered (Lab 05 not run on workspace)
- No serving endpoints deployed yet

## Available LLM Endpoints (accessible on trial)
- `databricks-llama-4-maverick` — best for tool calling (used everywhere)
- `databricks-meta-llama-3-3-70b-instruct` — good but sometimes misfires on tools
- `databricks-meta-llama-3-1-8b-instruct` — cheap, good for simple tasks
