import type { ReactNode } from "react";

/** Clear loading, error and empty states for every screen. */
export function Async({ loading, error, empty, children }: { loading: boolean; error: string; empty?: string | false; children: ReactNode }) {
  if (loading) return <p role="status" className="muted">Loading…</p>;
  if (error) return <p role="alert" className="error">Something went wrong: {error}</p>;
  if (empty) return <p className="empty">{empty}</p>;
  return <>{children}</>;
}

export function Badge({ kind, children }: { kind: "ok" | "warn" | "bad" | "info"; children: ReactNode }) {
  return <span className={`badge ${kind}`}>{children}</span>;
}
