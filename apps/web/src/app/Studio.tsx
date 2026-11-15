import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import ApprovalPanel from "../components/ApprovalPanel";
import EvidenceHover from "../components/EvidenceHover";
import { Async, Badge } from "../components/States";
import { api, useApi } from "../lib/http";
import type { Approval, Claim, Evidence } from "../lib/types";

type StudioData = {
  job: { job: { title: string }; status: string; status_reason: string; cover_letter?: string; claim_checks?: Claim[]; evidence?: Evidence[];
         critiques?: { approved: boolean; issues: string[]; revision: number }[]; compliance?: { allowed: boolean; violations: string[]; fixes: string[] };
         submission?: { status: string; id: string; connects_cost: number }; run_id?: string };
  approval: Approval | null;
};

/** Draft editor: evidence on hover, Critic and Compliance comments, regenerate a paragraph, approve / edit / reject. */
export default function Studio() {
  const { id } = useParams();
  const { data, loading, error, reload } = useApi<StudioData>(`/proposals/${id}`, 3000);
  const [note, setNote] = useState("");
  const job = data?.job;
  const text = data?.approval?.payload.cover_letter ?? job?.cover_letter ?? "";

  async function regenerate(index: number) {
    setNote("");
    await api(`/proposals/${id}/regenerate/${index}`, "POST").then(reload).catch((e) => setNote(e.message));
  }

  return (
    <Async loading={loading} error={error} empty={!text && "No draft for this job yet."}>
      {job && (
        <>
          <h1>Proposal: {job.job.title}</h1>
          <p className="row meta">
            <Badge kind="info">{job.status.replace("_", " ")}</Badge>
            {job.status_reason && <span>{job.status_reason}</span>}
            {job.run_id && <Link to={`/runs/${job.run_id}`}>Agent run</Link>}
          </p>
          <div className="grid">
            <section className="card">
              <h2>Draft <span className="muted">(hover or focus a highlighted claim to see its evidence)</span></h2>
              <EvidenceHover text={text} claims={data.approval?.payload.claims ?? job.claim_checks ?? []} evidence={job.evidence ?? []} />
              {data.approval && (
                <p className="row">
                  {text.split("\n\n").map((_, i) => <button key={i} className="secondary" onClick={() => regenerate(i)}>Regenerate paragraph {i + 1}</button>)}
                </p>
              )}
              {note && <p role="alert" className="error">{note}</p>}
              <h3>Critic</h3>
              <ul>
                {(job.critiques ?? []).map((c, i) => (
                  <li key={i}>Round {c.revision + 1}: {c.approved ? "approved" : c.issues.join("; ")}</li>
                ))}
              </ul>
              <h3>Compliance Guard</h3>
              <p>
                {job.compliance?.allowed ? <Badge kind="ok">allowed</Badge> : <Badge kind="bad">blocked</Badge>}{" "}
                {[...(job.compliance?.violations ?? []), ...(job.compliance?.fixes ?? [])].join("; ") || "No policy issues found."}
              </p>
            </section>
            {data.approval
              ? <ApprovalPanel key={text} approval={data.approval} text={text} onDone={reload} />
              : <section className="card"><h3>No decision needed</h3>
                  <p>{job.submission ? `Submitted (${job.submission.id}), ${job.submission.connects_cost} Connects spent.` : `Status: ${job.status.replace("_", " ")}.`}</p>
                </section>}
          </div>
        </>
      )}
    </Async>
  );
}
