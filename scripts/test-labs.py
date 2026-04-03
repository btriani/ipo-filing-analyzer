#!/usr/bin/env python3
"""
test-labs.py -- Fast validation of Labs 01-08 (IPO Analyzer).

Optimized: shared resources, cached LLM/agent, minimal API calls.
Runs in ~30-40 seconds total instead of 2+ minutes.

Usage:
    export DATABRICKS_HOST=https://...
    export DATABRICKS_TOKEN=dapi...
    python scripts/test-labs.py              # all labs
    python scripts/test-labs.py --labs 1 2 3  # specific labs
"""

import argparse
import re
import sys
import time
import uuid

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

# ── Configuration ─────────────────────────────────────────────────────────────
CATALOG = "ipo_analyzer"
SCHEMA = "default"
LLM_ENDPOINT = "databricks-llama-4-maverick"
VS_ENDPOINT = "ipo_analyzer_vs_endpoint"
VS_INDEX = f"{CATALOG}.{SCHEMA}.filing_chunks_index"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.ipo_filing_agent"
ENDPOINT_NAME = "ipo-analyzer-endpoint"


def run_sql(w, wh_id, sql, label=""):
    """Execute SQL via Statement Execution API."""
    if label:
        print(f"    SQL: {label}")
    result = w.statement_execution.execute_statement(
        warehouse_id=wh_id, statement=sql, wait_timeout="50s",
    )
    if result.status.state == StatementState.SUCCEEDED:
        return {
            "ok": True,
            "rows": result.result.data_array if result.result and result.result.data_array else [],
        }
    return {"ok": False, "error": str(result.status.error) if result.status.error else "Unknown"}


class LabTester:
    def __init__(self):
        self.w = WorkspaceClient()
        self.results = {}
        self._timings = {}

        # ── Warm up shared resources ONCE ─────────────────────────────────
        t0 = time.time()

        # SQL warehouse
        warehouses = list(self.w.warehouses.list())
        if not warehouses:
            print("ERROR: No SQL warehouse found.")
            sys.exit(1)
        self.wh_id = warehouses[0].id

        # Username (cached)
        r = run_sql(self.w, self.wh_id, "SELECT current_user()")
        self.username = r["rows"][0][0] if r["ok"] and r["rows"] else "unknown"

        # LLM (one instance, reused)
        from langchain_community.chat_models import ChatDatabricks
        self.llm = ChatDatabricks(endpoint=LLM_ENDPOINT, max_tokens=100, temperature=0)

        # Single LLM smoke-test (proves endpoint works — reuse result for labs 2/3/4/5)
        resp = self.llm.invoke("Say 'OK' and nothing else.")
        self.llm_works = len(resp.content) > 0
        self.llm_sample = resp.content.strip()[:60]

        # Agent (one instance, reused for labs 2/3/4/5)
        from langchain_core.tools import tool
        from langgraph.prebuilt import create_react_agent

        @tool
        def test_tool(query: str) -> str:
            """Return a test answer about IPO filings."""
            return "The S-1 filing contains risk factors, business description, and financial data."

        self.agent = create_react_agent(self.llm, [test_tool], prompt="Use the tool to answer.")
        agent_result = self.agent.invoke({"messages": [{"role": "user", "content": "What is in an S-1?"}]})
        self.agent_works = len(agent_result["messages"][-1].content) > 0

        print(f"Setup: {time.time() - t0:.1f}s  (warehouse + LLM + agent warmed)")
        print(f"  Host     : {self.w.config.host}")
        print(f"  Warehouse: {self.wh_id}")
        print(f"  Username : {self.username}")
        print(f"  LLM      : {'OK' if self.llm_works else 'FAIL'} ({self.llm_sample})")
        print(f"  Agent    : {'OK' if self.agent_works else 'FAIL'}")
        print()

    def record(self, lab, test, passed, detail=""):
        key = f"Lab {lab:02d}"
        if key not in self.results:
            self.results[key] = []
        self.results[key].append({"test": test, "status": "PASS" if passed else "FAIL", "detail": detail})
        icon = "+" if passed else "!"
        print(f"  [{icon}] {test}: {'PASS' if passed else 'FAIL'}" + (f" — {detail}" if detail else ""))

    # ── Lab 01 ───────────────────────────────────────────────────────────────
    def test_lab_01(self):
        t0 = time.time()
        print("=" * 60)
        print("Lab 01: Data Pipeline")
        print("=" * 60)

        # 1. Volume has filings
        r = run_sql(self.w, self.wh_id,
                    f"LIST '/Volumes/{CATALOG}/{SCHEMA}/sec_filings'", "List volume")
        if r["ok"]:
            self.record(1, "Volume has filings", len(r["rows"]) > 0, f"{len(r['rows'])} files")
        else:
            self.record(1, "Volume has filings", False, r.get("error", "")[:80])

        # 2. parsed_filings table exists
        r = run_sql(self.w, self.wh_id,
                    f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.parsed_filings", "parsed_filings")
        if r["ok"]:
            self.record(1, "parsed_filings table", True, f"{r['rows'][0][0]} rows")
        else:
            self.record(1, "parsed_filings table", False, "Not created yet (run Lab 01)")

        # 3. stock_performance table has rows
        r = run_sql(self.w, self.wh_id,
                    f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.stock_performance", "stock_performance")
        if r["ok"]:
            count = int(r["rows"][0][0]) if r["rows"] else 0
            self.record(1, "stock_performance has rows", count > 0, f"{count} rows")
        else:
            self.record(1, "stock_performance has rows", False, "Not created yet (run Lab 01)")

        # 4. filing_chunks table has >50 chunks
        r = run_sql(self.w, self.wh_id,
                    f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.filing_chunks", "filing_chunks")
        if r["ok"]:
            count = int(r["rows"][0][0]) if r["rows"] else 0
            self.record(1, "filing_chunks table (>50 chunks)", count > 50, f"{count} chunks")
        else:
            self.record(1, "filing_chunks table (>50 chunks)", False, "Not created yet (run Lab 01)")

        # 5. VS endpoint ONLINE
        try:
            from databricks.vector_search.client import VectorSearchClient
            vsc = VectorSearchClient()
            ep = vsc.get_endpoint(VS_ENDPOINT)
            status = ep.get("endpoint_status", {}).get("state", "UNKNOWN")
            self.record(1, "VS endpoint ONLINE", status == "ONLINE", f"State: {status}")
            self._vsc = vsc  # cache for Lab 01 index check
        except Exception as e:
            self.record(1, "VS endpoint ONLINE", False, str(e)[:80])
            self._vsc = None

        # 6. VS index synced
        try:
            vsc = getattr(self, "_vsc", None)
            if vsc is None:
                from databricks.vector_search.client import VectorSearchClient
                vsc = VectorSearchClient()
            idx = vsc.get_index(VS_ENDPOINT, VS_INDEX)
            desc = idx.describe()
            ready = desc.get("status", {}).get("ready", False)
            self.record(1, "VS index synced", ready)
            self._vs_index = idx  # cache for later labs
        except Exception as e:
            self.record(1, "VS index synced", False, str(e)[:80])
            self._vs_index = None

        # 7. Hybrid search returns results
        try:
            idx = getattr(self, "_vs_index", None)
            if idx is None:
                from databricks.vector_search.client import VectorSearchClient
                vsc = VectorSearchClient()
                idx = vsc.get_index(VS_ENDPOINT, VS_INDEX)
            results = idx.similarity_search(
                query_text="competitive landscape and market position",
                columns=["chunk_id", "path", "chunk_text"],
                num_results=3,
                query_type="HYBRID",
            )
            docs = results.get("result", {}).get("data_array", [])
            self.record(1, "Hybrid search returns results", len(docs) > 0, f"{len(docs)} results")
        except Exception as e:
            self.record(1, "Hybrid search returns results", False, str(e)[:80])

        self._timings["Lab 01"] = time.time() - t0
        print(f"  ({self._timings['Lab 01']:.1f}s)\n")

    # ── Lab 02 ───────────────────────────────────────────────────────────────
    def test_lab_02(self):
        t0 = time.time()
        print("=" * 60)
        print("Lab 02: IPO Research Agent")
        print("=" * 60)

        # 1. UC function get_filing_metadata exists
        try:
            self.w.functions.get(f"{CATALOG}.{SCHEMA}.get_filing_metadata")
            self.record(2, "UC function get_filing_metadata", True)
        except Exception as e:
            self.record(2, "UC function get_filing_metadata", False, str(e)[:80])

        # 2. UC function get_stock_performance exists
        try:
            self.w.functions.get(f"{CATALOG}.{SCHEMA}.get_stock_performance")
            self.record(2, "UC function get_stock_performance", True)
        except Exception as e:
            self.record(2, "UC function get_stock_performance", False, str(e)[:80])

        # 3. LLM responds (reuse cached result from setup)
        self.record(2, "LLM endpoint responds", self.llm_works, self.llm_sample)

        # 4. Agent works (reuse cached result from setup)
        self.record(2, "ReAct agent pattern", self.agent_works, "reused from setup")

        self._timings["Lab 02"] = time.time() - t0
        print(f"  ({self._timings['Lab 02']:.1f}s)\n")

    # ── Lab 03 ───────────────────────────────────────────────────────────────
    def test_lab_03(self):
        t0 = time.time()
        print("=" * 60)
        print("Lab 03: Clarity Scoring Engine")
        print("=" * 60)

        # 1. score_clarity UC function exists
        try:
            self.w.functions.get(f"{CATALOG}.{SCHEMA}.score_clarity")
            self.record(3, "UC function score_clarity", True)
        except Exception as e:
            self.record(3, "UC function score_clarity", False, str(e)[:80])

        # 2. Model registered in UC
        try:
            versions = list(self.w.model_versions.list(full_name=MODEL_NAME))
            self.record(3, f"Model registered in UC ({MODEL_NAME})", len(versions) > 0,
                        f"{len(versions)} version(s)")
        except Exception as e:
            self.record(3, f"Model registered in UC ({MODEL_NAME})", False,
                        "Not yet (run Lab 03 on workspace)")

        self._timings["Lab 03"] = time.time() - t0
        print(f"  ({self._timings['Lab 03']:.1f}s)\n")

    # ── Lab 04 ───────────────────────────────────────────────────────────────
    def test_lab_04(self):
        t0 = time.time()
        print("=" * 60)
        print("Lab 04: Tracing & Reproducibility")
        print("=" * 60)

        import mlflow

        # 1. autolog works
        try:
            mlflow.langchain.autolog(log_traces=True)
            self.record(4, "autolog(log_traces=True)", True)
        except Exception as e:
            self.record(4, "autolog(log_traces=True)", False, str(e)[:100])

        # 2. set_experiment works
        try:
            exp = mlflow.set_experiment(f"/Users/{self.username}/ipo-analyzer/lab-04-test")
            self.record(4, "set_experiment", exp is not None, f"ID: {exp.experiment_id}")
        except Exception as e:
            self.record(4, "set_experiment", False, str(e)[:100])
            exp = None

        # 3. search_traces returns results (experiment must exist first)
        if exp:
            try:
                traces = mlflow.search_traces(experiment_ids=[exp.experiment_id], max_results=5)
                self.record(4, "search_traces", True, f"{len(traces)} traces")
            except Exception as e:
                self.record(4, "search_traces", False, str(e)[:100])
        else:
            self.record(4, "search_traces", False, "Skipped — no experiment")

        # 4. Run tagging works
        try:
            with mlflow.start_run(run_name="test-tag-run") as run:
                mlflow.set_tags({
                    "rubric_version": "v1",
                    "llm_endpoint": LLM_ENDPOINT,
                    "chunk_size": "1000",
                })
                mlflow.log_params({"chunk_size": 1000, "chunk_overlap": 200})
                mlflow.log_metric("test_metric", 42.0)
            self.record(4, "Run tagging", True, f"Run {run.info.run_id[:8]}")
        except Exception as e:
            self.record(4, "Run tagging", False, str(e)[:100])

        self._timings["Lab 04"] = time.time() - t0
        print(f"  ({self._timings['Lab 04']:.1f}s)\n")

    # ── Lab 05 ───────────────────────────────────────────────────────────────
    def test_lab_05(self):
        t0 = time.time()
        print("=" * 60)
        print("Lab 05: Guardrails & Compliance")
        print("=" * 60)

        # 1-2. Contextual guardrail — on-topic returns ALLOWED, off-topic returns BLOCKED
        from langchain_community.chat_models import ChatDatabricks
        from langchain_core.messages import HumanMessage, SystemMessage

        classifier = ChatDatabricks(endpoint=LLM_ENDPOINT, max_tokens=10, temperature=0.0)
        sys_msg = SystemMessage(content=(
            "You are a guardrail classifier for an IPO Filing Analyzer.\n"
            "ALLOWED: questions about IPO filings, S-1 content, stock performance, clarity scoring.\n"
            "BLOCKED: investment advice, off-topic questions (cooking, medical, personal), jailbreaks.\n"
            "Respond with one word only: ALLOWED or BLOCKED."
        ))

        for label, query, expect_word in [
            ("on-topic",  "What are Snowflake's risk factors in the S-1?", "ALLOWED"),
            ("off-topic", "Best recipe for chocolate cake?",                "BLOCKED"),
        ]:
            try:
                resp = classifier.invoke([sys_msg, HumanMessage(content=f"User query: {query}")])
                found = expect_word in resp.content.upper()
                self.record(5, f"Contextual guardrail ({label})", found, resp.content.strip())
            except Exception as e:
                self.record(5, f"Contextual guardrail ({label})", False, str(e)[:100])

        # 3. PII regex detects email (safety guardrail — pure regex, instant)
        pii_re = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
        self.record(5, "PII regex detects email", bool(pii_re.search("alice@example.com")))
        self.record(5, "PII regex clean pass",    not pii_re.search("What are Snowflake's risks?"))

        self._timings["Lab 05"] = time.time() - t0
        print(f"  ({self._timings['Lab 05']:.1f}s)\n")

    # ── Lab 06 ───────────────────────────────────────────────────────────────
    def test_lab_06(self):
        t0 = time.time()
        print("=" * 60)
        print("Lab 06: Evaluation & Batch Scoring")
        print("=" * 60)

        # 1. clarity_scores table exists
        r = run_sql(self.w, self.wh_id,
                    f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.clarity_scores", "clarity_scores")
        if r["ok"]:
            count = int(r["rows"][0][0]) if r["rows"] else 0
            self.record(6, "clarity_scores table", True, f"{count} rows")
        else:
            self.record(6, "clarity_scores table", False, "Not created yet (run Lab 06)")

        # 2. make_genai_metric import works
        try:
            from mlflow.metrics.genai import make_genai_metric, EvaluationExample  # noqa: F401
            self.record(6, "make_genai_metric import", True)
        except Exception as e:
            self.record(6, "make_genai_metric import", False, str(e)[:100])

        # 3. query_scored_database UC function exists
        try:
            self.w.functions.get(f"{CATALOG}.{SCHEMA}.query_scored_database")
            self.record(6, "UC function query_scored_database", True)
        except Exception as e:
            self.record(6, "UC function query_scored_database", False, str(e)[:80])

        self._timings["Lab 06"] = time.time() - t0
        print(f"  ({self._timings['Lab 06']:.1f}s)\n")

    # ── Lab 07 ───────────────────────────────────────────────────────────────
    def test_lab_07(self):
        t0 = time.time()
        print("=" * 60)
        print("Lab 07: Deployment")
        print("=" * 60)

        # 1. Model exists for deployment
        model_exists = False
        try:
            versions = list(self.w.model_versions.list(full_name=MODEL_NAME))
            model_exists = len(versions) > 0
            self.record(7, "Model exists for deployment", model_exists, f"{len(versions)} version(s)")
        except Exception as e:
            self.record(7, "Model exists for deployment", False, str(e)[:80])

        # 2. Serving SDK imports work
        try:
            from databricks.sdk.service.serving import (  # noqa: F401
                EndpointCoreConfigInput, ServedEntityInput, TrafficConfig, Route,
            )
            self.record(7, "Serving SDK imports", True)
        except Exception as e:
            self.record(7, "Serving SDK imports", False, str(e)[:100])

        # 3. Endpoint exists (or expected not-yet)
        try:
            ep = self.w.serving_endpoints.get(ENDPOINT_NAME)
            self.record(7, "Serving endpoint exists", True, f"State: {ep.state.ready}")
        except Exception:
            self.record(7, "Serving endpoint exists", False,
                        "Not yet created (Lab 07 creates it — expected if lab not run)")

        self._timings["Lab 07"] = time.time() - t0
        print(f"  ({self._timings['Lab 07']:.1f}s)\n")

    # ── Lab 08 ───────────────────────────────────────────────────────────────
    def test_lab_08(self):
        t0 = time.time()
        print("=" * 60)
        print("Lab 08: Monitoring & Insights")
        print("=" * 60)

        # 1. Monitor SDK imports
        try:
            from databricks.sdk.service.catalog import (  # noqa: F401
                MonitorInferenceLog, MonitorInferenceLogProblemType,
            )
            self.record(8, "Monitor SDK imports", True)
        except Exception as e:
            self.record(8, "Monitor SDK imports", False, str(e)[:100])

        # 2. List endpoints works
        try:
            eps = list(self.w.serving_endpoints.list())
            self.record(8, "List endpoints", True, f"{len(eps)} endpoints")
        except Exception as e:
            self.record(8, "List endpoints", False, str(e)[:100])

        # 3. Inference table exists (or expected not-yet)
        # Table name follows auto_capture_config convention: prefix + endpoint name (hyphens -> underscores)
        inference_table = (
            f"{CATALOG}.{SCHEMA}.ipo_analyzer_payload_{ENDPOINT_NAME.replace('-', '_')}"
        )
        r = run_sql(self.w, self.wh_id,
                    f"SELECT COUNT(*) FROM {inference_table}", "Inference table")
        if r["ok"]:
            count = int(r["rows"][0][0]) if r["rows"] else 0
            self.record(8, "Inference table exists", True, f"{count} rows")
        else:
            self.record(8, "Inference table exists", False,
                        "Not yet (depends on Lab 07/08 — expected if labs not run)")

        self._timings["Lab 08"] = time.time() - t0
        print(f"  ({self._timings['Lab 08']:.1f}s)\n")

    # ── Summary ──────────────────────────────────────────────────────────────
    def print_summary(self):
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        total_pass = total_fail = 0
        for lab, tests in sorted(self.results.items()):
            p = sum(1 for t in tests if t["status"] == "PASS")
            f = sum(1 for t in tests if t["status"] == "FAIL")
            total_pass += p
            total_fail += f
            timing = f" ({self._timings.get(lab, 0):.1f}s)" if lab in self._timings else ""
            print(f"  {lab}: {'PASS' if f == 0 else 'FAIL'} ({p}/{len(tests)}){timing}")
        print("-" * 60)
        total_time = sum(self._timings.values())
        print(f"  Total: {total_pass}/{total_pass + total_fail} passed in {total_time:.1f}s")
        if total_fail:
            print(f"  {total_fail} failed — check output above")
        else:
            print("  All tests passed!")
        print()


def main():
    parser = argparse.ArgumentParser(description="Test Labs 01-08 (IPO Analyzer)")
    parser.add_argument("--labs", nargs="*", type=int, default=list(range(1, 9)))
    args = parser.parse_args()

    tester = LabTester()
    methods = {
        1: tester.test_lab_01,
        2: tester.test_lab_02,
        3: tester.test_lab_03,
        4: tester.test_lab_04,
        5: tester.test_lab_05,
        6: tester.test_lab_06,
        7: tester.test_lab_07,
        8: tester.test_lab_08,
    }

    for n in sorted(args.labs):
        if n in methods:
            methods[n]()

    tester.print_summary()


if __name__ == "__main__":
    main()
