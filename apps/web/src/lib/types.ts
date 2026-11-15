// Typed models come from the generated OpenAPI schema (src/lib/api/schema.d.ts, `make gen-api`).
import type { components } from "./api/schema";

type S = components["schemas"];
export type JobCard = S["JobCard"];
export type Settings = S["Settings"];
export type Decision = S["Decision"];
export type Token = S["Token"];
export type RunRef = S["RunRef"];

// Views over the free-form JSON documents the API returns (graph state mirrored per job/thread).
export type Evidence = { id: string; type: string; title: string; snippet: string; outcome: string; source: string; date: string };
export type Claim = { claim: string; label: "supported" | "partly_supported" | "unsupported"; evidence_ids: string[]; missing: string[] };
export type Preview = { would_send: Record<string, unknown>; connects_cost: number; balance_after: number | null };
export type ApprovalPayload = {
  kind: "proposal" | "message"; cover_letter?: string; claims?: Claim[]; evidence?: Evidence[];
  risk_report?: { score: number; flags: string[]; explanation: string };
  price_quote?: { amount_usd: number; connects_cost: number; rationale: string };
  preview: Preview & { interview_hold?: string[] };
  critiques?: { approved: boolean; issues: string[]; revision: number }[];
  compliance: { allowed: boolean; violations: string[]; fixes: string[] };
  client_message?: string; intent?: { intent: string; reason: string }; reply?: { text: string; slots: string[] };
};
export type Approval = { id: string; kind: string; job_id?: string; thread_id?: string; run_id: string; payload: ApprovalPayload };
export type RunEvent = { ts: number; node: string; detail?: string; status?: string; reason?: string };
