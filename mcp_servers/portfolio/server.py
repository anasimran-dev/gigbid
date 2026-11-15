"""Portfolio MCP server (A1, read-only).

Run for Claude Desktop / Cursor (stdio):   python -m mcp_servers.portfolio.server
Run over HTTP:                             python -m mcp_servers.portfolio.server --http
Point it at your own portfolio folder with GIGBID_PERSONA_DIR and PORTFOLIO_PERSONA.
"""
from mcp_servers.common import READ, MCPServer, main_entry
from mcp_servers.portfolio import prompts, resources, tools

mcp = MCPServer("gigbid-portfolio", instructions="Read-only access to a freelancer's portfolio evidence. "
                "Use search_evidence before claiming any experience; cite evidence ids.")

for fn in (tools.search_evidence, tools.get_case_study, tools.list_skills):
    mcp.tool(annotations=READ)(fn)
mcp.resource("portfolio://case/{id}")(resources.case_resource)
mcp.resource("portfolio://proposal/{id}")(resources.proposal_resource)
mcp.prompt()(prompts.answer_screening_question)
mcp.prompt()(prompts.prove_requirement)


def main():
    main_entry(mcp, "PORTFOLIO_MCP_PORT", 9001)


if __name__ == "__main__":
    main()
