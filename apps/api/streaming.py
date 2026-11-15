"""SSE bridge to LangGraph streams.

The graph runs in the worker with graph.stream(..., stream_mode="updates"); every node update is
appended to the run document (service.publish). This generator tails that document and forwards
each event to the browser, so the stream works across processes and survives a page refresh
(a reconnect simply replays the run's events from the start).
"""
import json
import time

from apps.api import db


def sse_events(user: str, run_id: str, poll_seconds: float = 0.4, max_seconds: int = 600):
    sent, deadline = 0, time.time() + max_seconds
    while time.time() < deadline:
        run = db.get(user, "run", run_id)
        for event in run["events"][sent:]:
            yield f"data: {json.dumps(event)}\n\n"
        sent = len(run["events"])
        if run["status"] in ("done", "waiting_approval", "error"):
            yield f"event: close\ndata: {json.dumps({'status': run['status']})}\n\n"
            return
        time.sleep(poll_seconds)
