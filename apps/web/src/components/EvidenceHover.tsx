import type { Claim, Evidence } from "../lib/types";

/** Renders the draft so that every claim shows the evidence behind it on hover or keyboard focus. */
export default function EvidenceHover({ text, claims, evidence }: { text: string; claims: Claim[]; evidence: Evidence[] }) {
  const byId = new Map(evidence.map((e) => [e.id, e]));
  return (
    <div className="draft">
      {text.split("\n\n").map((para, i) => (
        <p key={i}>
          {para.split(/(?<=[.!?])\s+/).map((sentence, j) => {
            const claim = claims.find((c) => c.claim === sentence.trim());
            if (!claim) return <span key={j}>{sentence} </span>;
            return (
              <span key={j} className={`claim ${claim.label}`} tabIndex={0} aria-label={`Claim, ${claim.label.replace("_", " ")}`}>
                {sentence}{" "}
                <span className="tooltip" role="tooltip">
                  <b>{claim.label.replace("_", " ")}</b>
                  {claim.evidence_ids.map((id) => (
                    <span key={id} className="ev"><i>{byId.get(id)?.title ?? id}</i> ({byId.get(id)?.type}): {byId.get(id)?.snippet.slice(0, 220)}…</span>
                  ))}
                  {claim.evidence_ids.length === 0 && <span className="ev">No evidence supports this sentence.</span>}
                  {claim.missing.length > 0 && <span className="ev">Not found in evidence: {claim.missing.join(", ")}</span>}
                </span>
              </span>
            );
          })}
        </p>
      ))}
    </div>
  );
}
