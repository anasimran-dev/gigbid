import { useEffect, useState } from "react";
import { API, getToken } from "../lib/http";
import type { RunEvent } from "../lib/types";

/** Live node-by-node progress, streamed from LangGraph over Server-Sent Events. */
export default function RunTimeline({ runId, onDone }: { runId: string; onDone?: (status: string) => void }) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [status, setStatus] = useState("running");
  useEffect(() => {
    setEvents([]);
    const source = new EventSource(`${API}/runs/${runId}/stream?token=${encodeURIComponent(getToken())}`);
    source.onmessage = (m) => setEvents((prev) => [...prev, JSON.parse(m.data)]);
    source.addEventListener("done", (m) => {
      const s = JSON.parse((m as MessageEvent).data).status;
      setStatus(s);
      onDone?.(s);
      source.close();
    });
    source.onerror = () => { setStatus("disconnected"); source.close(); };
    return () => source.close();
  }, [runId]);
  return (
    <ol className="timeline" aria-live="polite">
      {events.map((e, i) => (
        <li key={i}><b>{e.node}</b> {e.detail} {e.reason && <span className="muted">— {e.reason}</span>}</li>
      ))}
      <li className="muted">{status === "running" ? "Running…" : `Run ${status.replace("_", " ")}`}</li>
    </ol>
  );
}
