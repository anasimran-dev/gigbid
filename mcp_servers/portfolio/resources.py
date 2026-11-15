"""Portfolio MCP resource templates (A1): portfolio://case/{id} and portfolio://proposal/{id}."""
from mcp_servers.portfolio.tools import get_case_study


def case_resource(id: str) -> str:
    """Full text of a case study or other evidence item."""
    return get_case_study(id)["text"]


def proposal_resource(id: str) -> str:
    """Full text and outcome of a past proposal."""
    item = get_case_study(id)
    return f"outcome: {item['outcome']}\n\n{item['text']}"
