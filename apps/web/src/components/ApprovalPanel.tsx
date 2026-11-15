import { useState } from "react";
import { api } from "../lib/http";
import type { Approval, Decision } from "../lib/types";
import { Badge } from "./States";

/** Approve, edit or reject. Posting a decision resumes the interrupted LangGraph thread. */
export default function ApprovalPanel({ approval, text, onDone }: { approval: Approval; text: string; onDone: () => void }) {
  const [draft, setDraft] = useState(text);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { preview, compliance } = approval.payload;

  async function send(decision: Decision) {
    setBusy(true);
    setError("");
    try {
      await api(`/approvals/${encodeURIComponent(approval.id)}`, "POST", decision);
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-label="Approval">
      <h3>Your decision</h3>
      {!compliance.allowed && (
        <div role="alert" className="error">
          Compliance Guard blocked this text: {compliance.violations.join("; ")}. Edit it to continue.
        </div>
      )}
      <label htmlFor="edit">Edit before sending</label>
      <textarea id="edit" rows={10} value={draft} onChange={(e) => setDraft(e.target.value)} />
      <h4>What will be sent (dry run)</h4>
      <pre className="preview">{JSON.stringify(preview.would_send, null, 2)}</pre>
      {"connects_cost" in preview && (
        <p>Cost: <b>{preview.connects_cost} Connects</b>{preview.balance_after != null && <> (balance after: {preview.balance_after})</>}</p>
      )}
      {preview.interview_hold?.length ? <p>Tentative calendar hold: {preview.interview_hold[0]}</p> : null}
      <div className="row">
        <button disabled={busy || !compliance.allowed || draft !== text} onClick={() => send({ action: "approve", text: "", reason: "" })}>Approve and send</button>
        <button disabled={busy || draft === text} className="secondary" onClick={() => send({ action: "edit", text: draft, reason: "" })}>Save edit and re-check</button>
      </div>
      <label htmlFor="reason">Reason for rejecting</label>
      <input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. budget too low" />
      <button disabled={busy || !reason.trim()} className="danger" onClick={() => send({ action: "reject", text: "", reason })}>Reject</button>
      {busy && <p role="status">Working…</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {compliance.fixes.length > 0 && <p className="muted">Removed automatically: {compliance.fixes.join("; ")} <Badge kind="info">compliance</Badge></p>}
    </section>
  );
}
