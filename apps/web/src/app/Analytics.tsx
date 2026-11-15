import { Async } from "../components/States";
import { useApi } from "../lib/http";

type Stats = {
  by_category: Record<string, { sent: number; replied: number; hired: number; connects: number; reply_rate: number; hire_rate: number }>;
  connects_spent: number; proposals_sent: number; cost_per_proposal_usd: number; latency_p50_s: number; latency_p95_s: number;
  top_rejection_reasons: [string, number][]; decisions: Record<string, number>;
  declared_budgets: { declared_p95_seconds_per_proposal: number; declared_usd_per_proposal: number };
};

/** Reply and hire rate by category, Connects spent vs outcomes, cost and latency per proposal, rejection reasons. */
export default function Analytics() {
  const { data: s, loading, error } = useApi<Stats>("/analytics");
  return (
    <>
      <h1>Analytics</h1>
      <Async loading={loading} error={error} empty={s?.proposals_sent === 0 && "No proposals sent yet, so there is nothing to measure."}>
        {s && (
          <>
            <div className="grid stats">
              <div className="card"><span className="muted">Proposals sent</span><b>{s.proposals_sent}</b></div>
              <div className="card"><span className="muted">Connects spent</span><b>{s.connects_spent}</b></div>
              <div className="card"><span className="muted">Cost per proposal</span><b>${s.cost_per_proposal_usd}</b><span className="muted">budget ${s.declared_budgets.declared_usd_per_proposal}</span></div>
              <div className="card"><span className="muted">Latency p50 / p95</span><b>{s.latency_p50_s}s / {s.latency_p95_s}s</b><span className="muted">budget p95 {s.declared_budgets.declared_p95_seconds_per_proposal}s</span></div>
            </div>
            <section className="card">
              <h2>Outcomes by category</h2>
              <div className="scroll"><table>
                <thead><tr><th scope="col">Category</th><th scope="col">Sent</th><th scope="col">Reply rate</th><th scope="col">Hire rate</th><th scope="col">Connects</th><th scope="col">Connects per reply</th></tr></thead>
                <tbody>
                  {Object.entries(s.by_category).map(([c, r]) => (
                    <tr key={c}><th scope="row">{c}</th><td>{r.sent}</td><td>{(r.reply_rate * 100).toFixed(0)}%</td><td>{(r.hire_rate * 100).toFixed(0)}%</td><td>{r.connects}</td><td>{r.replied ? (r.connects / r.replied).toFixed(1) : "—"}</td></tr>
                  ))}
                </tbody>
              </table></div>
            </section>
            <section className="card">
              <h2>Top rejection reasons</h2>
              {s.top_rejection_reasons.length ? <ol>{s.top_rejection_reasons.map(([r, n]) => <li key={r}>{r} ({n})</li>)}</ol> : <p className="muted">You have not rejected any draft.</p>}
            </section>
          </>
        )}
      </Async>
    </>
  );
}
