import { useEffect, useState } from "react";
import { Async } from "../components/States";
import { api, useApi } from "../lib/http";
import type { Settings as S } from "../lib/types";

type Memory = { style: { key: string; rule: string; seen: number }[]; outcomes: { key: string; n: number; reply_rate: number; hire_rate: number; best_strategy: string }[] };

/** Autonomy, budgets, saved searches, connected accounts and the memory viewer (see and delete what GigBid learned). */
export default function Settings() {
  const { data, loading, error } = useApi<S>("/settings");
  const memory = useApi<Memory>("/memory");
  const health = useApi<{ mode: string; profile: string; marketplace: { ok: boolean } }>("/health/marketplace");
  const [s, setS] = useState<S | null>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => { if (data) setS(data); }, [data]);

  const save = async () => { if (s) { await api("/settings", "PUT", s); setSaved(true); } };
  const forget = (ns: string, key: string) => api(`/memory/${ns}/${encodeURIComponent(key)}`, "DELETE").then(memory.reload);

  return (
    <>
      <h1>Settings</h1>
      <Async loading={loading || !s} error={error}>
        {s && (
          <section className="card">
            <h2>Autonomy and budgets</h2>
            <label htmlFor="autonomy">Autonomy level</label>
            <select id="autonomy" value={s.autonomy} onChange={(e) => setS({ ...s, autonomy: e.target.value as S["autonomy"] })}>
              <option value="manual">Manual: I review every job</option>
              <option value="auto_skip">Auto-skip low-fit jobs (never auto-send)</option>
            </select>
            <label htmlFor="floor">Minimum project budget (USD)</label>
            <input id="floor" type="number" min={0} value={s.min_project_usd} onChange={(e) => setS({ ...s, min_project_usd: +e.target.value })} />
            <label htmlFor="connects">Weekly Connects budget</label>
            <input id="connects" type="number" min={0} value={s.weekly_connects_budget} onChange={(e) => setS({ ...s, weekly_connects_budget: +e.target.value })} />
            <label htmlFor="searches">Saved searches (one per line)</label>
            <textarea id="searches" rows={3} value={s.saved_searches.join("\n")} onChange={(e) => setS({ ...s, saved_searches: e.target.value.split("\n") })} />
            <button onClick={save}>Save settings</button> {saved && <span role="status">Saved.</span>}
          </section>
        )}
      </Async>
      <section className="card">
        <h2>Connected accounts</h2>
        <p>Marketplace: <b>{health.data?.mode ?? "…"}</b> ({health.data?.marketplace.ok ? "connected" : "unavailable"}). Model profile: <b>{health.data?.profile ?? "…"}</b>.</p>
      </section>
      <section className="card">
        <h2>What GigBid has learned</h2>
        <Async loading={memory.loading} error={memory.error}>
          <h3>Style memory (from your edits)</h3>
          {memory.data?.style.length ? (
            <ul className="list">{memory.data.style.map((m) => <li key={m.key} className="row spread"><span>{m.rule} <span className="muted">(seen {m.seen} times)</span></span><button className="danger" onClick={() => forget("style", m.key)}>Delete</button></li>)}</ul>
          ) : <p className="muted">Nothing yet. A rule appears after you make the same kind of edit twice.</p>}
          <h3>Outcome memory (per job category)</h3>
          {memory.data?.outcomes.length ? (
            <ul className="list">{memory.data.outcomes.map((m) => <li key={m.key} className="row spread"><span>{m.key}: reply rate {(m.reply_rate * 100).toFixed(0)}% over {m.n} proposals, best strategy {m.best_strategy.replace("_", " ")}</span><button className="danger" onClick={() => forget("outcomes", m.key)}>Delete</button></li>)}</ul>
          ) : <p className="muted">Nothing yet. Statistics appear after three outcomes in a category.</p>}
        </Async>
      </section>
    </>
  );
}
