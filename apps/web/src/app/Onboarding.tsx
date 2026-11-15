import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, useApi } from "../lib/http";
import type { Settings } from "../lib/types";
import { Async } from "../components/States";

const PERSONAS = [["ai_ml_engineer", "AI/ML engineer"], ["fullstack_dev", "Full-stack web developer"], ["data_analyst", "Data analyst"]];

/** Onboarding: choose persona, connect a marketplace, upload portfolio, set rates, filters and Connects budget. */
export default function Onboarding() {
  const navigate = useNavigate();
  const { data, loading, error } = useApi<Settings>("/settings");
  const [s, setS] = useState<Settings | null>(null);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [note, setNote] = useState("");
  useEffect(() => { if (data) setS(data); }, [data]);

  async function connectUpwork() {
    try {
      const res = await api<{ detail: { authorize_url: string } }>("/auth/upwork/start");
      window.location.href = res.detail.authorize_url;
    } catch (e) {
      setNote(`Could not start Upwork sign-in: ${(e as Error).message}`);
    }
  }

  async function finish(e: FormEvent) {
    e.preventDefault();
    if (!s) return;
    if (title && text) await api("/portfolio", "POST", { title, text, type: "case_study" });
    await api("/settings", "PUT", { ...s, onboarded: true });
    await api("/jobs/scout", "POST");
    navigate("/inbox");
  }

  return (
    <Async loading={loading || !s} error={error}>
      {s && (
        <form onSubmit={finish} className="card narrow">
          <h1>Set up GigBid</h1>
          <label htmlFor="persona">Profile</label>
          <select id="persona" value={s.persona} onChange={(e) => setS({ ...s, persona: e.target.value })}>
            {PERSONAS.map(([v, l]) => <option key={v} value={v}>{l} (sample persona)</option>)}
          </select>
          <fieldset>
            <legend>Marketplace</legend>
            <label><input type="radio" checked={s.marketplace === "gigsim"} onChange={() => setS({ ...s, marketplace: "gigsim" })} /> GigSim simulator</label>
            <label><input type="radio" checked={s.marketplace === "upwork"} onChange={() => setS({ ...s, marketplace: "upwork" })} /> Upwork (live, drafts only)</label>
            {s.marketplace === "upwork" && <button type="button" className="secondary" onClick={connectUpwork}>Connect Upwork account</button>}
          </fieldset>
          <label htmlFor="rate">Hourly rate (USD)</label>
          <input id="rate" type="number" min={1} value={s.hourly_rate_usd} onChange={(e) => setS({ ...s, hourly_rate_usd: +e.target.value })} />
          <label htmlFor="floor">Minimum project budget (USD)</label>
          <input id="floor" type="number" min={0} value={s.min_project_usd} onChange={(e) => setS({ ...s, min_project_usd: +e.target.value })} />
          <label htmlFor="connects">Weekly Connects budget</label>
          <input id="connects" type="number" min={0} value={s.weekly_connects_budget} onChange={(e) => setS({ ...s, weekly_connects_budget: +e.target.value })} />
          <label htmlFor="searches">Saved searches (one per line; empty = all new jobs)</label>
          <textarea id="searches" rows={3} value={s.saved_searches.join("\n")} onChange={(e) => setS({ ...s, saved_searches: e.target.value.split("\n") })} />
          <fieldset>
            <legend>Add a portfolio item (optional)</legend>
            <label htmlFor="ptitle">Title</label>
            <input id="ptitle" value={title} onChange={(e) => setTitle(e.target.value)} />
            <label htmlFor="ptext">Case study text</label>
            <textarea id="ptext" rows={4} value={text} onChange={(e) => setText(e.target.value)} />
          </fieldset>
          {note && <p role="alert" className="error">{note}</p>}
          <button type="submit">Finish and find jobs</button>
        </form>
      )}
    </Async>
  );
}
