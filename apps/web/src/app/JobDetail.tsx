import { Link, useParams } from "react-router-dom";
import { useApi } from "../lib/http";
import type { Evidence } from "../lib/types";
import { Async, Badge } from "../components/States";

type Job = {
  job: { title: string; description: string }; status: string; status_reason: string; run_id?: string;
  job_spec?: { required_skills: string[]; deliverables: string[]; budget_min: number; budget_max: number; timeline_days: number | null; screening_questions: string[]; hidden_needs: string[] };
  risk_report?: { score: number; flags: string[]; explanation: string; client_quality: number };
  fit_report?: { score: number; reasons: string[]; matrix: { requirement: string; covered: boolean; evidence_ids: string[] }[] };
  evidence?: Evidence[]; decision?: { action: string; reasons: string[] };
  price_quote?: { amount_usd: number; low_usd: number; high_usd: number; connects_cost: number; rationale: string };
};

/** JobSpec, risk report, requirement-to-evidence matrix, price rationale and bid-or-skip reasoning. */
export default function JobDetail() {
  const { id } = useParams();
  const { data: j, loading, error } = useApi<Job>(`/jobs/${id}`, 4000);
  const title = (evId: string) => j?.evidence?.find((e) => e.id === evId)?.title ?? evId;
  return (
    <Async loading={loading} error={error}>
      {j && (
        <>
          <h1>{j.job?.title}</h1>
          <p className="row meta">
            <Badge kind="info">{j.status.replace("_", " ")}</Badge>
            {j.run_id && <Link to={`/runs/${j.run_id}`}>Agent run</Link>}
            {j.status === "awaiting_approval" && <Link className="button" to={`/studio/${id}`}>Open proposal studio</Link>}
          </p>
          <section className="card">
            <h2>Decision: {j.decision?.action ?? "pending"}</h2>
            <ul>{j.decision?.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          </section>
          <section className="card">
            <h2>Job post <span className="muted">(untrusted text from the client)</span></h2>
            <p>{j.job?.description}</p>
            {j.job_spec && (
              <dl>
                <dt>Skills</dt><dd>{j.job_spec.required_skills.join(", ") || "none extracted"}</dd>
                <dt>Deliverables</dt><dd>{j.job_spec.deliverables.join("; ") || "—"}</dd>
                <dt>Budget</dt><dd>${j.job_spec.budget_min} – ${j.job_spec.budget_max}</dd>
                <dt>Timeline</dt><dd>{j.job_spec.timeline_days ?? "?"} days</dd>
                <dt>Screening</dt><dd>{j.job_spec.screening_questions.join(" ") || "—"}</dd>
                <dt>Hidden needs</dt><dd>{j.job_spec.hidden_needs.join("; ") || "—"}</dd>
              </dl>
            )}
          </section>
          {j.risk_report && (
            <section className="card">
              <h2>Risk {(j.risk_report.score * 100).toFixed(0)}%</h2>
              <p>{j.risk_report.explanation} Client quality {(j.risk_report.client_quality * 100).toFixed(0)}%.</p>
              <p className="row">{j.risk_report.flags.map((f) => <Badge key={f} kind="bad">{f.replaceAll("_", " ")}</Badge>)}</p>
            </section>
          )}
          {j.fit_report && (
            <section className="card">
              <h2>Fit {(j.fit_report.score * 100).toFixed(0)}%: requirement → evidence</h2>
              <div className="scroll">
                <table>
                  <thead><tr><th scope="col">Requirement</th><th scope="col">Proof</th><th scope="col">Portfolio items</th></tr></thead>
                  <tbody>
                    {j.fit_report.matrix.map((m) => (
                      <tr key={m.requirement}>
                        <th scope="row">{m.requirement}</th>
                        <td><Badge kind={m.covered ? "ok" : "bad"}>{m.covered ? "proven" : "missing"}</Badge></td>
                        <td>{m.evidence_ids.map(title).join("; ") || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
          {j.price_quote && (
            <section className="card">
              <h2>Price ${j.price_quote.amount_usd} <span className="muted">(market ${j.price_quote.low_usd}–${j.price_quote.high_usd})</span></h2>
              <p>{j.price_quote.rationale}</p>
            </section>
          )}
        </>
      )}
    </Async>
  );
}
