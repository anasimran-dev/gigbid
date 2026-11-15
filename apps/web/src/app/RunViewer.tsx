import { Link, useParams } from "react-router-dom";
import RunTimeline from "../components/RunTimeline";
import { Async, Badge } from "../components/States";
import { useApi } from "../lib/http";

type Run = { id: string; kind: string; subject: string; status: string; trace_id: string;
             summary?: { total_seconds: number; total_tokens: number; total_usd: number; nodes: Record<string, { seconds: number; tokens: number; usd: number }> } };
const LANGSMITH = import.meta.env.VITE_LANGSMITH_PROJECT_URL as string | undefined;

export function Runs() {
  const { data, loading, error } = useApi<Run[]>("/runs", 5000);
  return (
    <>
      <h1>Agent runs</h1>
      <Async loading={loading} error={error} empty={data?.length === 0 && "No agent runs yet."}>
        <ul className="list">
          {data?.map((r) => (
            <li key={r.id} className="card row spread">
              <Link to={`/runs/${r.id}`}>{r.kind} · {r.subject}</Link>
              <Badge kind={r.status === "error" ? "bad" : "info"}>{r.status.replace("_", " ")}</Badge>
            </li>
          ))}
        </ul>
      </Async>
    </>
  );
}

/** Live node-by-node progress with a link to the full trace. */
export default function RunViewer() {
  const { id } = useParams();
  const { data: run, loading, error, reload } = useApi<Run>(`/runs/${id}`);
  const { data: trace } = useApi<Record<string, unknown>[]>(run ? `/runs/${id}/trace` : null);
  return (
    <Async loading={loading} error={error}>
      {run && (
        <>
          <h1>Run: {run.kind} · {run.subject}</h1>
          <p className="row meta">
            <span>Trace id <code>{run.trace_id}</code></span>
            {LANGSMITH && <a href={LANGSMITH} target="_blank" rel="noreferrer">Open LangSmith project (search metadata trace_id)</a>}
            {run.kind === "bid" && <Link to={`/studio/${run.subject}`}>Proposal studio</Link>}
          </p>
          <section className="card"><h2>Progress</h2><RunTimeline runId={run.id} onDone={reload} /></section>
          {run.summary && (
            <section className="card">
              <h2>Cost and time per node</h2>
              <p>{run.summary.total_seconds}s · {run.summary.total_tokens} tokens · ${run.summary.total_usd}</p>
              <div className="scroll"><table>
                <thead><tr><th scope="col">Node</th><th scope="col">Seconds</th><th scope="col">Tokens</th><th scope="col">USD</th></tr></thead>
                <tbody>{Object.entries(run.summary.nodes).map(([n, v]) => <tr key={n}><th scope="row">{n}</th><td>{v.seconds.toFixed(3)}</td><td>{v.tokens}</td><td>{v.usd.toFixed(5)}</td></tr>)}</tbody>
              </table></div>
            </section>
          )}
          <details className="card"><summary>Full trace ({trace?.length ?? 0} events, PII masked)</summary><pre className="preview">{JSON.stringify(trace, null, 1)}</pre></details>
        </>
      )}
    </Async>
  );
}
