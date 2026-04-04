import uuid
from typing import Optional

try:
    from databricks.agents import ChatAgent, ChatAgentMessage, ChatAgentResponse
except ImportError:
    from mlflow.pyfunc import ChatAgent
    from mlflow.types.agent import ChatAgentMessage, ChatAgentResponse

import mlflow

CATALOG = "ipo_analyzer"
SCHEMA = "default"
LLM_ENDPOINT = "databricks-meta-llama-3.1-405b-instruct"
VS_ENDPOINT = "ipo_analyzer_vs_endpoint"
VS_INDEX = f"{CATALOG}.{SCHEMA}.filing_chunks_index"

SYSTEM_PROMPT = (
    "You are an IPO Filing Analyzer for a financial research firm. "
    "You have access to S-1 filings from tech IPOs and stock performance data.\n\n"
    "Tools:\n"
    "- search_filings: Search S-1 text for relevant passages. Include the company name.\n"
    "- get_filing_metadata: Look up filing statistics for a company\n"
    "- get_stock_performance: Look up stock returns by ticker symbol\n"
    "- score_clarity: Score a filing section for messaging clarity (1-100)\n\n"
    "Guidelines:\n"
    "- Always use tools to gather data before answering. Never guess.\n"
    "- Cite the source filing. Structure analysis with clear sections.\n"
    "- IMPORTANT: You provide financial ANALYSIS, not investment ADVICE."
)


class IpoAnalyzerAgent(ChatAgent):
    """IPO Filing Analyzer agent with lazy initialization.

    External resources (Vector Search, UC functions) are connected on first
    predict() call, not during __init__. This allows Model Serving to load
    the model without requiring runtime connections at load time.
    """

    def __init__(self):
        self._initialized = False
        self._llm = None
        self._tools = None
        self._agent = None

    def _lazy_init(self):
        """Connect to external resources on first call."""
        if self._initialized:
            return

        from langchain_community.chat_models import ChatDatabricks
        from langchain_core.tools import tool
        from databricks.vector_search.client import VectorSearchClient
        from unitycatalog.ai.core.databricks import DatabricksFunctionClient
        from unitycatalog.ai.langchain.toolkit import UCFunctionToolkit
        from langgraph.prebuilt import create_react_agent

        self._llm = ChatDatabricks(
            endpoint=LLM_ENDPOINT, max_tokens=1024, temperature=0.1
        )

        vsc = VectorSearchClient()
        vs_index = vsc.get_index(VS_ENDPOINT, VS_INDEX)

        @tool
        def search_filings(query: str) -> str:
            """Search S-1 filing text for passages relevant to the query."""
            results = vs_index.similarity_search(
                query_text=query,
                columns=["chunk_text", "path"],
                num_results=10,
                query_type="HYBRID",
            )
            docs = results.get("result", {}).get("data_array", [])
            parts = []
            for d in docs:
                source = d[1].split("/")[-1].replace("-S1.html", "")
                parts.append("[Source: " + source + "]\n" + d[0])
            return "\n\n---\n\n".join(parts) if parts else "No relevant passages found."

        uc_fn_names = [
            f"{CATALOG}.{SCHEMA}.get_filing_metadata",
            f"{CATALOG}.{SCHEMA}.get_stock_performance",
            f"{CATALOG}.{SCHEMA}.score_clarity",
        ]
        uc_client = DatabricksFunctionClient()
        uc_toolkit = UCFunctionToolkit(
            function_names=uc_fn_names, client=uc_client
        )
        self._tools = [search_filings] + uc_toolkit.tools
        self._agent = create_react_agent(
            self._llm, self._tools, prompt=SYSTEM_PROMPT
        )
        self._initialized = True

    def predict(self, messages, context=None, custom_inputs=None):
        self._lazy_init()

        user_query = messages[-1].content if messages else ""
        result = self._agent.invoke(
            {"messages": [{"role": "user", "content": user_query}]}
        )
        return ChatAgentResponse(
            messages=[
                ChatAgentMessage(
                    role="assistant",
                    id=str(uuid.uuid4()),
                    content=result["messages"][-1].content,
                )
            ]
        )


mlflow.models.set_model(IpoAnalyzerAgent())
