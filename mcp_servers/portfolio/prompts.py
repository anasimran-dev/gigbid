"""Portfolio MCP prompt templates (A1): what a freelancer would actually pick in Claude Desktop or Cursor."""


def answer_screening_question(question: str) -> str:
    """Answer a client's screening question from my portfolio."""
    return (f"Answer this screening question for a freelance job: \"{question}\".\n"
            "First call search_evidence with the question. Use only facts found in the returned items, "
            "cite each item id in brackets, keep it under 120 words, and say so plainly if no evidence exists.")


def prove_requirement(requirement: str) -> str:
    """Show which of my projects prove a job requirement."""
    return (f"Call search_evidence for: \"{requirement}\". List the best three items as "
            "'project - what I did - measurable result [id]'. If nothing matches, reply 'no evidence'.")
