import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../lib/http";
import type { Settings, Token } from "../lib/types";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const token = await api<Token>(`/auth/${mode}`, "POST", { email, password });
      setToken(token.access_token);
      const settings = await api<Settings>("/settings");
      navigate(settings.onboarded ? "/inbox" : "/onboarding");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <main className="narrow">
      <h1>GigBid</h1>
      <p className="muted">A multi-agent freelancer copilot. You approve everything before it is sent.</p>
      <form onSubmit={submit} className="card">
        <h2>{mode === "login" ? "Sign in" : "Create account"}</h2>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <label htmlFor="password">Password (8+ characters)</label>
        <input id="password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <p role="alert" className="error">{error}</p>}
        <button type="submit">{mode === "login" ? "Sign in" : "Create account"}</button>
        <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
        </button>
      </form>
    </main>
  );
}
