"""Checkpointer factory (C6 durability).

DATABASE_URL=postgres...  -> PostgresSaver (required for the crash-and-resume demo and for Docker)
otherwise                 -> in-memory saver (unit tests and quick local runs only)
"""
import os

_saver = None


def get_checkpointer():
    global _saver
    if _saver is None:
        url = os.getenv("DATABASE_URL", "")
        if url.startswith("postgres"):
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg.rows import dict_row
            _saver = PostgresSaver(psycopg.connect(url, autocommit=True, row_factory=dict_row))
            _saver.setup()  # creates the checkpoint tables on first run
        else:
            try:
                from langgraph.checkpoint.memory import InMemorySaver
            except ImportError:  # older LangGraph
                from langgraph.checkpoint.memory import MemorySaver as InMemorySaver
            _saver = InMemorySaver()
    return _saver


def thread_config(thread_id: str, trace_id: str = "") -> dict:
    """One thread per job (bid graph) or per client conversation. The trace id is attached as
    metadata so LangSmith runs can be found from the id shown in the UI."""
    return {"configurable": {"thread_id": thread_id}, "metadata": {"trace_id": trace_id}, "recursion_limit": 60}
