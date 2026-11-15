"""R&D question A: does tool granularity change agent behaviour?

  MODEL_PROFILE=open python -m evals.runners.tool_granularity   -> evals/results/tool_granularity.json

40 tasks with a known correct call are given to the small model under three tool sets:
  fine    many single-purpose tools (the server's real tools)
  coarse  two catch-all tools (marketplace_read / marketplace_write with an "action" argument)
  best    the fine set with rewritten, example-bearing descriptions
Reports tool-selection accuracy, argument accuracy and tokens per task. Needs an LLM profile.
"""
import json
import sys

from pydantic import BaseModel

from agent import llm
from agent.config import cfg
from evals.common import mean, save

FINE = {"search_jobs": "Search open jobs.", "get_job": "Get one job.", "get_client_history": "Get a client's history.",
        "get_connects_balance": "Get Connects balance.", "get_market_stats": "Price statistics for a category.",
        "list_messages": "List client threads.", "search_evidence": "Search portfolio evidence.",
        "get_case_study": "Load one evidence item.", "list_skills": "List provable skills.", "free_slots": "Free calendar slots."}
COARSE = {"marketplace_read": "Read anything from the marketplace. args: action (jobs|job|client|connects|stats|messages), id, query",
          "portfolio_read": "Read anything from the portfolio. args: action (search|item|skills), id, query",
          "workspace_read": "Read the calendar. args: action (slots)"}
BEST = {"search_jobs": "Find open jobs by keyword. Use for 'find/show jobs about X'. args: query",
        "get_job": "Fetch ONE job when you already have its id (job-0001). args: job_id",
        "get_client_history": "Is this client trustworthy? Spend, hires, payment verified. args: client_id (client-001)",
        "get_connects_balance": "How many Connects are left. No args.",
        "get_market_stats": "What similar jobs were awarded for; use before pricing. args: category (ai_ml|web|data)",
        "list_messages": "Client conversation threads and replies. args: thread_id (optional)",
        "search_evidence": "Find portfolio proof for a requirement; use before claiming experience. args: requirement",
        "get_case_study": "Load one evidence item in full by id (…-case-01). args: id",
        "list_skills": "Every skill the portfolio can prove. No args.",
        "free_slots": "Free interview times from the calendar. args: start_date (YYYY-MM-DD)"}
COARSE_OF = {"search_jobs": ("marketplace_read", "jobs"), "get_job": ("marketplace_read", "job"), "get_client_history": ("marketplace_read", "client"),
             "get_connects_balance": ("marketplace_read", "connects"), "get_market_stats": ("marketplace_read", "stats"),
             "list_messages": ("marketplace_read", "messages"), "search_evidence": ("portfolio_read", "search"),
             "get_case_study": ("portfolio_read", "item"), "list_skills": ("portfolio_read", "skills"), "free_slots": ("workspace_read", "slots")}
TEMPLATES = [("Find jobs about {x}", "search_jobs", "query", ["chatbots", "dashboards", "stripe", "dbt"]),
             ("Open job {x}", "get_job", "job_id", ["job-0003", "job-0041", "job-0107", "job-0222"]),
             ("Is {x} a reliable client?", "get_client_history", "client_id", ["client-004", "client-050", "client-099", "client-scam-02"]),
             ("How many Connects do I have left ({x})?", "get_connects_balance", None, ["today", "this week", "now", "right now"]),
             ("What do {x} jobs usually pay?", "get_market_stats", "category", ["ai_ml", "web", "data", "web"]),
             ("Show the conversation {x}", "list_messages", "thread_id", ["prop-0001", "prop-0002", "prop-0003", "prop-0004"]),
             ("Have I done work with {x}?", "search_evidence", "requirement", ["FastAPI", "Power BI", "Stripe", "PyTorch"]),
             ("Load evidence {x}", "get_case_study", "id", ["ai_ml_engineer-case-01", "data_analyst-case-03", "fullstack_dev-case-07", "ai_ml_engineer-rev-02"]),
             ("Which skills can I prove ({x})?", "list_skills", None, ["all", "full list", "everything", "summary"]),
             ("When am I free for a call from {x}?", "free_slots", "start_date", ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19"])]
TASKS = [{"ask": t.format(x=x), "tool": tool, "arg": arg, "value": x} for t, tool, arg, xs in TEMPLATES for x in xs]  # 40 tasks


class Call(BaseModel):
    tool: str
    arguments: dict


def run(name: str, tools: dict) -> dict:
    sel, arg, tokens = [], [], []
    listing = "\n".join(f"- {k}: {v}" for k, v in tools.items())
    for t in TASKS:
        llm.take_usage()
        call = llm.structured("analyst", Call, prompt="tool_choice", tools=listing, ask=t["ask"])
        tokens.append(llm.take_usage()[0])
        want_tool, want_action = (COARSE_OF[t["tool"]] if name == "coarse" else (t["tool"], None))
        ok = bool(call) and call.tool == want_tool and (want_action is None or call.arguments.get("action") == want_action)
        sel.append(ok)
        arg.append(ok and (t["arg"] is None or t["value"] in json.dumps(call.arguments)))
    return {"tools": len(tools), "tool_selection_accuracy": mean(sel), "argument_accuracy": mean(arg), "tokens_per_task": mean(tokens)}


if __name__ == "__main__":
    if not llm.enabled():
        sys.exit("R&D question A needs a model: set MODEL_PROFILE=open and OPEN_LLM_API_KEY.")
    save("tool_granularity", {"model": cfg()["profiles"][cfg()["profile"]]["small"], "n_tasks": len(TASKS),
                              "sets": {n: run(n, s) for n, s in (("fine", FINE), ("coarse", COARSE), ("best", BEST))}})
