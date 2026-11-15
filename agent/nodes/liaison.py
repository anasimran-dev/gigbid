"""Client Liaison: read client replies, classify intent, draft a response or interview slots.
MCP: marketplace (read; write only after approval), workspace, portfolio (read)."""
import re
from datetime import date, datetime, timedelta

from agent import llm
from agent.config import cfg
from agent.guardrails import detect_injection, wrap_untrusted
from agent.handoffs import MessageIntent, ReplyDraft
from agent.mcp_client import call_tool
from agent.nodes.base import node
from agent.nodes.compliance import check
from agent.nodes.writer import result_sentence


@node("read")
def read(state):
    threads = call_tool("liaison", "list_messages", {"user_id": state["user_id"], "thread_id": state["thread_id"]})["threads"]
    if not threads:
        return {"status": "dead_letter", "status_reason": f"thread {state['thread_id']} not found"}
    last = threads[0]["messages"][-1]
    if last["from"] != "client":
        return {"thread": threads[0], "status": "sent", "status_reason": "No new client message"}
    return {"thread": threads[0], "last_client_message": last["text"], "status": "drafting"}


def heuristic_intent(text: str) -> MessageIntent:
    low = text.lower()
    if detect_injection(text) or any(p in low for p in cfg()["policy"]["off_platform"]) or "personal email" in low:
        return MessageIntent(intent="scam_signal", reason="asks to leave the platform or contains injected instructions")
    if re.search(r"\b(call|interview|meeting|zoom|meet)\b", low):
        return MessageIntent(intent="interview_request", reason="asks for a call")
    if re.search(r"\$\s?\d|\b(budget|price|rate|discount|cheaper)\b", low):
        return MessageIntent(intent="negotiation", reason="talks about price")
    if "?" in text:
        return MessageIntent(intent="question", reason="asks a question")
    return MessageIntent(intent="other", reason="no clear ask")


@node("classify")
def classify(state):
    text = state["last_client_message"]
    base = heuristic_intent(text)
    model = llm.structured("intent", MessageIntent, message=wrap_untrusted(text, "client_message"))
    if base.intent == "scam_signal" or not model:  # a rule-based scam signal is never downgraded
        model = base
    return {"intent": model.model_dump()}


def heuristic_reply(state, intent: str) -> ReplyDraft:
    user, thread, text = state["user_id"], state["thread_id"], state["last_client_message"]
    floor = state.get("settings", {}).get("min_project_usd", 0)
    if intent == "scam_signal":
        return ReplyDraft(thread_id=thread, intent=intent, hold_scam=True,
                          text="Thanks for the reply. I keep all communication and payment on the platform, as its terms require. "
                               "I am glad to continue here and can answer any question about the project.")
    if intent == "interview_request":
        slots = call_tool("liaison", "free_slots", {"user_id": user, "start_date": str(date.today() + timedelta(days=1)), "days": 5})["slots"][:3]
        nice = ", ".join(datetime.fromisoformat(s).strftime("%a %d %b at %H:%M") for s in slots)
        return ReplyDraft(thread_id=thread, intent=intent, slots=slots,
                          text=f"A call works well. These times are free on my side (Asia/Karachi): {nice}. Which one suits you?")
    if intent == "negotiation":
        offer = [float(x.replace(",", "")) for x in re.findall(r"\$\s?([\d,]+)", text)]
        if offer and offer[0] >= floor:
            body = f"I can work with ${offer[0]:.0f} if we keep the scope to the deliverables in my proposal."
        else:
            body = f"The lowest I can go for this scope is ${floor:.0f}. If that is over budget, I can suggest a smaller first milestone."
        return ReplyDraft(thread_id=thread, intent=intent, text=f"Thanks for being direct about budget. {body}")
    found = call_tool("liaison", "search_evidence", {"requirement": text[:1000], "k": 3, "persona": state["persona"]})["evidence"]
    proof = next((e for e in found if e.get("project") and result_sentence(e)), None)
    body = (f"The closest example is {proof['title']}, where the work {result_sentence(proof)}. I would take the same approach here: "
            "confirm the inputs, deliver a small first version, then iterate.") if proof else \
           "I would start by confirming the inputs and success criteria, deliver a small first version, then iterate."
    return ReplyDraft(thread_id=thread, intent=intent, text=f"Thanks for the question. {body}")


@node("draft_reply")
def draft_reply(state):
    intent = state["intent"]["intent"]
    reply = heuristic_reply(state, intent)
    if intent in ("question", "negotiation", "other"):
        model = llm.structured("liaison", ReplyDraft, message=wrap_untrusted(state["last_client_message"], "client_message"),
                               intent=intent, floor_usd=state.get("settings", {}).get("min_project_usd", 0), fallback=reply.text)
        if model:
            reply = model.model_copy(update={"thread_id": state["thread_id"], "intent": intent, "slots": reply.slots})
    return {"reply": reply.model_dump()}


@node("reply_compliance")
def reply_compliance(state):
    edited = state.get("approval", {}).get("action") == "edit"
    verdict = check(state["reply"]["text"], [], edited, min_words=5)
    out = {"compliance": verdict.model_dump(), "reply": {**state["reply"], "text": verdict.cleaned_text or state["reply"]["text"]}}
    if not verdict.allowed and not edited:
        out.update(status="blocked", status_reason="Compliance Guard blocked the reply: " + "; ".join(verdict.violations))
    return out


@node("send")
def send(state):
    """Runs only after approval. Idempotency keys make a retried send a no-op."""
    reply, user = state["reply"], state["user_id"]
    n = len(state["thread"]["messages"])
    sent = call_tool("liaison", "send_message", {"user_id": user, "thread_id": state["thread_id"], "text": reply["text"],
                                                 "idempotency_key": f"{user}:{state['thread_id']}:msg{n}"})
    if reply.get("slots"):
        call_tool("liaison", "create_interview_hold", {"user_id": user, "slot": reply["slots"][0], "title": f"Interview: {state['thread_id']}",
                                                       "idempotency_key": f"{user}:{state['thread_id']}:hold{n}"})
    return {"sent": sent, "status": "sent"}
