import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { setToken, useApi } from "../lib/http";

type Health = { marketplace: { ok: boolean; error: string }; mode: string; profile: string };

/** Shown on every screen while the marketplace MCP server cannot be reached. */
export function DegradedBanner() {
  const { data } = useApi<Health>("/health/marketplace", 5000);
  if (!data || data.marketplace.ok) return null;
  return (
    <div role="alert" className="banner">
      Marketplace unavailable. New work is queued and will resume automatically when it is back.
    </div>
  );
}

const LINKS = [["/inbox", "Inbox"], ["/pipeline", "Pipeline"], ["/messages", "Messages"], ["/runs", "Runs"], ["/analytics", "Analytics"], ["/settings", "Settings"]];

export default function Layout() {
  const navigate = useNavigate();
  return (
    <>
      <header>
        <strong className="logo">GigBid</strong>
        <nav aria-label="Main">
          {LINKS.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}
        </nav>
        <button className="link" onClick={() => { setToken(""); navigate("/login"); }}>Sign out</button>
      </header>
      <DegradedBanner />
      <main><Outlet /></main>
    </>
  );
}
