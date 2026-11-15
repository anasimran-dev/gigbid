import { Link } from "react-router-dom";
import ApprovalPanel from "../components/ApprovalPanel";
import { Async, Badge } from "../components/States";
import { useApi } from "../lib/http";
import type { Approval } from "../lib/types";

type Thread = { id: string; status?: string; run_id?: string; thread?: { messages: { from: string; text: string }[] }; approval: Approval | null };

/** Client threads with suggested replies and interview slots. Nothing is sent before approval. */
export default function Messages() {
  const { data, loading, error, reload } = useApi<{ threads: Thread[] }>("/messages", 5000);
  return (
    <>
      <h1>Messages</h1>
      <Async loading={loading} error={error} empty={data?.threads.length === 0 && "No client replies yet."}>
        {data?.threads.map((t) => (
          <section key={t.id} className="card">
            <h2>Thread {t.id} {t.run_id && <Link className="muted" to={`/runs/${t.run_id}`}>agent run</Link>}</h2>
            <ul className="chat">
              {t.thread?.messages.map((m, i) => <li key={i} className={m.from}><b>{m.from}:</b> {m.text}</li>)}
            </ul>
            {t.approval ? (
              <>
                <p>
                  Intent: <Badge kind={t.approval.payload.intent?.intent === "scam_signal" ? "bad" : "info"}>{t.approval.payload.intent?.intent.replace("_", " ")}</Badge>{" "}
                  {t.approval.payload.reply?.slots.length ? `Proposed slots: ${t.approval.payload.reply.slots.join(", ")}` : ""}
                </p>
                <ApprovalPanel key={t.approval.payload.reply?.text} approval={t.approval} text={t.approval.payload.reply?.text ?? ""} onDone={reload} />
              </>
            ) : <p className="muted">No reply waiting for approval.</p>}
          </section>
        ))}
      </Async>
    </>
  );
}
