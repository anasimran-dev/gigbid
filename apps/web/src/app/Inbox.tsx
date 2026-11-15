import { useState } from "react";
import { Link } from "react-router-dom";
import { api, useApi } from "../lib/http";
import type { JobCard } from "../lib/types";
import { Async, Badge } from "../components/States";

const ACTION_KIND = { bid: "ok", watch: "warn", skip: "bad" } as const;

/** New jobs ranked by fit, with risk badges, recommended action, price and Connects cost. */
export default function Inbox() {
  const [filter, setFilter] = useState("");
  const { data, loading, error, reload } = useApi<JobCard[]>("/jobs", 4000);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState("");
  const jobs = (data ?? []).filter((j) => !filter || j.action === filter);

  async function scout() {
    setBusy(true);
    await api("/jobs/scout", "POST").catch(() => undefined);
    setBusy(false);
    reload();
  }

  async function analyseById() {
    if (!jobId.trim()) return;
    await api(`/jobs/${jobId.trim()}/analyse`, "POST").catch(() => undefined);
    setJobId("");
    reload();
  }

  return (
    <>
      <div className="row spread">
        <h1>Job inbox</h1>
        <div className="row">
          <label htmlFor="filter" className="sr">Filter by recommendation</label>
          <select id="filter" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All recommendations</option>
            <option value="bid">Bid</option>
            <option value="watch">Watch</option>
            <option value="skip">Skip</option>
          </select>
          <button onClick={scout} disabled={busy}>{busy ? "Looking…" : "Find new jobs"}</button>
        </div>
        <div className="row">
          <label htmlFor="jobid" className="muted">Analyse a job by ID</label>
          <input id="jobid" value={jobId} placeholder="e.g. job-0285" onChange={(e) => setJobId(e.target.value)} />
          <button type="button" className="secondary" onClick={analyseById}>Analyse</button>
        </div>
      </div>
      <Async loading={loading} error={error} empty={jobs.length === 0 && "No jobs yet. Press “Find new jobs” to run your saved searches."}>
        <ul className="list">
          {jobs.map((j) => (
            <li key={j.id} className="card">
              <div className="row spread">
                <Link to={`/jobs/${j.id}`}><b>{j.title || j.id}</b></Link>
                {j.action ? <Badge kind={ACTION_KIND[j.action as keyof typeof ACTION_KIND] ?? "info"}>{j.action}</Badge> : <Badge kind="info">{j.status}</Badge>}
              </div>
              <div className="row meta">
                {j.fit != null && <span>Fit {(j.fit * 100).toFixed(0)}%</span>}
                {j.price_usd != null && <span>Bid ${j.price_usd}</span>}
                {j.connects_cost != null && <span>{j.connects_cost} Connects</span>}
                {(j.risk_flags ?? []).map((f) => <Badge key={f} kind="bad">{f.replaceAll("_", " ")}</Badge>)}
              </div>
              <div className="row">
                {j.status === "awaiting_approval" && <Link className="button" to={`/studio/${j.id}`}>Open proposal</Link>}
                <button className="secondary" onClick={() => api(`/jobs/${j.id}/skip`, "POST").then(reload)}>Skip</button>
              </div>
            </li>
          ))}
        </ul>
      </Async>
    </>
  );
}
